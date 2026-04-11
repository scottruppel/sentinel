from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinel.db.models import Bom, Component, RiskScoreRecord, Scenario
from sentinel.enrichment.merge import merge_enrichment_records
from sentinel.risk.scorer import (
    score_lifecycle_risk,
    score_supply_risk,
    score_geographic_risk,
    score_supplier_risk,
    score_regulatory_risk,
    compute_composite,
    _generate_recommendation,
)
from sentinel.risk.weights import DEFAULT_PROFILE, PROFILES

log = structlog.get_logger()


async def _load_bom_names(session: AsyncSession, bom_ids: list[UUID]) -> dict[str, str]:
    if not bom_ids:
        return {}
    result = await session.execute(select(Bom.id, Bom.name).where(Bom.id.in_(bom_ids)))
    return {str(row[0]): row[1] for row in result.all()}


async def run_scenario(session: AsyncSession, scenario: Scenario) -> dict:
    """Execute a what-if scenario and compute impact."""
    log.info("scenario_executing", scenario_id=str(scenario.id), type=scenario.scenario_type)

    scenario.status = "running"
    await session.flush()

    bom_ids = scenario.affected_bom_ids
    if not bom_ids:
        result = await session.execute(select(Bom.id))
        bom_ids = [r[0] for r in result.all()]

    handler = _HANDLERS.get(scenario.scenario_type)
    if not handler:
        raise ValueError(f"Unknown scenario type: {scenario.scenario_type}")

    results = await handler(session, bom_ids, scenario.parameters)

    scenario.results = results
    scenario.status = "complete"
    await session.commit()

    log.info("scenario_complete", scenario_id=str(scenario.id), affected=results["summary"]["total_components_affected"])
    return results


async def _handle_country_disruption(session: AsyncSession, bom_ids: list[UUID], params: dict) -> dict:
    country = params.get("country", "")
    severity = params.get("severity", "total_loss")

    components = await _load_components(session, bom_ids)
    affected = []
    baseline_bom_risk: dict[str, float] = {}
    scenario_bom_risk: dict[str, float] = {}
    bom_components: dict[str, list] = {}

    for comp, enrichment, risk in components:
        bom_str = str(comp.bom_id)
        bom_components.setdefault(bom_str, [])

        baseline_composite = risk.composite_score if risk else 0
        bom_components[bom_str].append({"baseline": baseline_composite, "scenario": baseline_composite})

        if not enrichment or (enrichment.country_of_origin or "").strip() != country:
            continue

        if severity == "total_loss":
            new_supply = 100.0
            new_geo = 100.0
        elif severity == "partial_disruption":
            new_supply = min((risk.supply_risk if risk else 50) * 2.0, 100)
            new_geo = min((risk.geographic_risk if risk else 50) + 30, 100)
        else:
            new_supply = min((risk.supply_risk if risk else 50) + 20, 100)
            new_geo = min((risk.geographic_risk if risk else 50) + 20, 100)

        scenario_composite = compute_composite(
            type("D", (), {"score": risk.lifecycle_risk if risk else 50})(),
            type("D", (), {"score": new_supply})(),
            type("D", (), {"score": new_geo})(),
            type("D", (), {"score": risk.supplier_risk if risk else 50})(),
            type("D", (), {"score": risk.regulatory_risk if risk else 5})(),
            DEFAULT_PROFILE,
        )

        bom_components[bom_str][-1]["scenario"] = scenario_composite
        delta = scenario_composite - baseline_composite

        bom_result = await session.execute(select(Bom.name).where(Bom.id == comp.bom_id))
        bom_name = bom_result.scalar() or str(comp.bom_id)

        affected.append({
            "mpn": comp.mpn,
            "manufacturer": comp.manufacturer,
            "boms": [bom_name],
            "baseline_risk": round(baseline_composite, 1),
            "scenario_risk": round(scenario_composite, 1),
            "delta": round(delta, 1),
            "risk_factors": [f"Manufacturing in {country}", f"Severity: {severity}"],
            "recommendation": f"Identify alternate sources outside {country}" if delta > 10 else None,
        })

    for bom_id_str, comps in bom_components.items():
        baselines = [c["baseline"] for c in comps]
        scenarios = [c["scenario"] for c in comps]
        baseline_bom_risk[bom_id_str] = round(sum(baselines) / max(len(baselines), 1), 1)
        scenario_bom_risk[bom_id_str] = round(sum(scenarios) / max(len(scenarios), 1), 1)

    bom_names = await _load_bom_names(session, bom_ids)
    return _build_result(affected, baseline_bom_risk, scenario_bom_risk, bom_names)


