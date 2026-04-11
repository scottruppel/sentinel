from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinel.db.models import Bom, Component, EnrichmentRecord, RiskScoreRecord
from sentinel.db.session import get_session
from sentinel.ingest.parser import parse_bom
from sentinel.enrichment.merge import MergedEnrichment, merge_enrichment_records

log = structlog.get_logger()
router = APIRouter(tags=["boms"])


@router.post("/boms/upload")
async def upload_bom(
    file: UploadFile = File(...),
    name: str = Form(...),
    program: str | None = Form(None),
    description: str | None = Form(None),
    session: AsyncSession = Depends(get_session),
):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    content = await file.read()
    log.info("bom_upload_start", filename=file.filename, size=len(content))

    try:
        result = parse_bom(file.filename, content)
    except ValueError as e:
        raise HTTPException(400, str(e))

    bom = Bom(
        name=name,
        description=description,
        program=program,
        source_filename=file.filename,
        component_count=len(result.components),
    )
    session.add(bom)
    await session.flush()

    for pc in result.components:
        comp = Component(
            bom_id=bom.id,
            mpn=pc.mpn,
            mpn_normalized=pc.mpn_normalized,
            manufacturer=pc.manufacturer,
            reference_designator=pc.reference_designator,
            quantity=pc.quantity,
            description=pc.description,
            value=pc.value,
            package=pc.package,
            category=pc.category,
        )
        session.add(comp)

    await session.commit()
    log.info("bom_upload_complete", bom_id=str(bom.id), component_count=len(result.components))

    return {
        "bom_id": str(bom.id),
        "name": bom.name,
        "component_count": len(result.components),
        "parse_warnings": [{"row": w.row, "warning": w.warning} for w in result.warnings],
        "status": "ingested",
    }


@router.get("/boms")
async def list_boms(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Bom).order_by(Bom.uploaded_at.desc()))
    boms = result.scalars().all()
    return [_bom_dict(b) for b in boms]


@router.get("/boms/{bom_id}")
async def get_bom(bom_id: UUID, session: AsyncSession = Depends(get_session)):
    bom = await session.get(Bom, bom_id)
    if not bom:
        raise HTTPException(404, "BOM not found")
    return _bom_dict(bom)


@router.delete("/boms/{bom_id}")
async def delete_bom(bom_id: UUID, session: AsyncSession = Depends(get_session)):
    bom = await session.get(Bom, bom_id)
    if not bom:
        raise HTTPException(404, "BOM not found")
    await session.delete(bom)
    await session.commit()
    return {"status": "deleted"}


@router.get("/boms/{bom_id}/components")
async def list_components(
    bom_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    lifecycle_status: str | None = Query(None),
    risk_min: float | None = Query(None),
    risk_max: float | None = Query(None),
    manufacturer: str | None = Query(None),
    category: str | None = Query(None),
    sort_by: str = Query("mpn"),
    sort_order: str = Query("asc"),
    session: AsyncSession = Depends(get_session),
):
    bom = await session.get(Bom, bom_id)
    if not bom:
        raise HTTPException(404, "BOM not found")

    query = (
        select(Component)
        .where(Component.bom_id == bom_id)
        .options(
            selectinload(Component.enrichment_records),
            selectinload(Component.risk_scores),
        )
    )

    if search:
        query = query.where(
            Component.mpn.ilike(f"%{search}%")
            | Component.manufacturer.ilike(f"%{search}%")
            | Component.description.ilike(f"%{search}%")
        )
    if manufacturer:
        query = query.where(Component.manufacturer.ilike(f"%{manufacturer}%"))
    if category:
        query = query.where(Component.category.ilike(f"%{category}%"))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    sort_col = getattr(Component, sort_by, Component.mpn)
    order = sort_col.desc() if sort_order == "desc" else sort_col.asc()
    query = query.order_by(order).offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    components = result.scalars().all()

    items = []
    for c in components:
        merged = merge_enrichment_records(list(c.enrichment_records)) if c.enrichment_records else None
        latest_enrichment = merged  # merged view for display filters; _enrichment_dict expects record-like — see below
        latest_risk = max(c.risk_scores, key=lambda r: r.scored_at, default=None) if c.risk_scores else None

        if lifecycle_status and merged:
            if merged.lifecycle_status != lifecycle_status:
                continue
        if risk_min is not None and latest_risk:
            if latest_risk.composite_score < risk_min:
                continue
        if risk_max is not None and latest_risk:
            if latest_risk.composite_score > risk_max:
                continue

        items.append(_component_with_risk(c, latest_enrichment, latest_risk))

    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/boms/cross-exposure")
