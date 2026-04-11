"""Tests for the what-if scenario engine."""
import pytest

from sentinel.whatif.scenarios import (
    SCENARIO_TEMPLATES,
    CountryDisruptionScenario,
    SupplierFailureScenario,
    ObsolescenceWaveScenario,
    ComponentRemovalScenario,
    DemandSpikeScenario,
)
from sentinel.whatif.engine import _build_result


class TestScenarioTypes:
    def test_country_disruption_dataclass(self):
        s = CountryDisruptionScenario(country="Taiwan", severity="total_loss")
        assert s.type == "country_disruption"
        assert s.country == "Taiwan"

    def test_supplier_failure_dataclass(self):
        s = SupplierFailureScenario(manufacturer="Analog Devices", failure_mode="bankruptcy")
        assert s.type == "supplier_failure"

    def test_obsolescence_wave_dataclass(self):
        s = ObsolescenceWaveScenario(target_statuses=["NRFND", "Last Time Buy"], time_horizon_months=6)
        assert s.type == "obsolescence_wave"
        assert len(s.target_statuses) == 2

    def test_component_removal_dataclass(self):
        s = ComponentRemovalScenario(mpns=["XC7Z010-1CLG225C"], reason="sanction")
        assert s.type == "component_removal"

    def test_demand_spike_dataclass(self):
        s = DemandSpikeScenario(multiplier=3.0)
        assert s.type == "demand_spike"
        assert s.multiplier == 3.0


class TestScenarioTemplates:
    def test_templates_exist(self):
        assert len(SCENARIO_TEMPLATES) >= 4

    def test_template_structure(self):
        for t in SCENARIO_TEMPLATES:
            assert "name" in t
            assert "scenario_type" in t
            assert "parameters" in t


class TestBuildResult:
    def test_empty_affected(self):
        result = _build_result([], {}, {})
        assert result["summary"]["total_components_affected"] == 0
        assert result["summary"]["boms_affected"] == 0
        assert result.get("bom_names") == {}

    def test_with_affected(self):
        affected = [
            {
                "mpn": "TEST-MPN",
                "manufacturer": "TestCo",
                "boms": ["BOM-A"],
                "baseline_risk": 30.0,
                "scenario_risk": 80.0,
                "delta": 50.0,
                "risk_factors": ["Test factor"],
                "recommendation": "Test recommendation",
            },
            {
                "mpn": "TEST-MPN-2",
                "manufacturer": "TestCo",
                "boms": ["BOM-A", "BOM-B"],
                "baseline_risk": 20.0,
                "scenario_risk": 95.0,
                "delta": 75.0,
                "risk_factors": ["Critical"],
                "recommendation": "Replace immediately",
            },
        ]
        baseline = {"bom-1": 25.0}
        scenario = {"bom-1": 60.0}

        result = _build_result(affected, baseline, scenario, {"bom-1": "Test BOM"})
        assert result["bom_names"] == {"bom-1": "Test BOM"}
        assert result["summary"]["total_components_affected"] == 2
        assert result["summary"]["boms_affected"] == 2
        assert result["summary"]["components_at_critical"] == 2
        assert result["summary"]["components_with_no_alternate_source"] == 1
        assert result["affected_components"][0]["delta"] >= result["affected_components"][1]["delta"]

    def test_avg_delta(self):
        affected = [
            {"mpn": "A", "manufacturer": "X", "boms": ["B1"], "baseline_risk": 10, "scenario_risk": 50, "delta": 40, "risk_factors": [], "recommendation": None},
            {"mpn": "B", "manufacturer": "X", "boms": ["B1"], "baseline_risk": 20, "scenario_risk": 80, "delta": 60, "risk_factors": [], "recommendation": None},
        ]
        result = _build_result(affected, {}, {})
        assert result["summary"]["avg_risk_delta"] == 50.0
