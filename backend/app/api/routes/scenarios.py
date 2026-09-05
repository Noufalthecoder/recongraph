"""
Demo scenario listing and switching routes.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from backend.app.api.demo_state import demo_state
from backend.app.api.schemas import ScenarioInfo, ScenarioListResponse

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("", response_model=ScenarioListResponse)
def list_scenarios(x_scenario_id: Optional[str] = Header(None)):
    catalog = demo_state.scenarios_catalog
    active_id = x_scenario_id or "production_demo"

    items = []
    for sc_id, bundle in catalog.items():
        obs = bundle.observed_world
        rec_count = (
            len(obs.merchants)
            + len(obs.orders)
            + len(obs.payments)
            + len(obs.refunds)
            + len(obs.adjustments)
            + len(obs.transfers)
            + len(obs.settlement_transactions)
            + len(obs.settlements)
            + len(obs.bank_entries)
        )
        items.append(
            ScenarioInfo(
                scenario_id=sc_id,
                name=bundle.name,
                description=bundle.description,
                record_count=rec_count,
                has_anomalies=bundle.has_anomalies,
                is_active=(sc_id == active_id),
            )
        )

    return ScenarioListResponse(scenarios=items, active_scenario_id=active_id)


@router.post("/{scenario_id}/load", response_model=ScenarioListResponse)
def load_scenario(scenario_id: str):
    if scenario_id not in demo_state.scenarios_catalog:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario_id}' not found in demo catalog.",
        )
    return list_scenarios(x_scenario_id=scenario_id)