async def cross_exposure(session: AsyncSession = Depends(get_session)):
    query = (
        select(
            Component.mpn_normalized,
            Component.manufacturer,
            func.count(func.distinct(Component.bom_id)).label("bom_count"),
            func.array_agg(func.distinct(Component.bom_id)).label("bom_ids"),
            func.sum(Component.quantity).label("total_quantity"),
        )
        .group_by(Component.mpn_normalized, Component.manufacturer)
        .having(func.count(func.distinct(Component.bom_id)) > 1)
    )
    result = await session.execute(query)
    rows = result.all()
    return [
        {
            "mpn_normalized": r.mpn_normalized,
            "manufacturer": r.manufacturer,
            "bom_count": r.bom_count,
            "bom_ids": [str(bid) for bid in r.bom_ids] if r.bom_ids else [],
            "total_quantity": r.total_quantity,
        }
        for r in rows
    ]


def _bom_dict(bom: Bom) -> dict:
    return {
        "id": str(bom.id),
        "name": bom.name,
        "description": bom.description,
        "program": bom.program,
        "version": bom.version,
        "source_filename": bom.source_filename,
        "uploaded_at": bom.uploaded_at.isoformat() if bom.uploaded_at else None,
        "component_count": bom.component_count,
        "risk_score_overall": bom.risk_score_overall,
        "metadata": bom.metadata_,
    }


def _component_with_risk(comp: Component, enrichment, risk_score) -> dict:
    return {
        "id": str(comp.id),
        "bom_id": str(comp.bom_id),
        "reference_designator": comp.reference_designator,
        "mpn": comp.mpn,
        "mpn_normalized": comp.mpn_normalized,
        "manufacturer": comp.manufacturer,
        "description": comp.description,
        "quantity": comp.quantity,
        "category": comp.category,
        "package": comp.package,
        "value": comp.value,
        "is_critical": comp.is_critical,
        "metadata": comp.metadata_,
        "created_at": comp.created_at.isoformat() if comp.created_at else None,
        "enrichment": _enrichment_for_api(enrichment) if enrichment else None,
        "risk_score": _risk_dict(risk_score) if risk_score else None,
    }


def _enrichment_for_api(e: EnrichmentRecord | MergedEnrichment) -> dict:
    if isinstance(e, MergedEnrichment):
        return {
            "id": None,
            "component_id": None,
            "source": "merged",
            "fetched_at": None,
            "lifecycle_status": e.lifecycle_status,
            "yteol": e.yteol,
            "total_inventory": e.total_inventory,
            "avg_lead_time_days": e.avg_lead_time_days,
            "distributor_count": e.distributor_count,
            "num_alternates": e.num_alternates,
            "country_of_origin": e.country_of_origin,
            "single_source": e.single_source,
            "rohs_compliant": e.rohs_compliant,
            "reach_compliant": e.reach_compliant,
            "data": {"field_sources": e.field_sources},
        }
    return _enrichment_dict(e)


def _enrichment_dict(e: EnrichmentRecord) -> dict:
    return {
        "id": str(e.id),
        "component_id": str(e.component_id),
        "source": e.source,
        "fetched_at": e.fetched_at.isoformat() if e.fetched_at else None,
        "lifecycle_status": e.lifecycle_status,
        "yteol": e.yteol,
        "total_inventory": e.total_inventory,
        "avg_lead_time_days": e.avg_lead_time_days,
        "distributor_count": e.distributor_count,
        "num_alternates": e.num_alternates,
        "country_of_origin": e.country_of_origin,
        "single_source": e.single_source,
        "rohs_compliant": e.rohs_compliant,
        "reach_compliant": e.reach_compliant,
        "data": e.data,
    }


def _risk_dict(r: RiskScoreRecord) -> dict:
    return {
        "id": str(r.id),
        "component_id": str(r.component_id),
        "scored_at": r.scored_at.isoformat() if r.scored_at else None,
        "profile": r.profile,
        "lifecycle_risk": r.lifecycle_risk,
        "supply_risk": r.supply_risk,
        "geographic_risk": r.geographic_risk,
        "supplier_risk": r.supplier_risk,
        "regulatory_risk": r.regulatory_risk,
        "composite_score": r.composite_score,
        "risk_factors": r.risk_factors,
        "recommendation": r.recommendation,
    }
