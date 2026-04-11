from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.db.models import Component, EnrichmentRecord
from sentinel.db.session import get_session
from sentinel.enrichment.nexar import NexarProvider
from sentinel.enrichment.orchestrator import EnrichmentOrchestrator
from sentinel.enrichment.siliconexpert import SiliconExpertProvider
from sentinel.enrichment.z2data import Z2DataProvider

log = structlog.get_logger()
router = APIRouter(tags=["enrichment"])


def _get_orchestrator() -> EnrichmentOrchestrator:
    providers = [NexarProvider(), SiliconExpertProvider(), Z2DataProvider()]
    return EnrichmentOrchestrator(providers)


@router.post("/enrichment/run/{bom_id}")
async def run_enrichment(
    bom_id: UUID,
    force: bool = False,
    session: AsyncSession = Depends(get_session),
):
    orchestrator = _get_orchestrator()
    stats = await orchestrator.enrich_bom(session, bom_id, force_refresh=force)
    return {"bom_id": str(bom_id), "status": "complete", **stats}


@router.get("/enrichment/status/{bom_id}")
async def enrichment_status(
    bom_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Component.id).where(Component.bom_id == bom_id)
    )
    component_ids = [r[0] for r in result.all()]
    if not component_ids:
        raise HTTPException(404, "BOM not found or has no components")

    enriched_result = await session.execute(
        select(EnrichmentRecord.component_id)
        .where(EnrichmentRecord.component_id.in_(component_ids))
        .distinct()
    )
    enriched_ids = {r[0] for r in enriched_result.all()}

    return {
        "bom_id": str(bom_id),
        "total_components": len(component_ids),
        "enriched_components": len(enriched_ids),
        "pending_components": len(component_ids) - len(enriched_ids),
    }


@router.get("/components/{component_id}/enrichment")
async def component_enrichment(
    component_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(EnrichmentRecord)
        .where(EnrichmentRecord.component_id == component_id)
        .order_by(EnrichmentRecord.fetched_at.desc())
    )
    records = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "component_id": str(r.component_id),
            "source": r.source,
            "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
            "lifecycle_status": r.lifecycle_status,
            "yteol": r.yteol,
            "total_inventory": r.total_inventory,
            "avg_lead_time_days": r.avg_lead_time_days,
            "distributor_count": r.distributor_count,
            "num_alternates": r.num_alternates,
            "country_of_origin": r.country_of_origin,
            "single_source": r.single_source,
            "rohs_compliant": r.rohs_compliant,
            "reach_compliant": r.reach_compliant,
            "data": r.data,
        }
        for r in records
    ]
