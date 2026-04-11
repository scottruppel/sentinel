from __future__ import annotations

import httpx
import structlog

from sentinel.config import settings
from sentinel.enrichment.base import EnrichmentProvider, EnrichmentResult

log = structlog.get_logger()

NEXAR_TOKEN_URL = "https://identity.nexar.com/connect/token"
NEXAR_GRAPHQL_URL = "https://api.nexar.com/graphql"

NEXAR_MPN_QUERY = """
query SearchMPN($mpn: String!) {
  supSearchMpn(q: $mpn, limit: 3) {
    results {
      part {
        mpn
        manufacturer { name }
        manufacturerUrl
        bestDatasheet { url }
        totalAvail
        medianPrice1000 { price currency }
        specs { attribute { name shortname } displayValue }
        sellers {
          company { name isDistributorApi isAuthorized }
          offers {
            inventoryLevel
            moq
            prices { price quantity currency }
            factoryLeadDays
          }
        }
        descriptions { text }
        category { name parentId }
      }
    }
  }
}
"""


class NexarProvider(EnrichmentProvider):
    def __init__(self):
        self._token: str | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def source_name(self) -> str:
        return "nexar"

    async def _ensure_token(self):
        if self._token:
            return
        if not settings.nexar_client_id or not settings.nexar_client_secret:
            raise RuntimeError("Nexar credentials not configured")

        resp = await self._client.post(
            NEXAR_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.nexar_client_id,
                "client_secret": settings.nexar_client_secret,
            },
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        log.info("nexar_token_acquired")

    async def enrich(self, mpn: str, manufacturer: str | None = None) -> EnrichmentResult | None:
        try:
            await self._ensure_token()
        except RuntimeError:
            log.warning("nexar_not_configured", mpn=mpn)
            return None

        try:
            resp = await self._client.post(
                NEXAR_GRAPHQL_URL,
                json={"query": NEXAR_MPN_QUERY, "variables": {"mpn": mpn}},
                headers={"Authorization": f"Bearer {self._token}"},
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            log.error("nexar_request_failed", mpn=mpn, error=str(e))
            return None

        results = data.get("data", {}).get("supSearchMpn", {}).get("results", [])
        if not results:
            log.warning("nexar_no_results", mpn=mpn)
            return EnrichmentResult(source="nexar", raw_data=data)

        part = results[0].get("part", {})
        return self._parse_part(part, data)

    def _parse_specs(self, part: dict) -> dict:
        """Extract structured hints from Octopart/Nexar specs (shortname + displayValue)."""
        out: dict[str, str] = {}
        for spec in part.get("specs") or []:
            attr = spec.get("attribute") or {}
            sn = (attr.get("shortname") or "").lower()
            dv = (spec.get("displayValue") or "").strip()
            if sn and dv:
                out[sn] = dv
        return out

    def _map_nexar_lifecycle(self, display: str) -> str | None:
        """Map Nexar homogenized lifecycle strings to SENTINEL lifecycle labels."""
        d = display.upper()
        if "OBSOLETE" in d:
            return "Obsolete"
        if "NRND" in d or "NOT RECOMMENDED" in d:
            return "NRFND"
        if "LAST TIME BUY" in d or "LAST-TIME BUY" in d:
            return "Last Time Buy"
        if "PRODUCTION" in d or "ACTIVE" in d or " NEW" in d or d.startswith("NEW "):
            return "Active"
        if "EOL" in d:
            return "Obsolete"
        return None

    def _country_from_specs(self, specs_map: dict[str, str]) -> str | None:
        for key in ("countryoforigin", "country_of_origin", "origin", "country"):
            if key in specs_map:
                raw = specs_map[key].split("(")[0].strip()
                if raw:
                    return raw
        return None

    def _parse_part(self, part: dict, raw: dict) -> EnrichmentResult:
        total_inventory = part.get("totalAvail", 0)
        sellers = part.get("sellers", [])
        distributor_count = len([s for s in sellers if s.get("company", {}).get("isAuthorized")])

        lead_days = []
        for seller in sellers:
            for offer in seller.get("offers", []):
                if offer.get("factoryLeadDays"):
                    lead_days.append(offer["factoryLeadDays"])

        avg_lead = int(sum(lead_days) / len(lead_days)) if lead_days else None

        specs_map = self._parse_specs(part)
        lifecycle_status = None
        for spec_key in ("lifecyclestatus", "manufacturerlifecyclestatus"):
            if spec_key in specs_map:
                lifecycle_status = self._map_nexar_lifecycle(specs_map[spec_key])
                if lifecycle_status:
                    break

        country = self._country_from_specs(specs_map)

        rohs_compliant = None
        reach_compliant = None
        for key, val in specs_map.items():
            u = val.upper()
            if "rohs" in key and ("COMPLIANT" in u or "YES" in u):
                rohs_compliant = "NON" not in u and "NON-COMPLIANT" not in u
            if "reach" in key and ("COMPLIANT" in u or "YES" in u):
                reach_compliant = "NON" not in u

        num_alternates = None
        if "alternates" in specs_map:
            try:
                num_alternates = int(specs_map["alternates"].split()[0])
            except (ValueError, IndexError):
                pass

        return EnrichmentResult(
            source="nexar",
            lifecycle_status=lifecycle_status,
            total_inventory=total_inventory,
            distributor_count=distributor_count,
            avg_lead_time_days=avg_lead,
            country_of_origin=country,
            num_alternates=num_alternates,
            rohs_compliant=rohs_compliant,
            reach_compliant=reach_compliant,
            raw_data=raw,
        )

    async def health_check(self) -> bool:
        try:
            await self._ensure_token()
            return True
        except Exception:
            return False
