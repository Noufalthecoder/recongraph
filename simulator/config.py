"""
Simulation Configuration.
"""

from datetime import date
from pydantic import BaseModel, ConfigDict

class SimulationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    seed: int
    merchant_count: int
    start_date: date
    end_date: date
    order_count: int
    scenario_type: str = "minimal_lifecycle_v1"
