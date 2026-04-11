from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.db.models import Scenario
from sentinel.db.session import get_session
from sentinel.whatif.engine import run_scenario
from sentinel.whatif.scenarios import SCENARIO_TEMPLATES

log = structlog.get_logger()
router = APIRouter(tags=["scenarios"])


class ScenarioCreate(BaseModel):
    name: str
    description: str | None = None
    scenario_type: str
    parameters: dict
    affected_bom_ids: list[str] | None = None


@router.post("/scenarios")
async def create_scenario(
    body: ScenarioCreate,
    session: AsyncSession = Depends(get_session),
):
    bom_ids = [UUID(bid) for bid in body.affected_bom_ids] if body.affected_bom_ids else None

    scenario = Scenario(
        name=body.name,
        description=body.description,
        scenario_type=body.scenario_type,
        parameters=body.parameters,
        affected_bom_ids=bom_ids,
        status="draft",
    )
    session.add(scenario)
    await session.flush()

    try:
        results = await run_scenario(session, scenario)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "id": str(scenario.id),
        "name": scenario.name,
        "status": scenario.status,
        "summary": results.get("summary"),
    }


@router.get("/scenarios")
async def list_scenarios(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Scenario).order_by(Scenario.created_at.desc()))
    scenarios = result.scalars().all()
    return [_scenario_dict(s) for s in scenarios]


@router.get("/scenarios/templates")
async def get_templates():
    return SCENARIO_TEMPLATES


@router.get("/scenarios/{scenario_id}")
async def get_scenario(
    scenario_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    scenario = await session.get(Scenario, scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    return _scenario_dict(scenario)


@router.get("/scenarios/{scenario_id}/results")
async def get_results(
    scenario_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    scenario = await session.get(Scenario, scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    if not scenario.results:
        raise HTTPException(404, "Scenario has no results yet")

    return {
        "scenario_id": str(scenario.id),
        "name": scenario.name,
        **scenario.results,
    }


@router.delete("/scenarios/{scenario_id}")
async def delete_scenario(
    scenario_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    scenario = await session.get(Scenario, scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    await session.delete(scenario)
    await session.commit()
    return {"status": "deleted"}


def _scenario_dict(s: Scenario) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "description": s.description,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "scenario_type": s.scenario_type,
        "parameters": s.parameters,
        "affected_bom_ids": [str(bid) for bid in s.affected_bom_ids] if s.affected_bom_ids else None,
        "status": s.status,
        "summary": s.results.get("summary") if s.results else None,
    }
