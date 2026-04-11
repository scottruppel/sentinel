"""Tests for the risk scoring engine: dimension scoring and composites."""
import pytest

from sentinel.risk.scorer import (
    score_lifecycle_risk,
    score_supply_risk,
    score_geographic_risk,
    score_supplier_risk,
    score_regulatory_risk,
    compute_composite,
    compute_bom_risk,
    _generate_recommendation,
)
from sentinel.risk.weights import DEFAULT_PROFILE, SUPPLY_CHAIN_PROFILE, RiskWeightProfile


class TestLifecycleRisk:
    def test_obsolete_no_alternates(self):
        r = score_lifecycle_risk("Obsolete", 0, 0, True)
        assert r.score == 100

    def test_obsolete_with_alternates(self):
        r = score_lifecycle_risk("Obsolete", 0, 3, True)
        assert r.score == 80

    def test_ltb_open(self):
        r = score_lifecycle_risk("Last Time Buy", 1.5, 2, False)
        assert r.score == 70

    def test_ltb_expired(self):
        r = score_lifecycle_risk("Last Time Buy", 0, 0, True)
        assert r.score == 90

    def test_nrfnd_short(self):
        r = score_lifecycle_risk("NRFND", 1.5, 2, False)
        assert r.score == 60

    def test_nrfnd_mid(self):
        r = score_lifecycle_risk("NRFND", 3.0, 2, False)
        assert r.score == 40

    def test_active_single(self):
        r = score_lifecycle_risk("Active", 10.0, 0, True)
        assert r.score == 25

    def test_active_multi(self):
        r = score_lifecycle_risk("Active", 10.0, 5, False)
        assert r.score == 5

    def test_unknown(self):
        r = score_lifecycle_risk(None, None, None, None)
        assert r.score == 50

    def test_determinism(self):
        a = score_lifecycle_risk("NRFND", 2.5, 1, True)
        b = score_lifecycle_risk("NRFND", 2.5, 1, True)
        assert a.score == b.score


class TestSupplyRisk:
    def test_zero_inventory(self):
        r = score_supply_risk(0, 0, 0)
        assert r.score == 100

    def test_low_inventory(self):
        r = score_supply_risk(50, 14, 5)
        assert r.score == 75

    def test_long_lead_time(self):
        r = score_supply_risk(10000, 400, 5)
        assert r.score == 80

    def test_healthy(self):
        r = score_supply_risk(50000, 14, 10)
        assert r.score == 5


class TestGeographicRisk:
    def test_sanctioned(self):
        r = score_geographic_risk("Russia")
        assert r.score == 100

    def test_high_risk(self):
        r = score_geographic_risk("China")
        assert r.score == 60

    def test_taiwan(self):
        r = score_geographic_risk("Taiwan")
        assert r.score == 55

    def test_standard(self):
        r = score_geographic_risk("USA")
        assert r.score == 10

    def test_unknown(self):
        r = score_geographic_risk(None)
        assert r.score == 50


class TestSupplierRisk:
    def test_sole_source(self):
        r = score_supplier_risk(True, 0, "ADI")
        assert r.score == 85

    def test_single_source_with_alts(self):
        r = score_supplier_risk(True, 2, "ADI")
        assert r.score == 65

    def test_multi_source(self):
        r = score_supplier_risk(False, 5, "TI")
        assert r.score == 5

    def test_dual_source(self):
        r = score_supplier_risk(False, 1, "TI")
        assert r.score == 15


class TestRegulatoryRisk:
    def test_non_rohs(self):
        r = score_regulatory_risk(False, True)
        assert r.score == 60

    def test_non_reach(self):
        r = score_regulatory_risk(True, False)
        assert r.score == 50

    def test_both_non_compliant(self):
        r = score_regulatory_risk(False, False)
        assert r.score == 60

    def test_compliant(self):
        r = score_regulatory_risk(True, True)
        assert r.score == 5


class TestComposite:
    def test_all_zero(self):
        from sentinel.risk.scorer import DimensionScore
        dims = [DimensionScore(score=0)] * 5
        result = compute_composite(*dims, profile=DEFAULT_PROFILE)
        assert result == 0.0

    def test_all_hundred(self):
        from sentinel.risk.scorer import DimensionScore
        dims = [DimensionScore(score=100)] * 5
        result = compute_composite(*dims, profile=DEFAULT_PROFILE)
        assert result == 100.0

    def test_weight_profiles_differ(self):
        from sentinel.risk.scorer import DimensionScore
        lifecycle = DimensionScore(score=100)
        supply = DimensionScore(score=0)
        geo = DimensionScore(score=0)
        supplier = DimensionScore(score=0)
        reg = DimensionScore(score=0)

        default_score = compute_composite(lifecycle, supply, geo, supplier, reg, DEFAULT_PROFILE)
        sc_score = compute_composite(lifecycle, supply, geo, supplier, reg, SUPPLY_CHAIN_PROFILE)
        assert default_score == 30.0
        assert sc_score == 15.0


class TestBomRisk:
    def test_empty(self):
        result = compute_bom_risk([])
        assert result["overall_score"] == 0
        assert result["critical_count"] == 0

    def test_categorization(self):
        from unittest.mock import MagicMock
        import uuid
        scores = []
        for val in [80, 55, 35, 20]:
            m = MagicMock()
            m.composite_score = val
            m.component_id = uuid.uuid4()
            m.profile = "default"
            scores.append(m)

        result = compute_bom_risk(scores)
        assert result["critical_count"] == 1
        assert result["high_count"] == 1
        assert result["medium_count"] == 1
        assert result["low_count"] == 1
        assert len(result["top_risks"]) == 4

    def test_risk_by_category(self):
        from unittest.mock import MagicMock
        import uuid

        cat_id = uuid.uuid4()
        m_ic = MagicMock()
        m_ic.composite_score = 60.0
        m_ic.component_id = cat_id
        m_ic.profile = "default"
        m_cap = MagicMock()
        m_cap.composite_score = 40.0
        m_cap.component_id = uuid.uuid4()
        m_cap.profile = "default"

        comp_ic = MagicMock()
        comp_ic.category = "IC"
        comp_cap = MagicMock()
        comp_cap.category = "Capacitor"

        by_id = {cat_id: comp_ic, m_cap.component_id: comp_cap}
        result = compute_bom_risk([m_ic, m_cap], by_id)
        assert "IC" in result["risk_by_category"]
        assert result["risk_by_category"]["IC"]["count"] == 1
        assert result["risk_by_category"]["IC"]["avg_composite"] == 60.0
        assert result["risk_by_category"]["Capacitor"]["avg_composite"] == 40.0


class TestRecommendation:
    def test_low_risk_no_recommendation(self):
        from sentinel.risk.scorer import RiskFactor
        r = _generate_recommendation(15, [RiskFactor("active_multi", "Active", 5)])
        assert r is None

    def test_obsolete_recommendation(self):
        from sentinel.risk.scorer import RiskFactor
        r = _generate_recommendation(90, [RiskFactor("obsolete_no_alt", "Obsolete", 100)])
        assert r is not None
        assert "lifetime buy" in r.lower() or "alternate" in r.lower()
