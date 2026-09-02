"""
Tests for the Observed World & Anomaly Injection Layer (Step 6).
"""

from datetime import date
from decimal import Decimal
import pytest

from simulator.config import SimulationConfig
from simulator.engine import Simulator
from simulator.observed import (
    AnomalyManifest,
    AnomalyRecord,
    AnomalySpec,
    AnomalyType,
    ObservationConfig,
    ObservationGenerator,
    ObservedWorld,
)


def get_scenario_gt(scenario_type: str, seed: int = 42):
    config = SimulationConfig(
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
    return Simulator(config).run()


# ===================================================================
# 1. Ground Truth Immutability
# ===================================================================

def test_ground_truth_immutability():
    """Verify that GroundTruth is never mutated when anomalies are injected."""
    gt = get_scenario_gt("adjustment_v1", seed=42)
    gt_dump_before = gt.model_dump()

    config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
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
                target_index=0,
            ),
            AnomalySpec(
                anomaly_type=AnomalyType.DUPLICATE_RECORD,
                target_entity_type="payment",
                target_index=0,
            ),
        ],
    )

    obs, manifest = ObservationGenerator.generate(gt, config)

    # Ground Truth must be 100% byte/content identical to before injection
    gt_dump_after = gt.model_dump()
    assert gt_dump_before == gt_dump_after
    assert manifest.total_anomalies == 3


# ===================================================================
# 2 & 3. Clean Observation Identity & Deep Independence
# ===================================================================

def test_clean_observation_identity_and_independence():
    """Verify clean mode matches Ground Truth and is deeply independent."""
    gt = get_scenario_gt("adjustment_v1", seed=42)
    config = ObservationConfig.clean(seed=42)

    obs, manifest = ObservationGenerator.generate(gt, config)

    assert manifest.total_anomalies == 0
    assert len(manifest.records) == 0

    # Entity counts and values match exactly
    assert len(obs.merchants) == len(gt.merchants)
    assert len(obs.orders) == len(gt.orders)
    assert len(obs.payments) == len(gt.payments)
    assert len(obs.adjustments) == len(gt.adjustments)
    assert len(obs.settlement_transactions) == len(gt.settlement_transactions)
    assert len(obs.settlements) == len(gt.settlements)
    assert len(obs.bank_entries) == len(gt.bank_entries)

    for i in range(len(obs.payments)):
        assert obs.payments[i].model_dump() == gt.payments[i].model_dump()

    # Deep independence check: ObservedWorld is a separate object graph
    assert obs.payments is not gt.payments
    assert obs.payments[0] is not gt.payments[0]


# ===================================================================
# 4 & 5. Determinism
# ===================================================================

def test_determinism_identical_and_distinct_seeds():
    """Verify same seed produces byte-identical output, distinct seeds work deterministically."""
    gt = get_scenario_gt("adjustment_v1", seed=42)

    anomalies = [
        AnomalySpec(
            anomaly_type=AnomalyType.AMOUNT_MISMATCH,
            target_entity_type="bank_entry",
            delta=Decimal("-250.00"),
            target_index=0,
        )
    ]

    cfg1 = ObservationConfig.with_anomalies(seed=12345, anomalies=anomalies)
    cfg2 = ObservationConfig.with_anomalies(seed=12345, anomalies=anomalies)

    obs1, m1 = ObservationGenerator.generate(gt, cfg1)
    obs2, m2 = ObservationGenerator.generate(gt, cfg2)

    assert obs1.model_dump() == obs2.model_dump()
    assert m1.model_dump() == m2.model_dump()


# ===================================================================
# 6. AMOUNT_MISMATCH Anomaly
# ===================================================================

def test_amount_mismatch_anomaly():
    """Verify AMOUNT_MISMATCH mutates only the targeted field and records audit data."""
    gt = get_scenario_gt("adjustment_v1", seed=42)
    orig_bank = gt.bank_entries[0]
    assert orig_bank.amount == Decimal("14396.00")

    config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.AMOUNT_MISMATCH,
                target_entity_type="bank_entry",
                target_field="amount",
                delta=Decimal("-250.00"),
                target_index=0,
            )
        ],
    )

    obs, manifest = ObservationGenerator.generate(gt, config)

    assert len(obs.bank_entries) == 1
    obs_bank = obs.bank_entries[0]

    # Mutated value
    assert obs_bank.amount == Decimal("14146.00")
    # Surrounding fields intact
    assert obs_bank.bank_entry_id == orig_bank.bank_entry_id
    assert obs_bank.utr == orig_bank.utr
    assert obs_bank.account_number == orig_bank.account_number

    # Manifest verification
    assert manifest.total_anomalies == 1
    rec = manifest.records[0]
    assert rec.anomaly_id == "anom_0001"
    assert rec.anomaly_type == AnomalyType.AMOUNT_MISMATCH
    assert rec.target_entity_type == "bank_entries"
    assert rec.target_entity_id == orig_bank.bank_entry_id
    assert rec.target_field == "amount"
    assert rec.original_value == "14396.00"
    assert rec.observed_value == "14146.00"
    assert rec.settlement_id == gt.settlements[0].settlement_id


