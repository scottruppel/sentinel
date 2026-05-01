"""Mouser Search API — pricing, stock, lead time, lifecycle (API key)."""
from __future__ import annotations

import re

import httpx
import structlog

from sentinel.config import settings
from sentinel.enrichment.base import EnrichmentProvider, EnrichmentResult

log = structlog.get_logger()

DEFAULT_MOUSER_API = "https://api.mouser.com/api/v1"


def _first_part(payload: dict) -> dict | None:
    sr = payload.get("SearchResults") or {}
    parts = sr.get("Parts")
    if isinstance(parts, list) and parts:
        p0 = parts[0]
        return p0 if isinstance(p0, dict) else None
    return None


def _map_lifecycle(raw: str | None) -> str | None:
    if not raw:
        return None
    u = raw.upper()
    if "OBSOLETE" in u or "OBS " in u:
        return "Obsolete"
    if "END OF LIFE" in u or "EOL" in u:
        return "Obsolete"
    if "LAST" in u and "BUY" in u:
        return "Last Time Buy"
    if "NOT RECOMMENDED" in u or "NRND" in u:
        return "NRFND"
    if "ACTIVE" in u or "PRODUCTION" in u or "NEW" in u:
        return "Active"
    return None


def _parse_part(part: dict, raw: dict) -> EnrichmentResult:
    # Availability: stock string or int
    avail = part.get("Availability")
    inv: int | None = None
    if isinstance(avail, str):
        m = re.search(r"(\d+)", avail.replace(",", ""))
        if m:
            try:
                inv = int(m.group(1))
            except ValueError:
                inv = None
    elif isinstance(avail, (int, float)):
        inv = int(avail)

    lead_raw = part.get("LeadTime") or part.get("FactoryLeadDays") or ""
    lead_days: int | None = None
    if isinstance(lead_raw, (int, float)):
        lead_days = int(lead_raw)
    elif isinstance(lead_raw, str):
        m = re.search(r"(\d+)\s*(day|week)", lead_raw, re.I)
        if m:
            n = int(m.group(1))
            unit = (m.group(2) or "").lower()
            lead_days = n * 7 if unit.startswith("week") else n

    lifecycle = _map_lifecycle(part.get("LifecycleStatus") or part.get("ProductLifeCycle"))

    rohs = part.get("ROHSStatus") or part.get("RoHSStatus")
    rohs_ok: bool | None = None
    if isinstance(rohs, str):
        ru = rohs.upper()
        if "COMPLIANT" in ru or "YES" in ru:
            rohs_ok = "NON" not in ru

    alts = part.get("AlternateMPNs") or part.get("AlternateParts")
    n_alt: int | None = None
    if isinstance(alts, list):
        n_alt = len(alts)
    elif isinstance(alts, (int, float)):
        n_alt = int(alts)

    return EnrichmentResult(
        source="mouser",
        lifecycle_status=lifecycle,
        total_inventory=inv,
        avg_lead_time_days=lead_days,
        distributor_count=1,
        num_alternates=n_alt,
        rohs_compliant=rohs_ok,
        reach_compliant=None,
        raw_data=raw,
    )


class MouserProvider(EnrichmentProvider):
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=45.0)

    @property
    def source_name(self) -> str:
        return "mouser"

    async def enrich(self, mpn: str, manufacturer: str | None = None) -> EnrichmentResult | None:
        key = (settings.mouser_api_key or "").strip()
        if not key:
            log.debug("mouser_skipped", reason="no_api_key", mpn=mpn)
            return None

        base = (settings.mouser_api_url or DEFAULT_MOUSER_API).rstrip("/")
        url = f"{base}/search/keyword"
        body = {
            "SearchByKeywordRequest": {
                "keyword": mpn.strip(),
                "records": 10,
                "startingRecord": 0,
            }
        }
        try:
            resp = await self._client.post(
                f"{url}?apiKey={key}",
                json=body,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPStatusError as e:
            log.warning(
                "mouser_http_error",
                mpn=mpn,
                status=e.response.status_code,
                body=e.response.text[:500],
            )
            return None
        except httpx.HTTPError as e:
            log.warning("mouser_request_failed", mpn=mpn, error=str(e))
            return None
        except ValueError as e:
            log.warning("mouser_invalid_json", mpn=mpn, error=str(e))
            return None

        if not isinstance(payload, dict):
            return None
        part = _first_part(payload)
        if not part:
            log.info("mouser_no_results", mpn=mpn)
            return EnrichmentResult(source="mouser", raw_data=payload)

        return _parse_part(part, payload)

    async def health_check(self) -> bool:
        return bool((settings.mouser_api_key or "").strip())
