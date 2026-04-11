from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinel.db.models import Bom, Component, EnrichmentRecord, RiskScoreRecord
from sentinel.enrichment.merge import merge_enrichment_records
from sentinel.risk.weights import RiskWeightProfile, DEFAULT_PROFILE, PROFILES

log = structlog.get_logger()

HIGH_RISK_COUNTRIES = {"China", "Russia", "Iran", "North Korea"}
SANCTIONED_COUNTRIES = {"Russia", "Iran", "North Korea", "Syria", "Cuba"}


@dataclass
class RiskFactor:
    factor: str
    detail: str
    contribution: float


@dataclass
class DimensionScore:
    score: float
    factors: list[RiskFactor] = field(default_factory=list)


def score_lifecycle_risk(
    lifecycle_status: str | None,
    yteol: float | None,
    num_alternates: int | None,
    single_source: bool | None,
) -> DimensionScore:
    factors: list[RiskFactor] = []
    status = (lifecycle_status or "Unknown").strip()

    if status == "Obsolete":
        if (num_alternates or 0) == 0:
            score = 100.0
            factors.append(RiskFactor("obsolete_no_alt", "Obsolete with no alternates identified", 100))
        else:
            score = 80.0
            factors.append(RiskFactor("obsolete_with_alt", f"Obsolete, {num_alternates} alternates available", 80))
    elif status == "Last Time Buy":
        if yteol is not None and yteol <= 0:
            score = 90.0
            factors.append(RiskFactor("ltb_expired", "Last Time Buy window expired", 90))
        else:
            score = 70.0
            factors.append(RiskFactor("ltb_open", f"Last Time Buy window open (YTEOL: {yteol}y)", 70))
    elif status == "NRFND":
        if yteol is not None and yteol < 2:
            score = 60.0
            factors.append(RiskFactor("nrfnd_short", f"NRFND with YTEOL < 2 years ({yteol}y)", 60))
        elif yteol is not None and yteol <= 5:
            score = 40.0
            factors.append(RiskFactor("nrfnd_mid", f"NRFND with YTEOL 2-5 years ({yteol}y)", 40))
        else:
            score = 35.0
            factors.append(RiskFactor("nrfnd", "Not Recommended for New Designs", 35))
    elif "Active" in status:
        if single_source:
            score = 25.0
            factors.append(RiskFactor("active_single", "Active but single manufacturer", 25))
        else:
            score = 5.0
            factors.append(RiskFactor("active_multi", "Active, multi-source", 5))
    else:
        score = 50.0
        factors.append(RiskFactor("unknown_lifecycle", f"Unknown lifecycle status: {status}", 50))

    return DimensionScore(score=min(score, 100), factors=factors)


def score_supply_risk(
    total_inventory: int | None,
    avg_lead_time_days: int | None,
    distributor_count: int | None,
) -> DimensionScore:
    factors: list[RiskFactor] = []
    score = 5.0

    inv = total_inventory if total_inventory is not None else 0
    lead = avg_lead_time_days if avg_lead_time_days is not None else 0
    dists = distributor_count if distributor_count is not None else 0

    if inv == 0 and dists == 0:
        score = 100.0
        factors.append(RiskFactor("zero_inventory", "Zero authorized distributor inventory", 100))
    elif inv < 100:
        score = max(score, 75.0)
        factors.append(RiskFactor("low_inventory", f"Very low inventory ({inv} units)", 75))
    elif inv < 1000:
        score = max(score, 50.0)
        factors.append(RiskFactor("limited_inventory", f"Limited inventory ({inv} units)", 50))

    if lead > 365:
        score = max(score, 80.0)
        factors.append(RiskFactor("long_lead", f"Lead time > 52 weeks ({lead} days)", 80))
    elif lead > 182:
        score = max(score, 50.0)
        factors.append(RiskFactor("extended_lead", f"Lead time 26-52 weeks ({lead} days)", 50))
    elif lead > 90:
        score = max(score, 30.0)
        factors.append(RiskFactor("moderate_lead", f"Lead time > 90 days ({lead} days)", 30))

    if dists <= 1:
        score = max(score, 40.0)
        factors.append(RiskFactor("few_distributors", f"Only {dists} distributor(s)", 40))

    if not factors:
        factors.append(RiskFactor("healthy_supply", "Healthy inventory and lead time", 5))

    return DimensionScore(score=min(score, 100), factors=factors)


