"""
Benchmark runner orchestrating synthetic evaluation runs against the reconciliation engine.
"""

import time
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from backend.app.benchmark.matcher import (
    AnomalyMatcher,
    extract_detected_issues,
    extract_expected_anomalies,
)
from backend.app.benchmark.metrics import compute_benchmark_metrics
from backend.app.benchmark.models import (
    AnomalyTypeBenchmarkResult,
    BenchmarkConfig,
    BenchmarkMetrics,
    BenchmarkRunResult,
    PerformanceMetrics,
    ScenarioBenchmarkResult,
)
from backend.app.models.common import Currency
from backend.app.models.order import Order, OrderStatus
from backend.app.models.payment import Payment, PaymentMethod, PaymentStatus
from backend.app.models.settlement import Settlement, SettlementStatus
from backend.app.models.settlement_transaction import (
    SettlementTransaction,
    SettlementTransactionEntityType,
    SettlementTransactionType,
)
from backend.app.models.bank_entry import BankEntry
from backend.app.models.merchant import Merchant, MerchantStatus
from backend.app.reconciliation import (
    DeterministicReconciliationEngine,
    ReconciliationConfig,
)
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.ground_truth.models import GroundTruth, ScenarioLabel
from simulator.observed import (
    AnomalyRecord,
    AnomalySpec,
    AnomalyType,
    ObservationConfig,
    ObservationGenerator,
    ObservedWorld,
)


