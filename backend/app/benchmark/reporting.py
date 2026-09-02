"""
Reporting utilities for structured and human-readable benchmark outcomes.
"""

from typing import Any, Dict
from backend.app.benchmark.models import BenchmarkRunResult


class BenchmarkReporter:
    """Formats BenchmarkRunResult into JSON-serializable dictionaries and ASCII summary tables."""

    @classmethod
    def to_dict(cls, result: BenchmarkRunResult) -> Dict[str, Any]:
        """Converts BenchmarkRunResult to a JSON-compatible dictionary."""
        return result.model_dump(mode="json")

    @classmethod
    def to_text_report(cls, result: BenchmarkRunResult) -> str:
        """Generates a human-readable text report from BenchmarkRunResult."""
        agg = result.aggregate_metrics
        perf = result.performance

        lines = [
            "==================================================",
            "RECONGRAPH BENCHMARK REPORT",
            "==================================================",
            f"Run ID:                    {result.run_id}",
            f"Total Records Processed:   {agg.total_records}",
            f"Total Scenarios Evaluated: {len(result.scenario_results)}",
            f"Expected Anomalies:        {agg.total_expected_anomalies}",
            f"Detected Issues:           {agg.total_detected_issues}",
            f"True Positives (TP):       {agg.true_positives}",
            f"False Positives (FP):      {agg.false_positives}",
            f"False Negatives (FN):      {agg.false_negatives}",
            "--------------------------------------------------",
            f"Overall Precision:         {agg.precision * 100:.2f}%",
            f"Overall Recall:            {agg.recall * 100:.2f}%",
            f"Overall F1 Score:          {agg.f1 * 100:.2f}%",
            f"Clean Reconciliation Rate: {result.clean_reconciliation_rate * 100:.2f}%",
            f"Reconciliation Rate:       {agg.reconciliation_rate * 100:.2f}%",
            f"Execution Time:            {perf.elapsed_seconds:.4f}s",
            f"Throughput:                {perf.records_per_second:.2f} records/sec",
            "==================================================",
            "",
            "ANOMALY BREAKDOWN",
            "--------------------------------------------------",
        ]

        for anom_type, b in sorted(result.anomaly_breakdown.items()):
            lines.append(
                f"{anom_type:<22} | Exp: {b.expected_count:>2} | Det: {b.detected_count:>2} | "
                f"TP: {b.tp:>2} | FP: {b.fp:>2} | FN: {b.fn:>2} | "
                f"P: {b.precision * 100:>6.2f}% | R: {b.recall * 100:>6.2f}% | F1: {b.f1 * 100:>6.2f}%"
            )

        lines.extend([
            "--------------------------------------------------",
            "",
            "SCENARIO BREAKDOWN",
            "--------------------------------------------------",
            f"{'Scenario':<34} | {'Recs':>4} | {'Exp':>3} | {'TP':>2} | {'FP':>2} | {'FN':>2} | {'P':>7} | {'R':>7} | {'F1':>7} | {'Status':<12}",
            "--------------------------------------------------------------------------------------------------------------------",
        ])

        for sc in result.scenario_results:
            m = sc.metrics
            lines.append(
                f"{sc.scenario_name:<34} | {sc.total_records:>4} | {m.total_expected_anomalies:>3} | "
                f"{m.true_positives:>2} | {m.false_positives:>2} | {m.false_negatives:>2} | "
                f"{m.precision * 100:>6.2f}% | {m.recall * 100:>6.2f}% | {m.f1 * 100:>6.2f}% | {sc.reconciliation_status:<12}"
            )

        lines.append("==================================================")
        return "\n".join(lines)