def score_geographic_risk(country_of_origin: str | None) -> DimensionScore:
    factors: list[RiskFactor] = []
    country = (country_of_origin or "").strip()

    if not country:
        score = 50.0
        factors.append(RiskFactor("unknown_origin", "Country of origin unknown", 50))
    elif country in SANCTIONED_COUNTRIES:
        score = 100.0
        factors.append(RiskFactor("sanctioned", f"Manufacturing in sanctioned region: {country}", 100))
    elif country in HIGH_RISK_COUNTRIES:
        score = 60.0
        factors.append(RiskFactor("high_risk_country", f"Single-country concentration in {country}", 60))
    elif country == "Taiwan":
        score = 55.0
        factors.append(RiskFactor("taiwan_risk", "Manufacturing concentrated in Taiwan (geopolitical risk)", 55))
    else:
        score = 10.0
        factors.append(RiskFactor("standard_geo", f"Manufacturing in {country}", 10))

    return DimensionScore(score=min(score, 100), factors=factors)


def score_supplier_risk(
    single_source: bool | None,
    num_alternates: int | None,
    manufacturer: str | None,
) -> DimensionScore:
    factors: list[RiskFactor] = []

    if single_source and (num_alternates or 0) == 0:
        score = 85.0
        factors.append(RiskFactor("sole_source", f"Sole source ({manufacturer or 'unknown'})", 85))
    elif single_source:
        score = 65.0
        factors.append(RiskFactor("single_source", f"Single source with {num_alternates} alternates", 65))
    elif (num_alternates or 0) >= 3:
        score = 5.0
        factors.append(RiskFactor("multi_source", f"Multi-source ({num_alternates} alternates)", 5))
    elif (num_alternates or 0) >= 1:
        score = 15.0
        factors.append(RiskFactor("dual_source", f"Dual source ({num_alternates} alternates)", 15))
    else:
        score = 50.0
        factors.append(RiskFactor("unknown_sourcing", "Sourcing information unavailable", 50))

    return DimensionScore(score=min(score, 100), factors=factors)


def score_regulatory_risk(
    rohs_compliant: bool | None,
    reach_compliant: bool | None,
) -> DimensionScore:
    factors: list[RiskFactor] = []
    score = 5.0

    if rohs_compliant is False:
        score = max(score, 60.0)
        factors.append(RiskFactor("non_rohs", "Non-RoHS compliant", 60))
    if reach_compliant is False:
        score = max(score, 50.0)
        factors.append(RiskFactor("reach_svhc", "REACH SVHC listed substance", 50))

    if not factors:
        factors.append(RiskFactor("compliant", "Fully compliant", 5))

    return DimensionScore(score=min(score, 100), factors=factors)


def compute_composite(
    lifecycle: DimensionScore,
    supply: DimensionScore,
    geographic: DimensionScore,
    supplier: DimensionScore,
    regulatory: DimensionScore,
    profile: RiskWeightProfile = DEFAULT_PROFILE,
) -> float:
    return (
        lifecycle.score * profile.lifecycle
        + supply.score * profile.supply
        + geographic.score * profile.geographic
        + supplier.score * profile.supplier
        + regulatory.score * profile.regulatory
    )


def _generate_recommendation(composite: float, factors: list[RiskFactor]) -> str | None:
    if composite < 30:
        return None
    top = sorted(factors, key=lambda f: f.contribution, reverse=True)[:3]
    parts = []
    for f in top:
        if "obsolete" in f.factor.lower():
            parts.append("Initiate lifetime buy or identify form-fit-function alternate")
        elif "ltb" in f.factor.lower():
            parts.append("Execute last-time buy before window closes")
        elif "nrfnd" in f.factor.lower():
            parts.append("Plan migration to next-generation part")
        elif "sole_source" in f.factor.lower() or "single_source" in f.factor.lower():
            parts.append("Qualify second source to reduce supplier dependency")
        elif "inventory" in f.factor.lower() or "lead" in f.factor.lower():
            parts.append("Build safety stock buffer; negotiate supply agreements")
        elif "taiwan" in f.factor.lower() or "sanctioned" in f.factor.lower() or "high_risk" in f.factor.lower():
            parts.append("Identify alternate manufacturing sources outside risk region")
    return "; ".join(dict.fromkeys(parts)) if parts else "Review risk factors and develop mitigation plan"


