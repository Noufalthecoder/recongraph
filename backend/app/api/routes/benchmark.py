"""
Benchmark evaluation metrics route.
"""

from typing import List
from fastapi import APIRouter
from backend.app.api.demo_state import demo_state
from backend.app.api.schemas import (
    BenchmarkAnomalyRow,
    BenchmarkResponseDTO,
)

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])


@router.get("", response_model=BenchmarkResponseDTO)
def get_benchmark():
    bm = demo_state.benchmark_result
    m = bm.aggregate_metrics
    p = bm.performance

    breakdown_rows: List[BenchmarkAnomalyRow] = []
    for atype_key, at_res in bm.anomaly_breakdown.items():
        breakdown_rows.append(
            BenchmarkAnomalyRow(
                anomaly_type=at_res.anomaly_type,
                expected_count=at_res.expected_count,
                detected_count=at_res.detected_count,
                true_positives=at_res.tp,
                false_positives=at_res.fp,
                false_negatives=at_res.fn,
                precision=f"{at_res.precision:.2f}",
                recall=f"{at_res.recall:.2f}",
                f1=f"{at_res.f1:.2f}",
            )
        )

    rps = int(p.records_per_second)

    return BenchmarkResponseDTO(
        total_records_processed=p.total_records,
        total_scenarios_evaluated=len(bm.scenario_results),
        total_expected_anomalies=m.total_expected_anomalies,
        total_detected_issues=m.total_detected_issues,
        true_positives=m.true_positives,
        false_positives=m.false_positives,
        false_negatives=m.false_negatives,
        precision=f"{m.precision:.2f}",
        recall=f"{m.recall:.2f}",
        f1=f"{m.f1:.2f}",
        clean_reconciliation_rate=f"{(bm.clean_reconciliation_rate * 100):.1f}%",
        records_per_second=f"{rps:,} rec/s",
        elapsed_seconds=f"{p.elapsed_seconds:.3f}s",
        anomaly_breakdown=breakdown_rows,
        isolation_note="Ground Truth is used strictly by the isolated benchmark evaluation harness. The reconciliation engine and AI investigator operate purely on Observed World evidence.",
    )
