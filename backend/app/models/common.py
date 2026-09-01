"""
Shared types, validators, and base configuration for ReconGraph domain models.

All monetary values use decimal.Decimal — binary floating-point is forbidden.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, field_validator, BeforeValidator


# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------

class Currency(str, Enum):
    """Supported currencies. Currently INR-only per data contract."""
    INR = "INR"


# ---------------------------------------------------------------------------
# Monetary amount validator
# ---------------------------------------------------------------------------

def _coerce_to_decimal(value: object) -> Decimal:
    """
    Accept Decimal, int, or str and coerce to Decimal.

    Rejects float to prevent silent precision loss.
    Raises ValueError on invalid input.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        raise ValueError(
            f"Float values are forbidden for monetary amounts. "
            f"Use Decimal or str instead. Got: {value!r}"
        )
    if isinstance(value, (int, str)):
        try:
            return Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError(
                f"Cannot convert {value!r} to Decimal: {exc}"
            ) from exc
    raise ValueError(
        f"Unsupported type for monetary amount: {type(value).__name__}. "
        f"Expected Decimal, int, or str."
    )


# Annotated type for monetary amounts — use in model field definitions.
MoneyDecimal = Annotated[Decimal, BeforeValidator(_coerce_to_decimal)]


# ---------------------------------------------------------------------------
# Base model configuration
# ---------------------------------------------------------------------------

class FinancialBaseModel(BaseModel):
    """
    Base model for all ReconGraph financial entities.

    - Frozen (immutable) by default.
    - Strict type coercion disabled to allow Decimal from str/int.
    - Serialization preserves Decimal as str to avoid float conversion.
    """
    model_config = ConfigDict(
        frozen=True,
        use_enum_values=True,
        ser_json_timedelta="float",
        populate_by_name=True,
    )
