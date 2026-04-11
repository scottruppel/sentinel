from __future__ import annotations

import httpx
import structlog

from sentinel.config import settings
from sentinel.enrichment.base import EnrichmentProvider, EnrichmentResult

log = structlog.get_logger()


def _dig(d: dict, *keys: str):
    cur: object = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _map_z2data_payload(data: dict, raw: dict) -> EnrichmentResult | None:
    if not data:
        return None

    country = (
        data.get("country_of_origin")
        or data.get("countryOfOrigin")
        or _dig(data, "manufacturing", "country")
        or _dig(data, "site", "country")
    )

    return EnrichmentResult(
        source="z2data",
        country_of_origin=str(country) if country else None,
        lifecycle_status=data.get("lifecycle_status") or data.get("lifecycleStatus"),
        total_inventory=data.get("inventory"),
        num_alternates=data.get("num_alternates"),
        single_source=data.get("single_source"),
        raw_data=raw,
    )


class Z2DataProvider(EnrichmentProvider):
    """Z2Data REST client; configure `z2data_lookup_path` from vendor trial documentation."""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=45.0)

    @property
    def source_name(self) -> str:
        return "z2data"

    async def enrich(self, mpn: str, manufacturer: str | None = None) -> EnrichmentResult | None:
        if not settings.z2data_api_key:
            log.debug("z2data_skipped", reason="no_api_key", mpn=mpn)
            return None
        if not settings.z2data_lookup_path.strip():
            log.debug("z2data_skipped", reason="no_lookup_path", mpn=mpn)
            return None

        base = settings.z2data_api_url.rstrip("/")
        path = settings.z2data_lookup_path.strip().lstrip("/")
        url = f"{base}/{path}"

        try:
            resp = await self._client.get(
                url,
                params={
                    "mpn": mpn,
                    "partNumber": mpn,
                    "manufacturer": manufacturer or "",
                },
                headers={"Authorization": f"Bearer {settings.z2data_api_key}"},
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPStatusError as e:
            log.warning(
                "z2data_http_error",
                mpn=mpn,
                status=e.response.status_code,
                body=e.response.text[:500],
            )
            return None
        except httpx.HTTPError as e:
            log.warning("z2data_request_failed", mpn=mpn, error=str(e))
            return None
        except ValueError as e:
            log.warning("z2data_invalid_json", mpn=mpn, error=str(e))
            return None

        if isinstance(payload, list) and payload:
            payload = payload[0]
        if not isinstance(payload, dict):
            log.warning("z2data_unexpected_shape", mpn=mpn)
            return None

        result = _map_z2data_payload(payload, {"response": payload})
        if result:
            log.info("z2data_enriched", mpn=mpn, has_country=bool(result.country_of_origin))
        return result

    async def health_check(self) -> bool:
        return bool(settings.z2data_api_key and settings.z2data_lookup_path.strip())