async def _handle_supplier_failure(session: AsyncSession, bom_ids: list[UUID], params: dict) -> dict:
    manufacturer = params.get("manufacturer", "")
    failure_mode = params.get("failure_mode", "bankruptcy")

    components = await _load_components(session, bom_ids)
    affected = []
    baseline_bom_risk: dict[str, float] = {}
    scenario_bom_risk: dict[str, float] = {}
    bom_components: dict[str, list] = {}

    for comp, enrichment, risk in components:
        bom_str = str(comp.bom_id)
        bom_components.setdefault(bom_str, [])
        baseline_composite = risk.composite_score if risk else 0
        bom_components[bom_str].append({"baseline": baseline_composite, "scenario": baseline_composite})

        if not comp.manufacturer or manufacturer.lower() not in comp.manufacturer.lower():
            continue

        is_sole = enrichment.single_source if enrichment else True
        num_alt = enrichment.num_alternates if enrichment else 0

        if is_sole and (num_alt or 0) == 0:
            new_lifecycle = 100.0
            new_supply = 100.0
        elif is_sole:
            new_lifecycle = 80.0
            new_supply = 70.0
        else:
            new_lifecycle = risk.lifecycle_risk if risk else 50
            new_supply = min((risk.supply_risk if risk else 50) + 20, 100)

        scenario_composite = compute_composite(
            type("D", (), {"score": new_lifecycle})(),
            type("D", (), {"score": new_supply})(),
            type("D", (), {"score": risk.geographic_risk if risk else 50})(),
            type("D", (), {"score": min((risk.supplier_risk if risk else 50) + 30, 100)})(),
            type("D", (), {"score": risk.regulatory_risk if risk else 5})(),
            DEFAULT_PROFILE,
        )

        bom_components[bom_str][-1]["scenario"] = scenario_composite
        delta = scenario_composite - baseline_composite

        bom_result = await session.execute(select(Bom.name).where(Bom.id == comp.bom_id))
        bom_name = bom_result.scalar() or str(comp.bom_id)

        affected.append({
            "mpn": comp.mpn,
            "manufacturer": comp.manufacturer,
            "boms": [bom_name],
            "baseline_risk": round(baseline_composite, 1),
            "scenario_risk": round(scenario_composite, 1),
            "delta": round(delta, 1),
            "risk_factors": [f"Supplier {manufacturer} {failure_mode}", f"Sole source: {is_sole}"],
            "recommendation": "Qualify second source; initiate lifetime buy" if delta > 10 else None,
        })

    for bom_id_str, comps in bom_components.items():
        baselines = [c["baseline"] for c in comps]
        scenarios = [c["scenario"] for c in comps]
        baseline_bom_risk[bom_id_str] = round(sum(baselines) / max(len(baselines), 1), 1)
        scenario_bom_risk[bom_id_str] = round(sum(scenarios) / max(len(scenarios), 1), 1)

    bom_names = await _load_bom_names(session, bom_ids)
    return _build_result(affected, baseline_bom_risk, scenario_bom_risk, bom_names)


