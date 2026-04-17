"""Orchestrate Tier B + Tier C context and LLM or rules-based narrative."""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinel.config import settings
from sentinel.db.models import Bom, Component, LlmAuditLog, RiskScoreRecord
from sentinel.enrichment.merge import merge_enrichment_records
from sentinel.intelligence.context_packager import estimate_token_budget, pack_component_context, pack_market_events_tier_c
from sentinel.intelligence.llm_client import complete_narrative_json
from sentinel.intelligence.policy import POLICY_VERSION, RedactionPolicy, stable_component_token
from sentinel.intelligence.schemas import Citation, MarketEventPublic, NarrativeAnalysis, NarrativeRequest, NarrativeResponse
from sentinel.intelligence.signals import list_recent_events, match_events_for_component
from sentinel.risk.scorer import RiskFactor, _generate_recommendation

log = structlog.get_logger()


def _rules_narrative(
    component: Component,
    merged,
    risk: RiskScoreRecord | None,
    matched_events,
) -> NarrativeAnalysis:
    facts: list[str] = []
    if risk:
        facts.append(f"Composite risk score: {risk.composite_score:.1f}/100 (profile {risk.profile}).")
        for f in (risk.risk_factors or [])[:8]:
            if isinstance(f, dict):
                facts.append(f.get("detail", str(f)))
            else:
                facts.append(str(f))
    if merged:
        if merged.country_of_origin:
            facts.append(f"Country of origin (merged): {merged.country_of_origin}.")
        if merged.lifecycle_status:
            facts.append(f"Lifecycle: {merged.lifecycle_status}.")

    interp_parts = []
    if risk and risk.composite_score >= 50:
        interp_parts.append("Elevated composite risk suggests prioritizing mitigation before production impact.")
    elif risk:
        interp_parts.append("Risk is within typical operating bounds; monitor for lifecycle and supply shifts.")
    else:
        interp_parts.append("No scored risk record; run risk scoring first.")

    impact = "Single-line item view; portfolio-wide effects depend on duplicate MPNs across BOMs and shared suppliers."
    if matched_events:
        impact += f" {len(matched_events)} public market headline(s) overlap this part's regions or keywords."

    actions: list[str] = []
    if risk:
        factors_for_rec: list[RiskFactor] = []
        for f in risk.risk_factors or []:
            if isinstance(f, dict):
                factors_for_rec.append(
                    RiskFactor(
                        factor=str(f.get("factor", "unknown")),
                        detail=str(f.get("detail", "")),
                        contribution=float(f.get("contribution", 0)),
                    )
                )
        rec = _generate_recommendation(risk.composite_score, factors_for_rec)
        if rec:
            actions.append(rec)
    actions.append("Re-run enrichment on a schedule; validate critical parts against alternates in Nexar/SiliconExpert.")

    citations = [
        Citation(
            title=e.title,
            source_url=e.source_url,
            published_at=e.published_at.isoformat() if e.published_at else None,
            relevance="Keyword/region overlap with component profile",
        )
        for e in matched_events[:5]
    ]

    return NarrativeAnalysis(
        facts_used=facts,
        interpretation=" ".join(interp_parts),
        portfolio_impact=impact,
        actions=actions,
        citations=citations,
    )


async def build_narrative(
    session: AsyncSession,
    component_id: UUID,
    body: NarrativeRequest,
) -> NarrativeResponse:
    result = await session.execute(
        select(Component)
        .where(Component.id == component_id)
        .options(
            selectinload(Component.bom),
            selectinload(Component.enrichment_records),
            selectinload(Component.risk_scores),
        )
    )
    component = result.scalar_one_or_none()
    if not component:
        raise ValueError("component not found")

    merged = (
        merge_enrichment_records(list(component.enrichment_records))
        if component.enrichment_records
        else None
    )
    risk = max(component.risk_scores, key=lambda r: r.scored_at, default=None) if component.risk_scores else None

    all_events = await list_recent_events(session, limit=200)
    matched = match_events_for_component(component, merged, all_events, max_events=8)

    policy = RedactionPolicy(
        include_bom_name=False,
        include_program=False,
        include_source_filename=False,
        allow_remote_llm=body.allow_remote_llm,
    )
    ctx = pack_component_context(
        component,
        merged,
        risk,
        component.bom,
        policy,
        bom_label=None,
    )
    tier_c = pack_market_events_tier_c(matched)
    user_payload = {
        "policy_version": POLICY_VERSION,
        "component_context_tier_b": ctx,
        "public_events_tier_c": tier_c,
    }

    remote_used = False
    raw_err: str | None = None
    analysis: NarrativeAnalysis | None = None
    source = "rules"
    llm_attempted = False

    if body.use_llm and settings.llm_enabled:
        llm_attempted = True
        analysis, raw_err = await complete_narrative_json(user_payload, body.allow_remote_llm)
        if analysis:
            source = "llm"
            from sentinel.intelligence.llm_client import is_local_llm_endpoint

            remote_used = not is_local_llm_endpoint()
            if not analysis.citations and matched:
                analysis.citations = [
                    Citation(
                        title=e.title,
                        source_url=e.source_url,
                        published_at=e.published_at.isoformat() if e.published_at else None,
                        relevance="Matched public event",
                    )
                    for e in matched[:5]
                ]

    if analysis is None:
        analysis = _rules_narrative(component, merged, risk, matched)
        source = "rules"

    # Audit log (no raw payload)
    tiers = ["B", "C"]
    payload_chars = estimate_token_budget(user_payload)
    audit = LlmAuditLog(
        policy_version=POLICY_VERSION,
        policy_fingerprint=policy.fingerprint(),
        component_token=stable_component_token(str(component_id)),
        remote_llm=remote_used,
        tiers_included=tiers,
        payload_chars=payload_chars,
        error=raw_err if llm_attempted else None,
    )
    session.add(audit)
    await session.commit()

    matched_pub = [
        MarketEventPublic(
            id=str(e.id),
            title=e.title,
            summary=e.summary,
            source_url=e.source_url,
            published_at=e.published_at.isoformat() if e.published_at else None,
            event_type=e.event_type,
            region_tags=list(e.region_tags or []),
            keywords=list(e.keywords or []),
        )
        for e in matched
    ]

    return NarrativeResponse(
        analysis=analysis,
        source=source,
        policy_version=POLICY_VERSION,
        remote_llm_used=remote_used,
        matched_events=matched_pub,
        raw_model_error=raw_err if llm_attempted and source == "rules" else None,
    )
