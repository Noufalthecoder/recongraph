"""
Deterministic Application Demo State Management.
Orchestrates ObservedWorld, ReconciliationResult, FinancialGraph, and Benchmark results.
"""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from backend.app.benchmark.runner import BenchmarkRunner
from backend.app.graph import FinancialGraphBuilder
from backend.app.graph.evidence import GraphEvidenceLayer
from backend.app.graph.models import FinancialGraph
from backend.app.graph.queries import InvestigationQueryEngine
from backend.app.investigation import (
    DeterministicMockProvider,
    InvestigationService,
    InvestigationToolRegistry,
)
from backend.app.reconciliation import DeterministicReconciliationEngine
from backend.app.reconciliation.models import ReconciliationResult
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import (
    AnomalySpec,
    AnomalyType,
    ObservationConfig,
    ObservationGenerator,
    ObservedWorld,
)


class ScenarioBundle:
    """Encapsulates all runtime artifacts for a loaded scenario."""

    def __init__(
        self,
        scenario_id: str,
        name: str,
        description: str,
        observed_world: ObservedWorld,
        recon_result: ReconciliationResult,
        graph: FinancialGraph,
        evidence_layer: GraphEvidenceLayer,
        has_anomalies: bool,
    ):
        self.scenario_id = scenario_id
        self.name = name
        self.description = description
        self.observed_world = observed_world
        self.recon_result = recon_result
        self.graph = graph
        self.evidence_layer = evidence_layer
        self.has_anomalies = has_anomalies
        self.query_engine = InvestigationQueryEngine(graph, evidence_layer)
        self.tools = InvestigationToolRegistry(graph, evidence_layer, recon_result)


def _generate_composite_production_demo() -> ObservedWorld:
    """
    Generates a realistic composite batch of ~100+ financial records
    combining many-to-one settlements, fee/tax transactions, refunds, adjustments,
    and a bank amount mismatch of ₹250 on the adjustment settlement.
    """
    merchants = []
    orders = []
    payments = []
    refunds = []
    adjustments = []
    settlement_transactions = []
    settlements = []
    bank_entries = []

    # 1. Clean Many-to-One Batch (5 orders)
    sim1 = Simulator(
        SimulationConfig(
            seed=101,
            merchant_count=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            order_count=5,
            scenario_type="many_to_one_v1",
        )
    ).run()
    obs1, _ = ObservationGenerator.generate(sim1, ObservationConfig.clean(seed=101))
    merchants.extend(obs1.merchants)
    orders.extend(obs1.orders)
    payments.extend(obs1.payments)
    settlement_transactions.extend(obs1.settlement_transactions)
    settlements.extend(obs1.settlements)
    bank_entries.extend(obs1.bank_entries)

    # 2. Clean Many-to-One with Fee & Tax (5 orders)
    sim2 = Simulator(
        SimulationConfig(
            seed=102,
            merchant_count=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            order_count=5,
            scenario_type="many_to_one_with_fee_tax_v1",
        )
    ).run()
    obs2, _ = ObservationGenerator.generate(sim2, ObservationConfig.clean(seed=102))
    merchants.extend(obs2.merchants)
    orders.extend(obs2.orders)
    payments.extend(obs2.payments)
    settlement_transactions.extend(obs2.settlement_transactions)
    settlements.extend(obs2.settlements)
    bank_entries.extend(obs2.bank_entries)

    # 3. Clean Multiple Refunds Scenario (4 orders, 3 refunds)
    sim3 = Simulator(
        SimulationConfig(
            seed=103,
            merchant_count=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            order_count=4,
            scenario_type="multiple_refunds_v1",
        )
    ).run()
    obs3, _ = ObservationGenerator.generate(sim3, ObservationConfig.clean(seed=103))
    merchants.extend(obs3.merchants)
    orders.extend(obs3.orders)
    payments.extend(obs3.payments)
    refunds.extend(obs3.refunds)
    settlement_transactions.extend(obs3.settlement_transactions)
    settlements.extend(obs3.settlements)
    bank_entries.extend(obs3.bank_entries)

    # 4. Adjustment Scenario with ₹250 Bank Amount Mismatch
    sim4 = Simulator(
        SimulationConfig(
            seed=104,
            merchant_count=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            order_count=2,
            scenario_type="adjustment_v1",
        )
    ).run()
    spec = AnomalySpec(
        anomaly_type=AnomalyType.AMOUNT_MISMATCH,
        target_entity_type="bank_entry",
        target_field="amount",
        delta=Decimal("-250.00"),
        target_index=0,
    )
    obs4, _ = ObservationGenerator.generate(
        sim4, ObservationConfig.with_anomalies(seed=104, anomalies=[spec])
    )
    merchants.extend(obs4.merchants)
    orders.extend(obs4.orders)
    payments.extend(obs4.payments)
    adjustments.extend(obs4.adjustments)
    settlement_transactions.extend(obs4.settlement_transactions)
    settlements.extend(obs4.settlements)
    bank_entries.extend(obs4.bank_entries)

    return ObservedWorld(
        merchants=merchants,
        orders=orders,
        payments=payments,
        refunds=refunds,
        adjustments=adjustments,
        settlement_transactions=settlement_transactions,
        settlements=settlements,
        bank_entries=bank_entries,
    )