async def _handle_obsolescence_wave(session: AsyncSession, bom_ids: list[UUID], params: dict) -> dict:
    target_statuses = params.get("target_statuses", ["NRFND"])
    components = await _load_components(session, bom_ids)
    affected = []
    baseline_bom_risk: dict[str, float] = {}
    scenario_bom_risk: dict[str, float] = {}
    bom_components: dict[str, list] = {}

    for comp, enrichment, risk in components:
        bom_str = str(comp.bom_id)
        bom_components.setdefault(bom_str, [])
        baseline_composite = risk.composite_score if risk else 0
        bom_components[bom_str].append({"baseline": baseline_composite, "scenario": baseline_composite})

        status = enrichment.lifecycle_status if enrichment else None
        if not status or status not in target_statuses:
            continue

        new_lifecycle = 95.0
        scenario_composite = compute_composite(
            type("D", (), {"score": new_lifecycle})(),
            type("D", (), {"score": risk.supply_risk if risk else 50})(),
            type("D", (), {"score": risk.geographic_risk if risk else 50})(),
            type("D", (), {"score": risk.supplier_risk if risk else 50})(),
            type("D", (), {"score": risk.regulatory_risk if risk else 5})(),
            DEFAULT_PROFILE,
        )

        bom_components[bom_str][-1]["scenario"] = scenario_composite
        delta = scenario_composite - baseline_composite

        bom_result = await session.execute(select(Bom.name).where(Bom.id == comp.bom_id))
        bom_name = bom_result.scalar() or str(comp.bom_id)

        affected.append({
            "mpn": comp.mpn,
            "manufacturer": comp.manufacturer,
            "boms": [bom_name],
            "baseline_risk": round(baseline_composite, 1),
            "scenario_risk": round(scenario_composite, 1),
            "delta": round(delta, 1),
            "risk_factors": [f"Status {status} → Obsolete", "Accelerated obsolescence wave"],
            "recommendation": "Plan migration to next-generation part; execute lifetime buy",
        })

    for bom_id_str, comps in bom_components.items():
        baselines = [c["baseline"] for c in comps]
        scenarios = [c["scenario"] for c in comps]
        baseline_bom_risk[bom_id_str] = round(sum(baselines) / max(len(baselines), 1), 1)
        scenario_bom_risk[bom_id_str] = round(sum(scenarios) / max(len(scenarios), 1), 1)

    bom_names = await _load_bom_names(session, bom_ids)
    return _build_result(affected, baseline_bom_risk, scenario_bom_risk, bom_names)


async def _handle_component_removal(session: AsyncSession, bom_ids: list[UUID], params: dict) -> dict:
    mpns = [m.upper() for m in params.get("mpns", [])]
    reason = params.get("reason", "obsolete")
    components = await _load_components(session, bom_ids)
    affected = []
    baseline_bom_risk: dict[str, float] = {}
    scenario_bom_risk: dict[str, float] = {}
    bom_components: dict[str, list] = {}

    for comp, enrichment, risk in components:
        bom_str = str(comp.bom_id)
        bom_components.setdefault(bom_str, [])
        baseline_composite = risk.composite_score if risk else 0
        bom_components[bom_str].append({"baseline": baseline_composite, "scenario": baseline_composite})

        if comp.mpn_normalized not in mpns:
            continue

        scenario_composite = 100.0
        bom_components[bom_str][-1]["scenario"] = scenario_composite
        delta = scenario_composite - baseline_composite

        bom_result = await session.execute(select(Bom.name).where(Bom.id == comp.bom_id))
        bom_name = bom_result.scalar() or str(comp.bom_id)

        affected.append({
            "mpn": comp.mpn,
            "manufacturer": comp.manufacturer,
            "boms": [bom_name],
            "baseline_risk": round(baseline_composite, 1),
            "scenario_risk": 100.0,
            "delta": round(delta, 1),
            "risk_factors": [f"Component removed: {reason}"],
            "recommendation": "Immediate replacement required",
        })

    for bom_id_str, comps in bom_components.items():
        baselines = [c["baseline"] for c in comps]
        scenarios = [c["scenario"] for c in comps]
        baseline_bom_risk[bom_id_str] = round(sum(baselines) / max(len(baselines), 1), 1)
        scenario_bom_risk[bom_id_str] = round(sum(scenarios) / max(len(scenarios), 1), 1)

    bom_names = await _load_bom_names(session, bom_ids)
    return _build_result(affected, baseline_bom_risk, scenario_bom_risk, bom_names)


