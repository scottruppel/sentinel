"""Intelligence: policy, packaging, merge with Tier B."""
from __future__ import annotations

import uuid

from sentinel.db.models import Bom, Component, RiskScoreRecord
from sentinel.enrichment.merge import MergedEnrichment
from sentinel.intelligence.context_packager import pack_component_context
from sentinel.intelligence.policy import POLICY_VERSION, RedactionPolicy, stable_component_token
from sentinel.intelligence.signals import match_events_for_component
from sentinel.db.models import MarketEvent


def test_stable_component_token_deterministic():
    u = str(uuid.uuid4())
    assert stable_component_token(u) == stable_component_token(u)
    assert len(stable_component_token(u)) == 12


def test_pack_component_strips_bom_by_default():
    bom = Bom(
        name="Secret Program",
        program="CLASSIFIED",
        source_filename="secret.csv",
        description=None,
        component_count=1,
    )
    comp = Component(
        bom_id=uuid.uuid4(),
        mpn="XC7Z010",
        mpn_normalized="xc7z010",
        manufacturer="AMD",
        reference_designator="U1",
        quantity=99,
        category="IC",
    )
    merged = MergedEnrichment(
        lifecycle_status="Active",
        yteol=5.0,
        total_inventory=1000,
        avg_lead_time_days=60,
        distributor_count=4,
        num_alternates=2,
        country_of_origin="Taiwan",
        single_source=False,
        rohs_compliant=True,
        reach_compliant=True,
        field_sources={},
    )
    risk = RiskScoreRecord(
        component_id=comp.id,
        profile="default",
        lifecycle_risk=20,
        supply_risk=30,
        geographic_risk=40,
        supplier_risk=25,
        regulatory_risk=5,
        composite_score=35,
        risk_factors=[{"factor": "t", "detail": "test", "contribution": 10}],
        recommendation="Qualify alt",
    )
    policy = RedactionPolicy()
    ctx = pack_component_context(comp, merged, risk, bom, policy)
    assert "Secret" not in str(ctx)
    assert ctx["mpn"] == "XC7Z010"
    assert ctx["risk"]["composite_score"] == 35
    assert "bom" not in ctx or "name" not in ctx.get("bom", {})


def test_match_events_scores_overlap():
    comp = Component(
        bom_id=uuid.uuid4(),
        mpn="AD9363",
        mpn_normalized="ad9363",
        manufacturer="Analog Devices",
        category="IC",
    )
    merged = MergedEnrichment(
        country_of_origin="Taiwan",
        field_sources={},
    )
    ev = MarketEvent(
        title="Taiwan semiconductor capacity outlook",
        summary="Foundry utilization and export controls",
        source_url="https://example.com/a",
        event_type="rss",
        region_tags=["Taiwan"],
        keywords=["semiconductor", "supply chain"],
    )
    matched = match_events_for_component(comp, merged, [ev], max_events=5)
    assert len(matched) >= 1
    assert matched[0].title.startswith("Taiwan")


def test_policy_version_constant():
    assert POLICY_VERSION.startswith("2026")
