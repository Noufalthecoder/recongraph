"""
Simulation Configuration.
"""

from datetime import date
from pydantic import BaseModel, ConfigDict
from decimal import Decimal

class SimulationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    seed: int
    merchant_count: int
    start_date: date
    end_date: date
    order_count: int
    scenario_type: str = "minimal_lifecycle_v1"
    
    fee_rate: Decimal = Decimal("0.02")
    tax_rate: Decimal = Decimal("0.18")
    rounding_mode: str = "ROUND_HALF_UP"
