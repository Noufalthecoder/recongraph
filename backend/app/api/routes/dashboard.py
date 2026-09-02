"""
Dashboard summary and KPI endpoints.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from backend.app.api.demo_state import demo_state
from backend.app.api.schemas import (
    DashboardKPIs,
    DashboardResponse,
    ExceptionSummaryItem,
)

router = APIRouter(prefix="/api", tags=["dashboard"])


def _fmt_money(val: Any) -> Optional[str]:
    if val is None:
        return None
    try:
        d = Decimal(str(val))
        if d < 0:
            return f"-₹{abs(d):,.2f}"
        return f"₹{d:,.2f}"
    except Exception:
        return str(val)


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard():
    bundle = demo_state.active_scenario
    obs = bundle.observed_world
    res = bundle.recon_result

    total_records = (
        len(obs.merchants)
        + len(obs.orders)
        + len(obs.payments)
        + len(obs.refunds)
        + len(obs.adjustments)
        + len(obs.transfers)
        + len(obs.settlement_transactions)
        + len(obs.settlements)
        + len(obs.bank_entries)
    )

    settlement_count = len(obs.settlements)
    reconciled_count = res.metrics.reconciled_settlements_count
    exception_count = res.metrics.total_exceptions_count
    unmatched_count = res.metrics.unmatched_settlements_count + res.metrics.unmatched_bank_entries_count

    # Reconciliation rate
    rate_val = res.metrics.settlement_reconciliation_rate * Decimal("100.0")
    rate_str = f"{rate_val:.1f}%"

    # Total settlement and bank values
    tot_setl = sum((s.amount for s in obs.settlements), Decimal("0.00"))
    tot_bank = sum((b.amount for b in obs.bank_entries), Decimal("0.00"))

    # Benchmark metrics
    bm = demo_state.benchmark_result
    f1_str = f"{bm.aggregate_metrics.f1:.2f}"
    prec_str = f"{bm.aggregate_metrics.precision:.2f}"
    rec_str = f"{bm.aggregate_metrics.recall:.2f}"
    clean_rate_str = f"{(bm.clean_reconciliation_rate * 100):.1f}%"
    rps = int(bm.performance.records_per_second)
    rps_display = f"{rps:,} rec/s"

    kpis = DashboardKPIs(
        active_scenario=bundle.scenario_id,
        active_scenario_label=bundle.name,
        total_records=total_records,
        settlement_count=settlement_count,
        reconciled_count=reconciled_count,
        exception_count=exception_count,
        unmatched_count=unmatched_count,
        reconciliation_rate=rate_str,
        total_settlement_value=f"₹{tot_setl:,.2f}",
        total_bank_value=f"₹{tot_bank:,.2f}",
        benchmark_f1=f1_str,
        benchmark_precision=prec_str,
        benchmark_recall=rec_str,
        benchmark_clean_rate=clean_rate_str,
        throughput_display=rps_display,
    )

    # Settlement health breakdown
    settlement_health = {
        "RECONCILED": reconciled_count,
        "EXCEPTION": res.metrics.exception_settlements_count,
        "UNMATCHED": res.metrics.unmatched_settlements_count,
    }

    # Exception distribution
    dist: Dict[str, int] = {}
    recent_exceptions: List[ExceptionSummaryItem] = []

    for exc in res.exceptions:
        rule = exc.rule_code
        dist[rule] = dist.get(rule, 0) + 1

        setl_id = None
        if exc.primary_entity.entity_type == "settlement":
            setl_id = exc.primary_entity.entity_id
        else:
            for rel in exc.related_entities:
                if rel.entity_type == "settlement":
                    setl_id = rel.entity_id
                    break

        recent_exceptions.append(
            ExceptionSummaryItem(
                exception_id=exc.exception_id,
                rule_code=exc.rule_code,
                severity=exc.severity.value if hasattr(exc.severity, "value") else str(exc.severity),
                entity_type=exc.primary_entity.entity_type,
                entity_id=exc.primary_entity.entity_id,
                settlement_id=setl_id,
                expected_value=_fmt_money(exc.expected_value),
                observed_value=_fmt_money(exc.observed_value),
                difference=_fmt_money(exc.difference),
                description=exc.evidence.rule_description if exc.evidence else rule,
            )
        )

    return DashboardResponse(
        kpis=kpis,
        settlement_health=settlement_health,
        exception_distribution=dist,
        recent_exceptions=recent_exceptions,
    )
