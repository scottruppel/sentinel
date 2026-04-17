"""Build Tier B minimized JSON for LLM consumption; strip Tier A by default."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sentinel.db.models import Bom, Component, RiskScoreRecord
from sentinel.enrichment.merge import MergedEnrichment
from sentinel.intelligence.policy import RedactionPolicy, stable_component_token

MAX_FACTORS = 12


def pack_component_context(
    component: Component,
    merged: MergedEnrichment | None,
    risk: RiskScoreRecord | None,
    bom: Bom | None,
    policy: RedactionPolicy,
    bom_label: str | None = None,
) -> dict[str, Any]:
    """
    Tier B payload. Tier A fields (ref des, qty, descriptions) omitted unless policy enables.
    """
    cid = str(component.id)
    comp_key = stable_component_token(cid) if policy.hash_component_ids else cid

    row: dict[str, Any] = {
        "component_key": comp_key,
        "mpn": component.mpn,
        "manufacturer": component.manufacturer,
        "category": component.category,
    }

    if policy.include_reference_designator:
        row["reference_designator"] = component.reference_designator
    if policy.include_quantity:
        row["quantity"] = component.quantity
    if policy.include_component_description:
        row["description"] = component.description

    if merged:
        row["enrichment"] = {
            "lifecycle_status": merged.lifecycle_status,
            "yteol": merged.yteol,
            "total_inventory": merged.total_inventory,
            "avg_lead_time_days": merged.avg_lead_time_days,
            "distributor_count": merged.distributor_count,
            "num_alternates": merged.num_alternates,
            "country_of_origin": merged.country_of_origin,
            "single_source": merged.single_source,
            "rohs_compliant": merged.rohs_compliant,
            "reach_compliant": merged.reach_compliant,
            "field_sources": merged.field_sources,
        }

    if risk:
        factors = risk.risk_factors or []
        if isinstance(factors, list) and len(factors) > MAX_FACTORS:
            factors = factors[:MAX_FACTORS]
        row["risk"] = {
            "lifecycle_risk": risk.lifecycle_risk,
            "supply_risk": risk.supply_risk,
            "geographic_risk": risk.geographic_risk,
            "supplier_risk": risk.supplier_risk,
            "regulatory_risk": risk.regulatory_risk,
            "composite_score": risk.composite_score,
            "risk_factors": factors,
            "rule_recommendation": risk.recommendation,
            "profile": risk.profile,
        }

    bom_meta: dict[str, Any] = {}
    if bom_label:
        bom_meta["label"] = bom_label
    elif bom:
        if policy.include_bom_name:
            bom_meta["name"] = bom.name
        if policy.include_program:
            bom_meta["program"] = bom.program
        if policy.include_source_filename:
            bom_meta["source_filename"] = bom.source_filename
    if bom_meta:
        row["bom"] = bom_meta

    return row


def pack_market_events_tier_c(events: list[Any]) -> list[dict[str, Any]]:
    """Tier C snippets for prompting."""
    out = []
    for e in events:
        out.append(
            {
                "title": e.title,
                "summary": (e.summary or "")[:2000],
                "source_url": e.source_url,
                "published_at": e.published_at.isoformat() if e.published_at else None,
                "event_type": e.event_type,
                "region_tags": list(e.region_tags or []),
                "keywords": list(e.keywords or []),
            }
        )
    return out


def estimate_token_budget(obj: dict[str, Any]) -> int:
    """Rough character-based budget for logging (not exact tokens)."""
    import json

    return len(json.dumps(obj, default=str))
