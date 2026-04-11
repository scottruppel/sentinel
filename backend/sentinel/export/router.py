from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.db.session import get_session
from sentinel.export.report import generate_risk_report, generate_scenario_report

router = APIRouter(tags=["export"])


@router.get("/export/risk-report/{bom_id}")
async def risk_report(
    bom_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    try:
        md = await generate_risk_report(session, bom_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return PlainTextResponse(md, media_type="text/markdown")


@router.get("/export/scenario-report/{scenario_id}")
async def scenario_report(
    scenario_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    try:
        md = await generate_scenario_report(session, scenario_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return PlainTextResponse(md, media_type="text/markdown")
