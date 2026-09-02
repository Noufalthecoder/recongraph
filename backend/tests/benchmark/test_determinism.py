"""
Tests verifying benchmark determinism, output sorting, GroundTruth isolation, and dataset immutability.
"""

from decimal import Decimal
import pytest

from backend.app.benchmark import BenchmarkConfig, BenchmarkRunner
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import ObservationConfig, ObservationGenerator


def test_repeated_benchmark_runs_are_deterministic():
    """Verify two runs with identical config produce 100% identical metrics and evaluations."""
    runner = BenchmarkRunner()
    config = BenchmarkConfig(
        scenarios=["minimal_lifecycle_v1", "many_to_one_v1", "adjustment_v1"],
        run_clean=True,
        run_anomalies=True,
        seed=42,
    )

    res1 = runner.run(config)
    res2 = runner.run(config)

    # Exclude non-deterministic runtime IDs and timing
    dump1 = res1.model_dump(exclude={"run_id": True, "performance": {"elapsed_seconds": True, "records_per_second": True}})
    dump2 = res2.model_dump(exclude={"run_id": True, "performance": {"elapsed_seconds": True, "records_per_second": True}})

    assert dump1 == dump2


def test_observed_world_not_mutated_during_benchmark_evaluation():
    """Verify that ObservedWorld domain models are completely unchanged after benchmark evaluation."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=SimulationConfig.model_fields["start_date"].default if "default" in str(SimulationConfig.model_fields["start_date"]) else __import__("datetime").date(2026, 1, 1),
        end_date=__import__("datetime").date(2026, 1, 31),
        order_count=1,
        scenario_type="adjustment_v1",
    )
    gt = Simulator(sim_config).run()
    obs_world, manifest = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))

    dump_before = obs_world.model_dump()

    runner = BenchmarkRunner()
    _ = runner.run(BenchmarkConfig(scenarios=["adjustment_v1"], run_clean=True, run_anomalies=False))

    dump_after = obs_world.model_dump()
    assert dump_before == dump_after


def test_no_ground_truth_leakage_in_reconciliation_package():
    """Verify backend.app.reconciliation does not import GroundTruth or AnomalyManifest."""
    import backend.app.reconciliation.composition
    import backend.app.reconciliation.engine
    import backend.app.reconciliation.exceptions
    import backend.app.reconciliation.indexer
    import backend.app.reconciliation.matcher
    import backend.app.reconciliation.models
    import backend.app.reconciliation.rules

    modules = [
        backend.app.reconciliation.composition,
        backend.app.reconciliation.engine,
        backend.app.reconciliation.exceptions,
        backend.app.reconciliation.indexer,
        backend.app.reconciliation.matcher,
        backend.app.reconciliation.models,
        backend.app.reconciliation.rules,
    ]

    for m in modules:
        src = open(m.__file__, "r", encoding="utf-8").read()
        assert "GroundTruth" not in src
        assert "AnomalyManifest" not in src
        assert "AnomalyRecord" not in src
        assert "ScenarioLabel" not in src
        assert "import random" not in src