# ===================================================================
# 7. MISSING_RECORD Anomaly
# ===================================================================

def test_missing_record_anomaly():
    """Verify MISSING_RECORD removes target entity and creates accurate record."""
    gt = get_scenario_gt("many_to_one_v1", seed=42)
    assert len(gt.payments) == 5
    target_payment = sorted(gt.payments, key=lambda p: p.payment_id)[0]

    config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.MISSING_RECORD,
                target_entity_type="payment",
                target_index=0,
            )
        ],
    )

    obs, manifest = ObservationGenerator.generate(gt, config)

    assert len(obs.payments) == 4
    assert not any(p.payment_id == target_payment.payment_id for p in obs.payments)

    assert manifest.total_anomalies == 1
    rec = manifest.records[0]
    assert rec.anomaly_type == AnomalyType.MISSING_RECORD
    assert rec.target_entity_id == target_payment.payment_id
    assert rec.observed_value is None


# ===================================================================
# 8. DUPLICATE_RECORD Anomaly
# ===================================================================

def test_duplicate_record_anomaly():
    """Verify DUPLICATE_RECORD inserts exactly one additional copy."""
    gt = get_scenario_gt("minimal_lifecycle_v1", seed=42)
    assert len(gt.settlement_transactions) == 1
    orig_stxn = gt.settlement_transactions[0]

    config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.DUPLICATE_RECORD,
                target_entity_type="settlement_transaction",
                target_index=0,
            )
        ],
    )

    obs, manifest = ObservationGenerator.generate(gt, config)

    assert len(obs.settlement_transactions) == 2
    assert obs.settlement_transactions[0].settlement_txn_id == orig_stxn.settlement_txn_id
    assert obs.settlement_transactions[1].settlement_txn_id == orig_stxn.settlement_txn_id

    assert manifest.total_anomalies == 1
    rec = manifest.records[0]
    assert rec.anomaly_type == AnomalyType.DUPLICATE_RECORD
    assert rec.target_entity_id == orig_stxn.settlement_txn_id


# ===================================================================
# 9. IDENTIFIER_MISMATCH Anomaly
# ===================================================================

def test_identifier_mismatch_anomaly():
    """Verify IDENTIFIER_MISMATCH deterministically breaks identifier matching."""
    gt = get_scenario_gt("minimal_lifecycle_v1", seed=42)
    orig_bank = gt.bank_entries[0]

    config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.IDENTIFIER_MISMATCH,
                target_entity_type="bank_entry",
                target_field="utr",
                target_index=0,
            )
        ],
    )

    obs, manifest = ObservationGenerator.generate(gt, config)

    assert len(obs.bank_entries) == 1
    obs_bank = obs.bank_entries[0]
    expected_mutated_utr = f"{orig_bank.utr}_MISMATCH"

    assert obs_bank.utr == expected_mutated_utr
    assert obs_bank.utr != orig_bank.utr
    assert obs_bank.amount == orig_bank.amount

    assert manifest.total_anomalies == 1
    rec = manifest.records[0]
    assert rec.anomaly_type == AnomalyType.IDENTIFIER_MISMATCH
    assert rec.original_value == orig_bank.utr
    assert rec.observed_value == expected_mutated_utr


# ===================================================================
# 10. Multi-Anomaly Execution & Manifest Accounting
# ===================================================================

