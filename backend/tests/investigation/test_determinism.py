"""
Tests verifying investigation determinism, immutability, and GroundTruth import isolation.
"""

from datetime import date
import pytest

from backend.app.investigation import InvestigationService
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import ObservationConfig, ObservationGenerator


def test_repeated_investigation_is_deterministic():
    """Verify running the same investigation twice produces byte-identical answers."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=2,
        scenario_type="adjustment_v1",
    )
    gt = Simulator(sim_config).run()
    obs_world, _ = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))

    service = InvestigationService()
    setl_id = obs_world.settlements[0].settlement_id
    q = f"Why is settlement {setl_id} reconciling?"

    ans1 = service.investigate(obs_world, question=q)
    ans2 = service.investigate(obs_world, question=q)

    assert ans1.model_dump() == ans2.model_dump()


def test_observed_world_immutability_during_investigation():
    """Verify ObservedWorld is completely unchanged after investigation."""
    sim_config = SimulationConfig(
        seed=42,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1,
        scenario_type="minimal_lifecycle_v1",
    )
    gt = Simulator(sim_config).run()
    obs_world, _ = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))

    snap_before = obs_world.model_dump()

    service = InvestigationService()
    _ = service.investigate(obs_world, question="Explain this settlement.")

    snap_after = obs_world.model_dump()
    assert snap_before == snap_after


def test_no_ground_truth_or_anomaly_leakage_in_investigation_package():
    """Verify investigation package does not import GroundTruth, AnomalyManifest, or random."""
    import backend.app.investigation.agent
    import backend.app.investigation.context
    import backend.app.investigation.guardrails
    import backend.app.investigation.models
    import backend.app.investigation.prompts
    import backend.app.investigation.providers
    import backend.app.investigation.service
    import backend.app.investigation.tools

    modules = [
        backend.app.investigation.agent,
        backend.app.investigation.context,
        backend.app.investigation.guardrails,
        backend.app.investigation.models,
        backend.app.investigation.prompts,
        backend.app.investigation.providers,
        backend.app.investigation.service,
        backend.app.investigation.tools,
    ]

    for m in modules:
        src = open(m.__file__, "r", encoding="utf-8").read()
        assert "GroundTruth" not in src
        assert "AnomalyManifest" not in src
        assert "AnomalyRecord" not in src
        assert "ScenarioLabel" not in src
        assert "import random" not in src
