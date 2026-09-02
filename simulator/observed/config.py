"""
Configuration models for Observation Generation and Anomaly Injection.
"""

from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator

from simulator.observed.models import AnomalyType
from backend.app.models.common import _coerce_to_decimal


class AnomalySpec(BaseModel):
    """
    Specification for a single controlled anomaly injection.
    """
    model_config = ConfigDict(frozen=True)

    anomaly_type: AnomalyType
    target_entity_type: str  # "payment", "bank_entry", "settlement_transaction", etc.
    target_field: Optional[str] = None  # e.g., "amount", "utr", etc.
    delta: Optional[Decimal] = None  # Monetary delta for AMOUNT_MISMATCH
    target_index: int = 0  # Deterministic index in sorted candidate list
    target_entity_id: Optional[str] = None  # Optional explicit entity ID target

    @field_validator("delta", mode="before")
    @classmethod
    def validate_delta(cls, v: object) -> Optional[Decimal]:
        if v is None:
            return None
        return _coerce_to_decimal(v)


class ObservationConfig(BaseModel):
    """
    Configuration governing the generation of ObservedWorld.
    """
    model_config = ConfigDict(frozen=True)

    seed: int
    anomalies_enabled: bool = False
    anomalies: List[AnomalySpec] = []

    @classmethod
    def clean(cls, seed: int = 42) -> "ObservationConfig":
        """Convenience factory for clean (un-corrupted) observations."""
        return cls(seed=seed, anomalies_enabled=False, anomalies=[])

    @classmethod
    def with_anomalies(cls, seed: int, anomalies: List[AnomalySpec]) -> "ObservationConfig":
        """Convenience factory for controlled anomaly injection."""
        return cls(seed=seed, anomalies_enabled=True, anomalies=anomalies)