class BenchmarkRunner:
    """
    Executes automated benchmark suites evaluating the deterministic reconciliation engine
    across clean baselines, anomaly injections, and large batch loads.
    """

    def __init__(self, engine: Optional[DeterministicReconciliationEngine] = None):
        self.engine = engine or DeterministicReconciliationEngine()

    def run(self, config: Optional[BenchmarkConfig] = None) -> BenchmarkRunResult:
        start_time = time.perf_counter()
        config = config or BenchmarkConfig()

        scenario_results: List[ScenarioBenchmarkResult] = []

        # ---------------------------------------------------------------------
        # 1. Clean Scenarios Benchmark
        # ---------------------------------------------------------------------
        if config.run_clean:
            for sc_name in config.scenarios:
                clean_res = self._run_scenario_clean(sc_name, config)
                scenario_results.append(clean_res)

        # ---------------------------------------------------------------------
        # 2. Anomaly-Injected Scenarios Benchmark
        # ---------------------------------------------------------------------
        if config.run_anomalies:
            for sc_name in config.scenarios:
                for a_type in config.anomaly_types:
                    anom_res = self._run_scenario_with_anomaly(sc_name, a_type, config)
                    if anom_res is not None:
                        scenario_results.append(anom_res)

        # ---------------------------------------------------------------------
        # 3. Anomaly Breakdown Aggregation
        # ---------------------------------------------------------------------
        anomaly_breakdown = self._compute_anomaly_breakdown(scenario_results)

        # ---------------------------------------------------------------------
        # 4. Aggregate Metrics
        # ---------------------------------------------------------------------
        total_tp = sum(s.metrics.true_positives for s in scenario_results)
        total_fp = sum(s.metrics.false_positives for s in scenario_results)
        total_fn = sum(s.metrics.false_negatives for s in scenario_results)
        total_exp = sum(s.metrics.total_expected_anomalies for s in scenario_results)
        total_det = sum(s.metrics.total_detected_issues for s in scenario_results)
        total_rec = sum(s.total_records for s in scenario_results)
        total_setl = sum(s.settlement_count for s in scenario_results)

        clean_results = [s for s in scenario_results if s.is_clean]
        clean_reconciled = sum(1 for s in clean_results if s.reconciliation_status == "RECONCILED")
        clean_rec_rate = (
            (Decimal(clean_reconciled) / Decimal(len(clean_results))).quantize(Decimal("0.0001"))
            if clean_results
            else Decimal("1.0000")
        )

        aggregate_metrics = compute_benchmark_metrics(
            true_positives=total_tp,
            false_positives=total_fp,
            false_negatives=total_fn,
            total_expected_anomalies=total_exp,
            total_detected_issues=total_det,
            total_records=total_rec,
            total_settlements=total_setl,
            reconciled_settlements=sum(1 for s in scenario_results if s.reconciliation_status == "RECONCILED"),
            exception_settlements=sum(1 for s in scenario_results if s.reconciliation_status == "EXCEPTION"),
        )

        elapsed = time.perf_counter() - start_time
        perf = PerformanceMetrics(
            elapsed_seconds=round(elapsed, 4),
            total_records=total_rec,
            records_per_second=round(total_rec / elapsed, 2) if elapsed > 0 else 0.0,
        )

        run_id = f"bm_run_{int(start_time * 1000)}"

        return BenchmarkRunResult(
            run_id=run_id,
            config=config,
            scenario_results=scenario_results,
            anomaly_breakdown=anomaly_breakdown,
            aggregate_metrics=aggregate_metrics,
            performance=perf,
            clean_reconciliation_rate=clean_rec_rate,
        )

    def run_large_batch(self, batch_size: int = 100, seed: int = 42) -> ScenarioBenchmarkResult:
        """
        Generates a synthetic financial dataset containing >= batch_size records,
        injects controlled anomalies, and runs full reconciliation benchmark.
        """
        start_time = time.perf_counter()
        gt = self._generate_large_batch_ground_truth(batch_size, seed)

        # Inject controlled anomalies across the batch
        anomalies = [
            AnomalySpec(
                anomaly_type=AnomalyType.AMOUNT_MISMATCH,
                target_entity_type="bank_entry",
                target_field="amount",
                delta=Decimal("-250.00"),
                target_index=0,
            ),
            AnomalySpec(
                anomaly_type=AnomalyType.MISSING_RECORD,
                target_entity_type="settlement_transaction",
                target_index=1,
            ),
            AnomalySpec(
                anomaly_type=AnomalyType.DUPLICATE_RECORD,
                target_entity_type="payment",
                target_index=2,
            ),
            AnomalySpec(
                anomaly_type=AnomalyType.IDENTIFIER_MISMATCH,
                target_entity_type="bank_entry",
                target_field="utr",
                target_index=1,
            ),
        ]

        obs_config = ObservationConfig.with_anomalies(seed=seed, anomalies=anomalies)
        obs_world, manifest = ObservationGenerator.generate(gt, obs_config)

        recon_res = self.engine.reconcile(obs_world, ReconciliationConfig())

        expected = extract_expected_anomalies(manifest)
        detected = extract_detected_issues(recon_res)

        evaluations, metrics = AnomalyMatcher.evaluate(
            expected_anomalies=expected,
            detected_issues=detected,
            total_records=recon_res.metrics.total_records,
            total_settlements=len(obs_world.settlements),
            reconciled_settlements=recon_res.metrics.reconciled_settlements_count,
            exception_settlements=recon_res.metrics.exception_settlements_count,
        )

        return ScenarioBenchmarkResult(
            scenario_name=f"large_batch_{batch_size}_records",
            is_clean=False,
            total_records=recon_res.metrics.total_records,
            settlement_count=len(obs_world.settlements),
            expected_anomalies=expected,
            detected_issues=detected,
            evaluations=evaluations,
            metrics=metrics,
            reconciliation_status=recon_res.status,
        )

    def _run_scenario_clean(self, scenario_name: str, config: BenchmarkConfig) -> ScenarioBenchmarkResult:
        sim_config = SimulationConfig(
            seed=config.seed,
            merchant_count=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            order_count=1,
            scenario_type=scenario_name,
            fee_rate=Decimal("0.02"),
            tax_rate=Decimal("0.18"),
            rounding_mode="ROUND_HALF_UP",
        )
        gt = Simulator(sim_config).run()
        obs_world, manifest = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=config.seed))

        recon_res = self.engine.reconcile(obs_world, ReconciliationConfig(tolerance=config.tolerance))

        expected = extract_expected_anomalies(manifest)
        detected = extract_detected_issues(recon_res)

        evaluations, metrics = AnomalyMatcher.evaluate(
            expected_anomalies=expected,
            detected_issues=detected,
            total_records=recon_res.metrics.total_records,
            total_settlements=len(obs_world.settlements),
            reconciled_settlements=recon_res.metrics.reconciled_settlements_count,
            exception_settlements=recon_res.metrics.exception_settlements_count,
        )

        return ScenarioBenchmarkResult(
            scenario_name=f"{scenario_name}_clean",
            is_clean=True,
            total_records=recon_res.metrics.total_records,
            settlement_count=len(obs_world.settlements),
            expected_anomalies=expected,
            detected_issues=detected,
            evaluations=evaluations,
            metrics=metrics,
            reconciliation_status=recon_res.status,
        )

    def _run_scenario_with_anomaly(
        self,
        scenario_name: str,
        anomaly_type: AnomalyType,
        config: BenchmarkConfig,
    ) -> Optional[ScenarioBenchmarkResult]:
        sim_config = SimulationConfig(
            seed=config.seed,
            merchant_count=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            order_count=1,
            scenario_type=scenario_name,
            fee_rate=Decimal("0.02"),
            tax_rate=Decimal("0.18"),
            rounding_mode="ROUND_HALF_UP",
        )
        gt = Simulator(sim_config).run()

        # Construct specific anomaly spec depending on anomaly type
        spec: Optional[AnomalySpec] = None
        if anomaly_type == AnomalyType.AMOUNT_MISMATCH and gt.bank_entries:
            spec = AnomalySpec(
                anomaly_type=AnomalyType.AMOUNT_MISMATCH,
                target_entity_type="bank_entry",
                target_field="amount",
                delta=Decimal("-250.00"),
                target_index=0,
            )
        elif anomaly_type == AnomalyType.MISSING_RECORD and gt.settlement_transactions:
            spec = AnomalySpec(
                anomaly_type=AnomalyType.MISSING_RECORD,
                target_entity_type="settlement_transaction",
                target_index=0,
            )
        elif anomaly_type == AnomalyType.DUPLICATE_RECORD and gt.payments:
            spec = AnomalySpec(
                anomaly_type=AnomalyType.DUPLICATE_RECORD,
                target_entity_type="payment",
                target_index=0,
            )
        elif anomaly_type == AnomalyType.IDENTIFIER_MISMATCH and gt.bank_entries:
            spec = AnomalySpec(
                anomaly_type=AnomalyType.IDENTIFIER_MISMATCH,
                target_entity_type="bank_entry",
                target_field="utr",
                target_index=0,
            )

        if spec is None:
            return None

        obs_config = ObservationConfig.with_anomalies(seed=config.seed, anomalies=[spec])
        obs_world, manifest = ObservationGenerator.generate(gt, obs_config)

        recon_res = self.engine.reconcile(obs_world, ReconciliationConfig(tolerance=config.tolerance))

        expected = extract_expected_anomalies(manifest)
        detected = extract_detected_issues(recon_res)

        evaluations, metrics = AnomalyMatcher.evaluate(
            expected_anomalies=expected,
            detected_issues=detected,
            total_records=recon_res.metrics.total_records,
            total_settlements=len(obs_world.settlements),
            reconciled_settlements=recon_res.metrics.reconciled_settlements_count,
            exception_settlements=recon_res.metrics.exception_settlements_count,
        )

        return ScenarioBenchmarkResult(
            scenario_name=f"{scenario_name}_{anomaly_type.value.lower()}",
            is_clean=False,
            total_records=recon_res.metrics.total_records,
            settlement_count=len(obs_world.settlements),
            expected_anomalies=expected,
            detected_issues=detected,
            evaluations=evaluations,
            metrics=metrics,
            reconciliation_status=recon_res.status,
        )

    def _compute_anomaly_breakdown(
        self, scenario_results: List[ScenarioBenchmarkResult]
    ) -> Dict[str, AnomalyTypeBenchmarkResult]:
        breakdown: Dict[str, AnomalyTypeBenchmarkResult] = {}

        for a_type in AnomalyType:
            type_str = a_type.value
            type_suffix = a_type.value.lower()
            matching_scenarios = [s for s in scenario_results if s.scenario_name.endswith(type_suffix)]

            expected_count = sum(s.metrics.total_expected_anomalies for s in matching_scenarios)
            detected_count = sum(s.metrics.total_detected_issues for s in matching_scenarios)
            tp = sum(s.metrics.true_positives for s in matching_scenarios)
            fp = sum(s.metrics.false_positives for s in matching_scenarios)
            fn = sum(s.metrics.false_negatives for s in matching_scenarios)

            p = (Decimal(tp) / Decimal(tp + fp)).quantize(Decimal("0.0001")) if (tp + fp) > 0 else (Decimal("1.0000") if expected_count == 0 else Decimal("0.0000"))
            r = (Decimal(tp) / Decimal(tp + fn)).quantize(Decimal("0.0001")) if (tp + fn) > 0 else Decimal("0.0000")
            sum_pr = p + r
            f1 = ((Decimal("2.0") * p * r) / sum_pr).quantize(Decimal("0.0001")) if sum_pr > 0 else Decimal("0.0000")

            breakdown[type_str] = AnomalyTypeBenchmarkResult(
                anomaly_type=type_str,
                expected_count=expected_count,
                detected_count=detected_count,
                tp=tp,
                fp=fp,
                fn=fn,
                precision=p,
                recall=r,
                f1=f1,
            )

        return breakdown

    def _generate_large_batch_ground_truth(self, target_records: int, seed: int) -> GroundTruth:
        """
        Deterministically builds a high-volume GroundTruth dataset with multiple merchants,
        orders, payments, settlements, and bank entries.
        """
        import random
        from datetime import datetime, timezone, timedelta

        rng = random.Random(seed)
        base_time = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        # 1. Merchants (e.g. 3 merchants)
        merchants = [
            Merchant(merchant_id=f"merch_{i+1:03d}", name=f"Merchant {i+1}", status=MerchantStatus.ACTIVE, created_at=base_time)
            for i in range(3)
        ]

        orders: List[Order] = []
        payments: List[Payment] = []
        stxns: List[SettlementTransaction] = []
        settlements: List[Settlement] = []
        bank_entries: List[BankEntry] = []

        # Target payments per merchant to reach total target records
        # Each payment lifecycle adds: 1 Order + 1 Payment + 1 STXN + (shared setl & bank) ~= 3.2 records
        payments_needed = max(15, target_records // 3)

        for m_idx, merchant in enumerate(merchants):
            m_payments_count = payments_needed // len(merchants)
            setl_id = f"setl_batch_{m_idx+1:03d}"
            utr = f"MOCKUTR{rng.randint(100000000, 999999999)}"

            total_net = Decimal("0.00")
            total_fee = Decimal("0.00")
            total_tax = Decimal("0.00")

            for p_idx in range(m_payments_count):
                amt = Decimal(f"{rng.randint(500, 5000)}.00")
                fee = (amt * Decimal("0.02")).quantize(Decimal("0.01"))
                tax = (fee * Decimal("0.18")).quantize(Decimal("0.01"))
                net = amt - fee - tax

                total_net += net
                total_fee += fee
                total_tax += tax

                order_id = f"ord_b_{m_idx+1:02d}_{p_idx+1:03d}"
                pay_id = f"pay_b_{m_idx+1:02d}_{p_idx+1:03d}"
                stxn_id = f"stxn_b_{m_idx+1:02d}_{p_idx+1:03d}"

                t_ord = base_time + timedelta(hours=p_idx)
                orders.append(
                    Order(order_id=order_id, merchant_id=merchant.merchant_id, amount=amt, currency=Currency.INR, status=OrderStatus.PAID, created_at=t_ord)
                )
                payments.append(
                    Payment(
                        payment_id=pay_id,
                        order_id=order_id,
                        merchant_id=merchant.merchant_id,
                        amount=amt,
                        currency=Currency.INR,
                        status=PaymentStatus.CAPTURED,
                        method=PaymentMethod.UPI,
                        created_at=t_ord + timedelta(minutes=5),
                        captured_at=t_ord + timedelta(minutes=6),
                        fee=fee,
                        tax=tax,
                        settlement_id=setl_id,
                    )
                )
                stxns.append(
                    SettlementTransaction(
                        settlement_txn_id=stxn_id,
                        settlement_id=setl_id,
                        merchant_id=merchant.merchant_id,
                        entity_type=SettlementTransactionEntityType.PAYMENT,
                        entity_id=pay_id,
                        amount=amt,
                        fee=fee,
                        tax=tax,
                        net_amount=net,
                        type=SettlementTransactionType.CREDIT,
                        created_at=t_ord + timedelta(days=2),
                    )
                )

            setl_time = base_time + timedelta(days=2, hours=m_payments_count)
            settlements.append(
                Settlement(
                    settlement_id=setl_id,
                    merchant_id=merchant.merchant_id,
                    amount=total_net,
                    currency=Currency.INR,
                    status=SettlementStatus.PROCESSED,
                    fees=total_fee,
                    tax=total_tax,
                    created_at=setl_time,
                    utr=utr,
                    settled_at=setl_time,
                )
            )
            bank_entries.append(
                BankEntry(
                    bank_entry_id=f"bank_b_{m_idx+1:03d}",
                    merchant_id=merchant.merchant_id,
                    account_number=f"ACCT{m_idx+1:08d}",
                    amount=total_net,
                    currency=Currency.INR,
                    utr=utr,
                    transaction_date=setl_time + timedelta(days=1),
                )
            )

        sim_config = SimulationConfig(
            seed=seed,
            merchant_count=len(merchants),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            order_count=len(orders),
            scenario_type="large_batch",
        )

        return GroundTruth(
            config=sim_config,
            merchants=merchants,
            orders=orders,
            payments=payments,
            settlement_transactions=stxns,
            settlements=settlements,
            bank_entries=bank_entries,
            scenario_labels={s.settlement_id: ScenarioLabel(settlement_id=s.settlement_id, scenario_type="large_batch") for s in settlements},
        )
