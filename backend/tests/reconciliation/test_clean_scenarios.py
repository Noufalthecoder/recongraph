"""
Tests for Core Deterministic Reconciliation on all 6 clean scenarios.
"""

from datetime import date
from decimal import Decimal
import pytest

from backend.app.reconciliation import DeterministicReconciliationEngine, ReconciliationConfig
from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import ObservationConfig, ObservationGenerator


def get_clean_observed_world(scenario_type: str, seed: int = 42):
    sim_config = SimulationConfig(
        seed=seed,
        merchant_count=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        order_count=1,
        scenario_type=scenario_type,
        fee_rate=Decimal("0.02"),
        tax_rate=Decimal("0.18"),
        rounding_mode="ROUND_HALF_UP",
    )
    gt = Simulator(sim_config).run()
    obs_world, _ = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=seed))
    return obs_world


@pytest.mark.parametrize(
    "scenario_name,expected_settlement_count",
    [
        ("minimal_lifecycle_v1", 1),
        ("many_to_one_v1", 1),
        ("many_to_one_with_fee_tax_v1", 1),
        ("refund_v1", 2),
        ("multiple_refunds_v1", 4),
        ("adjustment_v1", 1),
    ],
)
def test_all_six_clean_scenarios_reconcile_completely(scenario_name: str, expected_settlement_count: int):
    """
    Verifies that all 6 supported synthetic scenarios reconcile completely (100% rate, 0 exceptions)
    when observed without anomalies.
    """
    obs = get_clean_observed_world(scenario_name)
    engine = DeterministicReconciliationEngine()
    result = engine.reconcile(obs, ReconciliationConfig())

    assert result.status == "RECONCILED", f"Scenario {scenario_name} failed: {result.summary}"
    assert len(result.exceptions) == 0, f"Scenario {scenario_name} had unexpected exceptions: {result.exceptions}"
    assert len(result.settlements) == expected_settlement_count
    assert result.metrics.settlement_reconciliation_rate == Decimal("1.0000")
    assert result.metrics.reconciled_settlements_count == expected_settlement_count
    assert result.metrics.exception_settlements_count == 0

    for s in result.settlements:
        assert s.status == "RECONCILED"
        assert s.difference == Decimal("0.00")
        assert s.bank_entry_id is not None
        assert s.utr is not None
        assert len(s.exceptions) == 0
        assert len(s.matches) >= 2  # Composition match + Bank match