async def _handle_demand_spike(session: AsyncSession, bom_ids: list[UUID], params: dict) -> dict:
    multiplier = params.get("multiplier", 2.0)
    components = await _load_components(session, bom_ids)
    affected = []
    baseline_bom_risk: dict[str, float] = {}
    scenario_bom_risk: dict[str, float] = {}
    bom_components: dict[str, list] = {}

    for comp, enrichment, risk in components:
        bom_str = str(comp.bom_id)
        bom_components.setdefault(bom_str, [])
        baseline_composite = risk.composite_score if risk else 0
        bom_components[bom_str].append({"baseline": baseline_composite, "scenario": baseline_composite})

        inv = enrichment.total_inventory if enrichment else 0
        demand = comp.quantity * multiplier
        if inv and demand > inv:
            supply_escalation = min(100, (risk.supply_risk if risk else 50) + 30)
        elif inv and demand > inv * 0.5:
            supply_escalation = min(100, (risk.supply_risk if risk else 50) + 15)
        else:
            continue

        scenario_composite = compute_composite(
            type("D", (), {"score": risk.lifecycle_risk if risk else 50})(),
            type("D", (), {"score": supply_escalation})(),
            type("D", (), {"score": risk.geographic_risk if risk else 50})(),
            type("D", (), {"score": risk.supplier_risk if risk else 50})(),
            type("D", (), {"score": risk.regulatory_risk if risk else 5})(),
            DEFAULT_PROFILE,
        )

        bom_components[bom_str][-1]["scenario"] = scenario_composite
        delta = scenario_composite - baseline_composite

        bom_result = await session.execute(select(Bom.name).where(Bom.id == comp.bom_id))
        bom_name = bom_result.scalar() or str(comp.bom_id)

        affected.append({
            "mpn": comp.mpn,
            "manufacturer": comp.manufacturer,
            "boms": [bom_name],
            "baseline_risk": round(baseline_composite, 1),
            "scenario_risk": round(scenario_composite, 1),
            "delta": round(delta, 1),
            "risk_factors": [f"Demand {multiplier}x exceeds inventory ({inv})"],
            "recommendation": "Build safety stock; negotiate supply agreements",
        })

    for bom_id_str, comps in bom_components.items():
        baselines = [c["baseline"] for c in comps]
        scenarios = [c["scenario"] for c in comps]
        baseline_bom_risk[bom_id_str] = round(sum(baselines) / max(len(baselines), 1), 1)
        scenario_bom_risk[bom_id_str] = round(sum(scenarios) / max(len(scenarios), 1), 1)

    bom_names = await _load_bom_names(session, bom_ids)
    return _build_result(affected, baseline_bom_risk, scenario_bom_risk, bom_names)


async def _load_components(session: AsyncSession, bom_ids: list[UUID]):
    """Load components with latest enrichment and risk scores."""
    result = await session.execute(
        select(Component)
        .where(Component.bom_id.in_(bom_ids))
        .options(
            selectinload(Component.enrichment_records),
            selectinload(Component.risk_scores),
        )
    )
    components = result.scalars().all()

    out = []
    for comp in components:
        latest_enrichment = (
            merge_enrichment_records(list(comp.enrichment_records))
            if comp.enrichment_records
            else None
        )
        latest_risk = max(comp.risk_scores, key=lambda r: r.scored_at, default=None) if comp.risk_scores else None
        out.append((comp, latest_enrichment, latest_risk))
    return out


def _build_result(
    affected,
    baseline_bom_risk,
    scenario_bom_risk,
    bom_names: dict[str, str] | None = None,
) -> dict:
    deltas = [a["delta"] for a in affected]
    bom_set = set()
    for a in affected:
        bom_set.update(a["boms"])

    return {
        "summary": {
            "total_components_affected": len(affected),
            "boms_affected": len(bom_set),
            "avg_risk_delta": round(sum(deltas) / max(len(deltas), 1), 1),
            "components_at_critical": sum(1 for a in affected if a["scenario_risk"] >= 70),
            "components_with_no_alternate_source": sum(1 for a in affected if a["scenario_risk"] >= 95),
        },
        "baseline_bom_risk": baseline_bom_risk,
        "scenario_bom_risk": scenario_bom_risk,
        "bom_names": bom_names or {},
        "affected_components": sorted(affected, key=lambda a: a["delta"], reverse=True),
    }


_HANDLERS = {
    "country_disruption": _handle_country_disruption,
    "supplier_failure": _handle_supplier_failure,
    "obsolescence_wave": _handle_obsolescence_wave,
    "component_removal": _handle_component_removal,
    "demand_spike": _handle_demand_spike,
}