def _build_scenario_bundle(
    scenario_id: str,
    name: str,
    description: str,
    observed_world: ObservedWorld,
    has_anomalies: bool = False,
) -> ScenarioBundle:
    engine = DeterministicReconciliationEngine()
    recon_res = engine.reconcile(observed_world)
    graph, evidence = FinancialGraphBuilder.build(observed_world, reconciliation_result=recon_res)
    return ScenarioBundle(
        scenario_id=scenario_id,
        name=name,
        description=description,
        observed_world=observed_world,
        recon_result=recon_res,
        graph=graph,
        evidence_layer=evidence,
        has_anomalies=has_anomalies,
    )


class DemoStateManager:
    """
    Manages active scenario bundle, available scenario catalogue, and cached benchmark results.
    """

    def __init__(self):
        self._scenarios_catalog: Dict[str, ScenarioBundle] = {}
        self._active_scenario_id: str = "production_demo"
        self._benchmark_cache = None
        self._initialize()

    def _initialize(self):
        # 1. Production Demo Composite Scenario
        comp_obs = _generate_composite_production_demo()
        self._scenarios_catalog["production_demo"] = _build_scenario_bundle(
            scenario_id="production_demo",
            name="Production Demo (Large Batch)",
            description="Realistic composite workload: 100+ records, multiple settlements, fee/tax calculations, refunds, adjustments, and an authentic ₹250 bank mismatch exception.",
            observed_world=comp_obs,
            has_anomalies=True,
        )

        # 2. 100% Clean Batch
        sim_clean = Simulator(
            SimulationConfig(
                seed=201,
                merchant_count=1,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                order_count=10,
                scenario_type="many_to_one_with_fee_tax_v1",
            )
        ).run()
        obs_clean, _ = ObservationGenerator.generate(sim_clean, ObservationConfig.clean(seed=201))
        self._scenarios_catalog["clean_batch"] = _build_scenario_bundle(
            scenario_id="clean_batch",
            name="Clean Batch (100% Reconciled)",
            description="Pure clean batch with fee/tax breakdowns and 100% clean reconciliation rate.",
            observed_world=obs_clean,
            has_anomalies=False,
        )

        # 3. Bank Amount Mismatch
        sim_bank = Simulator(
            SimulationConfig(
                seed=202,
                merchant_count=1,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                order_count=2,
                scenario_type="adjustment_v1",
            )
        ).run()
        obs_bank, _ = ObservationGenerator.generate(
            sim_bank,
            ObservationConfig.with_anomalies(
                seed=202,
                anomalies=[
                    AnomalySpec(
                        anomaly_type=AnomalyType.AMOUNT_MISMATCH,
                        target_entity_type="bank_entry",
                        target_field="amount",
                        delta=Decimal("-250.00"),
                        target_index=0,
                    )
                ],
            ),
        )
        self._scenarios_catalog["bank_amount_mismatch"] = _build_scenario_bundle(
            scenario_id="bank_amount_mismatch",
            name="Bank Amount Mismatch (-₹250)",
            description="Settlement payout with ₹250 discrepancy against bank credit statement.",
            observed_world=obs_bank,
            has_anomalies=True,
        )

        # 4. Missing Record Anomaly
        sim_miss = Simulator(
            SimulationConfig(
                seed=203,
                merchant_count=1,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                order_count=2,
                scenario_type="many_to_one_v1",
            )
        ).run()
        obs_miss, _ = ObservationGenerator.generate(
            sim_miss,
            ObservationConfig.with_anomalies(
                seed=203,
                anomalies=[
                    AnomalySpec(
                        anomaly_type=AnomalyType.MISSING_RECORD,
                        target_entity_type="payment",
                        target_index=0,
                    )
                ],
            ),
        )
        self._scenarios_catalog["missing_record"] = _build_scenario_bundle(
            scenario_id="missing_record",
            name="Missing Payment Record",
            description="Settlement transaction references a payment missing from the ingested batch.",
            observed_world=obs_miss,
            has_anomalies=True,
        )

        # 5. Duplicate Record Anomaly
        sim_dup = Simulator(
            SimulationConfig(
                seed=204,
                merchant_count=1,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                order_count=2,
                scenario_type="many_to_one_v1",
            )
        ).run()
        obs_dup, _ = ObservationGenerator.generate(
            sim_dup,
            ObservationConfig.with_anomalies(
                seed=204,
                anomalies=[
                    AnomalySpec(
                        anomaly_type=AnomalyType.DUPLICATE_RECORD,
                        target_entity_type="payment",
                        target_index=0,
                    )
                ],
            ),
        )
        self._scenarios_catalog["duplicate_record"] = _build_scenario_bundle(
            scenario_id="duplicate_record",
            name="Duplicate Record Ingestion",
            description="Duplicate payment entity with duplicate primary key ingested into batch.",
            observed_world=obs_dup,
            has_anomalies=True,
        )

        # 6. Identifier Mismatch
        sim_idm = Simulator(
            SimulationConfig(
                seed=205,
                merchant_count=1,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                order_count=1,
                scenario_type="minimal_lifecycle_v1",
            )
        ).run()
        obs_idm, _ = ObservationGenerator.generate(
            sim_idm,
            ObservationConfig.with_anomalies(
                seed=205,
                anomalies=[
                    AnomalySpec(
                        anomaly_type=AnomalyType.IDENTIFIER_MISMATCH,
                        target_entity_type="bank_entry",
                        target_field="utr",
                        target_index=0,
                    )
                ],
            ),
        )
        self._scenarios_catalog["identifier_mismatch"] = _build_scenario_bundle(
            scenario_id="identifier_mismatch",
            name="Bank UTR Identifier Mismatch",
            description="Bank entry contains corrupted UTR identifier preventing direct UTR settlement matching.",
            observed_world=obs_idm,
            has_anomalies=True,
        )

        # Pre-compute authoritative benchmark evaluation
        self._benchmark_cache = BenchmarkRunner().run()

    @property
    def active_scenario(self) -> ScenarioBundle:
        return self._scenarios_catalog[self._active_scenario_id]

    @property
    def active_scenario_id(self) -> str:
        return self._active_scenario_id

    @property
    def scenarios_catalog(self) -> Dict[str, ScenarioBundle]:
        return self._scenarios_catalog

    @property
    def benchmark_result(self):
        return self._benchmark_cache

    def set_active_scenario(self, scenario_id: str) -> bool:
        if scenario_id in self._scenarios_catalog:
            self._active_scenario_id = scenario_id
            return True
        return False


# Global singleton instance for demo application
demo_state = DemoStateManager()