async def score_bom(
    session: AsyncSession,
    bom_id: UUID,
    profile_name: str = "default",
) -> dict:
    profile = PROFILES.get(profile_name, DEFAULT_PROFILE)

    result = await session.execute(
        select(Component)
        .where(Component.bom_id == bom_id)
        .options(selectinload(Component.enrichment_records))
    )
    components = result.scalars().all()
    log.info("scoring_bom", bom_id=str(bom_id), component_count=len(components), profile=profile.name)

    scores: list[RiskScoreRecord] = []

    for comp in components:
        merged = (
            merge_enrichment_records(list(comp.enrichment_records))
            if comp.enrichment_records
            else None
        )

        lifecycle = score_lifecycle_risk(
            merged.lifecycle_status if merged else None,
            merged.yteol if merged else None,
            merged.num_alternates if merged else None,
            merged.single_source if merged else None,
        )
        supply = score_supply_risk(
            merged.total_inventory if merged else None,
            merged.avg_lead_time_days if merged else None,
            merged.distributor_count if merged else None,
        )
        geographic = score_geographic_risk(merged.country_of_origin if merged else None)
        supplier = score_supplier_risk(
            merged.single_source if merged else None,
            merged.num_alternates if merged else None,
            comp.manufacturer,
        )
        regulatory = score_regulatory_risk(
            merged.rohs_compliant if merged else None,
            merged.reach_compliant if merged else None,
        )

        composite = compute_composite(lifecycle, supply, geographic, supplier, regulatory, profile)
        all_factors = lifecycle.factors + supply.factors + geographic.factors + supplier.factors + regulatory.factors
        recommendation = _generate_recommendation(composite, all_factors)

        record = RiskScoreRecord(
            component_id=comp.id,
            profile=profile.name,
            lifecycle_risk=lifecycle.score,
            supply_risk=supply.score,
            geographic_risk=geographic.score,
            supplier_risk=supplier.score,
            regulatory_risk=regulatory.score,
            composite_score=round(composite, 2),
            risk_factors=[{"factor": f.factor, "detail": f.detail, "contribution": f.contribution} for f in all_factors],
            recommendation=recommendation,
        )
        session.add(record)
        scores.append(record)

    await session.flush()

    comp_by_id = {c.id: c for c in components}
    summary = compute_bom_risk(scores, comp_by_id)

    bom = await session.get(Bom, bom_id)
    if bom:
        bom.risk_score_overall = summary["overall_score"]

    await session.commit()
    log.info("scoring_complete", bom_id=str(bom_id), overall=summary["overall_score"])
    return summary


def compute_bom_risk(
    scores: list[RiskScoreRecord],
    components_by_id: dict[UUID, Component] | None = None,
) -> dict:
    if not scores:
        return {
            "overall_score": 0,
            "max_component_risk": 0,
            "critical_count": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "top_risks": [],
            "risk_by_category": {},
        }

    composites = [s.composite_score for s in scores]

    risk_by_category: dict[str, dict] = {}
    if components_by_id:
        from collections import defaultdict

        buckets: dict[str, list[float]] = defaultdict(list)
        for s in scores:
            comp = components_by_id.get(s.component_id)
            cat = (comp.category if comp else None) or "Unknown"
            buckets[cat].append(s.composite_score)
        for cat, vals in sorted(buckets.items()):
            risk_by_category[cat] = {
                "count": len(vals),
                "avg_composite": round(sum(vals) / len(vals), 2),
            }

    return {
        "overall_score": round(sum(composites) / len(composites), 2),
        "max_component_risk": max(composites),
        "critical_count": sum(1 for s in composites if s >= 70),
        "high_count": sum(1 for s in composites if 50 <= s < 70),
        "medium_count": sum(1 for s in composites if 30 <= s < 50),
        "low_count": sum(1 for s in composites if s < 30),
        "top_risks": [
            {
                "component_id": str(s.component_id),
                "composite_score": s.composite_score,
                "profile": s.profile,
            }
            for s in sorted(scores, key=lambda s: s.composite_score, reverse=True)[:10]
        ],
        "risk_by_category": risk_by_category,
    }