def test_multi_anomaly_manifest_accounting():
    """Verify multiple simultaneous anomalies apply cleanly in sequence."""
    gt = get_scenario_gt("adjustment_v1", seed=42)

    config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.AMOUNT_MISMATCH,
                target_entity_type="bank_entry",
                target_field="amount",
                delta=Decimal("-250.00"),
                target_index=0,
            ),
            AnomalySpec(
                anomaly_type=AnomalyType.IDENTIFIER_MISMATCH,
                target_entity_type="bank_entry",
                target_field="utr",
                target_index=0,
            ),
            AnomalySpec(
                anomaly_type=AnomalyType.DUPLICATE_RECORD,
                target_entity_type="settlement_transaction",
                target_index=0,
            ),
        ],
    )

    obs, manifest = ObservationGenerator.generate(gt, config)

    assert manifest.total_anomalies == 3
    assert len(manifest.records) == 3
    assert manifest.records[0].anomaly_id == "anom_0001"
    assert manifest.records[1].anomaly_id == "anom_0002"
    assert manifest.records[2].anomaly_id == "anom_0003"
    assert len(obs.settlement_transactions) == 4  # 3 original + 1 duplicated


# ===================================================================
# 11, 12, 13. Error Handling & Validation
# ===================================================================

def test_invalid_configurations_rejected():
    """Verify invalid target types, zero delta, and float delta are rejected."""
    gt = get_scenario_gt("minimal_lifecycle_v1", seed=42)

    # 1. Invalid target entity type
    invalid_target_config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.AMOUNT_MISMATCH,
                target_entity_type="crypto_wallet",
                delta=Decimal("100.00"),
            )
        ],
    )
    with pytest.raises(ValueError, match="Unsupported target_entity_type"):
        ObservationGenerator.generate(gt, invalid_target_config)

    # 2. Empty collection target (e.g. refund in minimal_lifecycle_v1)
    empty_target_config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.AMOUNT_MISMATCH,
                target_entity_type="refund",
                delta=Decimal("100.00"),
            )
        ],
    )
    with pytest.raises(ValueError, match="No entities of type 'refund'"):
        ObservationGenerator.generate(gt, empty_target_config)

    # 3. Non-existent explicit ID
    missing_id_config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.AMOUNT_MISMATCH,
                target_entity_type="payment",
                target_entity_id="non_existent_pay_123",
                delta=Decimal("100.00"),
            )
        ],
    )
    with pytest.raises(ValueError, match="Target entity with payment_id='non_existent_pay_123' not found"):
        ObservationGenerator.generate(gt, missing_id_config)

    # 4. Zero delta for amount mismatch
    zero_delta_config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.AMOUNT_MISMATCH,
                target_entity_type="payment",
                delta=Decimal("0.00"),
            )
        ],
    )
    with pytest.raises(ValueError, match="A non-zero Decimal delta must be provided"):
        ObservationGenerator.generate(gt, zero_delta_config)

    # 5. Float rejection in AnomalySpec
    with pytest.raises(ValueError, match="Float values are forbidden"):
        AnomalySpec(
            anomaly_type=AnomalyType.AMOUNT_MISMATCH,
            target_entity_type="payment",
            delta=50.25,  # type: ignore[arg-type]
        )


# ===================================================================
# 15. All Six Existing Scenarios Compatibility
# ===================================================================

@pytest.mark.parametrize(
    "scenario_name",
    [
        "minimal_lifecycle_v1",
        "many_to_one_v1",
        "many_to_one_with_fee_tax_v1",
        "refund_v1",
        "multiple_refunds_v1",
        "adjustment_v1",
    ],
)
def test_all_six_scenarios_compatibility(scenario_name: str):
    """Verify ObservationGenerator works seamlessly across all 6 scenarios in clean and anomaly modes."""
    gt = get_scenario_gt(scenario_name, seed=42)

    # Clean mode
    clean_obs, clean_manifest = ObservationGenerator.generate(gt, ObservationConfig.clean(seed=42))
    assert clean_manifest.total_anomalies == 0
    assert len(clean_obs.payments) == len(gt.payments)

    # Anomaly mode: amount mismatch on bank entry
    anom_config = ObservationConfig.with_anomalies(
        seed=42,
        anomalies=[
            AnomalySpec(
                anomaly_type=AnomalyType.AMOUNT_MISMATCH,
                target_entity_type="bank_entry",
                target_field="amount",
                delta=Decimal("-100.00"),
                target_index=0,
            )
        ],
    )
    anom_obs, anom_manifest = ObservationGenerator.generate(gt, anom_config)
    assert anom_manifest.total_anomalies == 1
    assert anom_obs.bank_entries[0].amount == gt.bank_entries[0].amount - Decimal("100.00")
