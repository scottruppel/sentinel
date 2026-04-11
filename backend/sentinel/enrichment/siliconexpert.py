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


def _map_siliconexpert_payload(data: dict, raw: dict) -> EnrichmentResult | None:
    """
    Map vendor JSON to EnrichmentResult. Tries common key paths; extend when trial docs arrive.
    """
    if not data:
        return None

    lifecycle = (
        _dig(data, "lifecycle", "status")
        or _dig(data, "part", "lifecycle")
        or data.get("lifecycleStatus")
        or data.get("lifecycle_status")
    )
    yteol = data.get("yteol") or _dig(data, "part", "yteol")
    if yteol is not None:
        try:
            yteol = float(yteol)
        except (TypeError, ValueError):
            yteol = None

    return EnrichmentResult(
        source="siliconexpert",
        lifecycle_status=str(lifecycle) if lifecycle is not None else None,
        yteol=yteol,
        total_inventory=data.get("inventory") or data.get("total_inventory"),
        num_alternates=data.get("num_alternates") or data.get("alternates_count"),
        country_of_origin=data.get("country_of_origin") or data.get("countryOfOrigin"),
        single_source=data.get("single_source"),
        rohs_compliant=data.get("rohs_compliant"),
        reach_compliant=data.get("reach_compliant"),
        raw_data=raw,
    )


class SiliconExpertProvider(EnrichmentProvider):
    """SiliconExpert REST client; configure `siliconexpert_lookup_path` from vendor trial documentation."""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=45.0)

    @property
    def source_name(self) -> str:
        return "siliconexpert"

    async def enrich(self, mpn: str, manufacturer: str | None = None) -> EnrichmentResult | None:
        if not settings.siliconexpert_api_key:
            log.debug("siliconexpert_skipped", reason="no_api_key", mpn=mpn)
            return None
        if not settings.siliconexpert_lookup_path.strip():
            log.debug("siliconexpert_skipped", reason="no_lookup_path", mpn=mpn)
            return None

        base = settings.siliconexpert_api_url.rstrip("/")
        path = settings.siliconexpert_lookup_path.strip().lstrip("/")
        url = f"{base}/{path}"

        try:
            resp = await self._client.get(
                url,
                params={
                    "mpn": mpn,
                    "partNumber": mpn,
                    "manufacturer": manufacturer or "",
                },
                headers={"Authorization": f"Bearer {settings.siliconexpert_api_key}"},
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPStatusError as e:
            log.warning(
                "siliconexpert_http_error",
                mpn=mpn,
                status=e.response.status_code,
                body=e.response.text[:500],
            )
            return None
        except httpx.HTTPError as e:
            log.warning("siliconexpert_request_failed", mpn=mpn, error=str(e))
            return None
        except ValueError as e:
            log.warning("siliconexpert_invalid_json", mpn=mpn, error=str(e))
            return None

        if isinstance(payload, list) and payload:
            payload = payload[0]
        if not isinstance(payload, dict):
            log.warning("siliconexpert_unexpected_shape", mpn=mpn)
            return None

        result = _map_siliconexpert_payload(payload, {"response": payload})
        if result:
            log.info("siliconexpert_enriched", mpn=mpn, has_lifecycle=bool(result.lifecycle_status))
        return result

    async def health_check(self) -> bool:
        return bool(settings.siliconexpert_api_key and settings.siliconexpert_lookup_path.strip())
