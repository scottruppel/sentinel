"""Digi-Key Product Information v4 — keyword search (OAuth2 client credentials)."""
from __future__ import annotations

import time

import httpx
import structlog

from sentinel.config import settings
from sentinel.enrichment.base import EnrichmentProvider, EnrichmentResult

log = structlog.get_logger()

# Production vs sandbox hosts
DK_PROD = "https://api.digikey.com"
DK_SANDBOX = "https://sandbox-api.digikey.com"


def _dk_base() -> str:
    return DK_SANDBOX if settings.digikey_use_sandbox else DK_PROD


def _map_product_status(status: str | None) -> str | None:
    if not status:
        return None
    u = status.upper()
    if "OBS" in u or "EOL" in u:
        return "Obsolete"
    if "NOT FOR NEW" in u or "NRND" in u:
        return "NRFND"
    if "LAST" in u and "BUY" in u:
        return "Last Time Buy"
    if "ACTIVE" in u or "PREVIEW" in u:
        return "Active"
    return None


def _first_product(payload: dict) -> dict | None:
    ksr = payload.get("KeywordSearchResult") or {}
    prods = ksr.get("Products")
    if isinstance(prods, list) and prods:
        p0 = prods[0]
        return p0 if isinstance(p0, dict) else None
    # alternate shape
    prods = payload.get("Products")
    if isinstance(prods, list) and prods and isinstance(prods[0], dict):
        return prods[0]
    return None


def _parse_product(prod: dict, raw: dict) -> EnrichmentResult:
    qty = prod.get("QuantityAvailable")
    inv: int | None = None
    if isinstance(qty, (int, float)):
        inv = int(qty)

    lead_days: int | None = None
    mfg_lead = prod.get("ManufacturerLeadWeeks")
    if isinstance(mfg_lead, (int, float)):
        lead_days = int(float(mfg_lead) * 7)
    else:
        ship_lead = prod.get("ShippingInfo") or {}
        if isinstance(ship_lead, dict):
            w = ship_lead.get("LeadWeeks")
            if isinstance(w, (int, float)):
                lead_days = int(float(w) * 7)

    ps = prod.get("ProductStatus")
    if isinstance(ps, dict):
        status_str = ps.get("Status")
    elif isinstance(ps, str):
        status_str = ps
    else:
        status_str = None
    lifecycle = _map_product_status(status_str if isinstance(status_str, str) else None)

    rohs = prod.get("RoHSStatus")
    rohs_ok: bool | None = None
    if isinstance(rohs, str):
        ru = rohs.upper()
        if "COMPLIANT" in ru or rohs == "RoHS Compliant":
            rohs_ok = "NON" not in ru

    return EnrichmentResult(
        source="digikey",
        lifecycle_status=lifecycle,
        total_inventory=inv,
        avg_lead_time_days=lead_days,
        distributor_count=1,
        num_alternates=None,
        rohs_compliant=rohs_ok,
        reach_compliant=None,
        raw_data=raw,
    )


class DigiKeyProvider(EnrichmentProvider):
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=45.0)
        self._token: str | None = None
        self._token_expires: float = 0.0

    @property
    def source_name(self) -> str:
        return "digikey"

    async def _ensure_token(self) -> str | None:
        cid = (settings.digikey_client_id or "").strip()
        csec = (settings.digikey_client_secret or "").strip()
        if not cid or not csec:
            return None
        now = time.time()
        if self._token and now < self._token_expires - 60:
            return self._token

        token_url = f"{_dk_base()}/v1/oauth2/token"
        try:
            resp = await self._client.post(
                token_url,
                data={
                    "client_id": cid,
                    "client_secret": csec,
                    "grant_type": "client_credentials",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            log.warning("digikey_token_failed", error=str(e))
            return None

        self._token = data.get("access_token")
        exp = int(data.get("expires_in") or 600)
        self._token_expires = now + exp
        return self._token

    async def enrich(self, mpn: str, manufacturer: str | None = None) -> EnrichmentResult | None:
        token = await self._ensure_token()
        if not token:
            log.debug("digikey_skipped", reason="no_credentials", mpn=mpn)
            return None

        cid = (settings.digikey_client_id or "").strip()
        search_url = f"{_dk_base()}/products/v4/search/keyword"
        body = {"Keywords": mpn.strip(), "RecordCount": 10}
        try:
            resp = await self._client.post(
                search_url,
                json=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-DIGIKEY-Client-Id": cid,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPStatusError as e:
            log.warning(
                "digikey_http_error",
                mpn=mpn,
                status=e.response.status_code,
                body=e.response.text[:500],
            )
            return None
        except httpx.HTTPError as e:
            log.warning("digikey_request_failed", mpn=mpn, error=str(e))
            return None
        except ValueError as e:
            log.warning("digikey_invalid_json", mpn=mpn, error=str(e))
            return None

        if not isinstance(payload, dict):
            return None
        prod = _first_product(payload)
        if not prod:
            log.info("digikey_no_results", mpn=mpn)
            return EnrichmentResult(source="digikey", raw_data=payload)

        return _parse_product(prod, payload)

    async def health_check(self) -> bool:
        t = await self._ensure_token()
        return bool(t)
