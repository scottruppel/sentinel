from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.db.models import RiskScoreRecord
from sentinel.db.session import get_session
from sentinel.risk.scorer import score_bom, compute_bom_risk
from sentinel.risk.weights import PROFILES, RiskWeightProfile

log = structlog.get_logger()
router = APIRouter(tags=["risk"])


@router.post("/risk/score/{bom_id}")
async def run_scoring(
    bom_id: UUID,
    profile: str = "default",
    session: AsyncSession = Depends(get_session),
):
    if profile not in PROFILES:
        raise HTTPException(400, f"Unknown profile: {profile}. Available: {list(PROFILES.keys())}")
    summary = await score_bom(session, bom_id, profile)
    return {"bom_id": str(bom_id), "profile": profile, **summary}


@router.get("/risk/scores/{bom_id}")
async def get_scores(
    bom_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    from sentinel.db.models import Component
    result = await session.execute(
        select(RiskScoreRecord)
        .join(Component, RiskScoreRecord.component_id == Component.id)
        .where(Component.bom_id == bom_id)
        .order_by(RiskScoreRecord.composite_score.desc())
    )
    scores = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "component_id": str(s.component_id),
            "scored_at": s.scored_at.isoformat() if s.scored_at else None,
            "profile": s.profile,
            "lifecycle_risk": s.lifecycle_risk,
            "supply_risk": s.supply_risk,
            "geographic_risk": s.geographic_risk,
            "supplier_risk": s.supplier_risk,
            "regulatory_risk": s.regulatory_risk,
            "composite_score": s.composite_score,
            "risk_factors": s.risk_factors,
            "recommendation": s.recommendation,
        }
        for s in scores
    ]


@router.get("/risk/summary/{bom_id}")
async def get_summary(
    bom_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    from sentinel.db.models import Component
    result = await session.execute(
        select(RiskScoreRecord)
        .join(Component, RiskScoreRecord.component_id == Component.id)
        .where(Component.bom_id == bom_id)
    )
    scores = result.scalars().all()
    if not scores:
        raise HTTPException(404, "No risk scores found for this BOM")
    return compute_bom_risk(scores)


@router.get("/risk/profiles")
async def list_profiles():
    return {name: p.as_dict() for name, p in PROFILES.items()}


@router.put("/risk/profiles/{name}")
async def upsert_profile(name: str, body: dict):
    try:
        profile = RiskWeightProfile(
            name=name,
            lifecycle=body["lifecycle"],
            supply=body["supply"],
            geographic=body["geographic"],
            supplier=body["supplier"],
            regulatory=body["regulatory"],
        )
    except KeyError as e:
        raise HTTPException(400, f"Missing weight: {e}")

    total = profile.lifecycle + profile.supply + profile.geographic + profile.supplier + profile.regulatory
    if abs(total - 1.0) > 0.01:
        raise HTTPException(400, f"Weights must sum to 1.0, got {total}")

    PROFILES[name] = profile
    return profile.as_dict()
