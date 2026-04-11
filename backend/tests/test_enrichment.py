"""Tests for the enrichment pipeline: providers, orchestrator, and synthetic data."""
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from sentinel.enrichment.base import EnrichmentResult, EnrichmentProvider
from sentinel.enrichment.merge import merge_enrichment_records
from sentinel.enrichment.siliconexpert import SiliconExpertProvider
from sentinel.enrichment.z2data import Z2DataProvider


class MockProvider(EnrichmentProvider):
    def __init__(self, source: str, result: EnrichmentResult | None = None, fail: bool = False):
        self._source = source
        self._result = result
        self._fail = fail
        self.call_count = 0

    @property
    def source_name(self) -> str:
        return self._source

    async def enrich(self, mpn: str, manufacturer: str | None = None) -> EnrichmentResult | None:
        self.call_count += 1
        if self._fail:
            raise RuntimeError("Provider failure")
        return self._result

    async def health_check(self) -> bool:
        return not self._fail


def _fake_record(
    source: str,
    *,
    lifecycle_status=None,
    total_inventory=None,
    country_of_origin=None,
    fetched_at=None,
):
    return SimpleNamespace(
        id=uuid4(),
        component_id=uuid4(),
        source=source,
        fetched_at=fetched_at or datetime.now(timezone.utc),
        lifecycle_status=lifecycle_status,
        yteol=None,
        total_inventory=total_inventory,
        avg_lead_time_days=None,
        distributor_count=None,
        num_alternates=None,
        country_of_origin=country_of_origin,
        single_source=None,
        rohs_compliant=None,
        reach_compliant=None,
        data={},
    )


class TestNexarParse:
    def test_parse_lifecycle_from_specs(self):
        from sentinel.enrichment.nexar import NexarProvider

        p = NexarProvider()
        part = {
            "totalAvail": 1000,
            "sellers": [],
            "specs": [
                {
                    "attribute": {"shortname": "lifecyclestatus", "name": "Lifecycle Status"},
                    "displayValue": "Production (Last Updated: 2 years ago)",
                }
            ],
        }
        raw = {"data": {}}
        r = p._parse_part(part, raw)
        assert r.lifecycle_status == "Active"
        assert r.total_inventory == 1000

    def test_parse_nrnd(self):
        from sentinel.enrichment.nexar import NexarProvider

        p = NexarProvider()
        part = {
            "totalAvail": 0,
            "sellers": [],
            "specs": [
                {
                    "attribute": {"shortname": "lifecyclestatus", "name": "Lifecycle Status"},
                    "displayValue": "NRND (Not recommended for new designs)",
                }
            ],
        }
        r = p._parse_part(part, {})
        assert r.lifecycle_status == "NRFND"


class TestMergeEnrichment:
    def test_priority_prefers_siliconexpert_lifecycle(self):
        r1 = _fake_record("nexar", lifecycle_status="Obsolete", total_inventory=100)
        r2 = _fake_record("siliconexpert", lifecycle_status="Active", total_inventory=None)
        m = merge_enrichment_records([r1, r2], ("siliconexpert", "z2data", "nexar", "synthetic"))
        assert m is not None
        assert m.lifecycle_status == "Active"
        assert m.total_inventory == 100
        assert m.field_sources.get("lifecycle_status") == "siliconexpert"
        assert m.field_sources.get("total_inventory") == "nexar"

    def test_nexar_supply_when_only_nexar(self):
        r = _fake_record("nexar", lifecycle_status=None, total_inventory=5000)
        m = merge_enrichment_records([r])
        assert m.total_inventory == 5000


class TestEnrichmentResult:
    def test_defaults(self):
        r = EnrichmentResult(source="test")
        assert r.source == "test"
        assert r.lifecycle_status is None
        assert r.raw_data == {}

    def test_full_result(self):
        r = EnrichmentResult(
            source="nexar",
            lifecycle_status="Active",
            yteol=8.0,
            total_inventory=5000,
            avg_lead_time_days=14,
            distributor_count=6,
            num_alternates=3,
            country_of_origin="USA",
            single_source=False,
            rohs_compliant=True,
            reach_compliant=True,
            raw_data={"test": True},
        )
        assert r.lifecycle_status == "Active"
        assert r.total_inventory == 5000


class TestStubs:
    @pytest.mark.asyncio
    async def test_siliconexpert_returns_none(self):
        provider = SiliconExpertProvider()
        result = await provider.enrich("ADAR1000BCPZ")
        assert result is None

    @pytest.mark.asyncio
    async def test_z2data_returns_none(self):
        provider = Z2DataProvider()
        result = await provider.enrich("ADAR1000BCPZ")
        assert result is None


class TestMockProvider:
    @pytest.mark.asyncio
    async def test_success(self):
        expected = EnrichmentResult(source="mock", lifecycle_status="Active")
        provider = MockProvider("mock", expected)
        result = await provider.enrich("TEST-MPN")
        assert result is not None
        assert result.lifecycle_status == "Active"
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_failure_raises(self):
        provider = MockProvider("mock", fail=True)
        with pytest.raises(RuntimeError):
            await provider.enrich("TEST-MPN")

    @pytest.mark.asyncio
    async def test_none_result(self):
        provider = MockProvider("mock", result=None)
        result = await provider.enrich("TEST-MPN")
        assert result is None


class TestSyntheticEnrichment:
    def test_lifecycle_distribution(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from scripts.generate_synthetic_enrichment import _pick_lifecycle, _generate_for_component

        import random
        random.seed(123)
        statuses = [_pick_lifecycle() for _ in range(1000)]
        active_pct = statuses.count("Active") / len(statuses)
        assert 0.40 < active_pct < 0.70, f"Active percentage {active_pct} out of expected range"

    def test_hand_tuned_profiles(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from scripts.generate_synthetic_enrichment import _generate_for_component

        data = _generate_for_component("ADAR1000BCPZ", "IC")
        assert data["lifecycle_status"] == "Active (single source)"
        assert data["single_source"] is True
        assert data["country_of_origin"] == "USA"

    def test_generic_component(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from scripts.generate_synthetic_enrichment import _generate_for_component

        import random
        random.seed(42)
        data = _generate_for_component("UNKNOWN-PART", "Capacitor")
        assert "lifecycle_status" in data
        assert "total_inventory" in data
        assert data["total_inventory"] > 0
