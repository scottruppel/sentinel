"""Readiness checks for operations and demo prep."""
from __future__ import annotations

from sqlalchemy import text

from sentinel.config import settings
from sentinel.db.session import async_session_factory
from sentinel.enrichment.digikey import DigiKeyProvider
from sentinel.enrichment.mouser import MouserProvider
from sentinel.enrichment.nexar import NexarProvider


async def readiness() -> dict:
    checks: dict = {}
    status = "ok"

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = {"ok": True}
    except Exception as e:
        checks["database"] = {"ok": False, "error": str(e)}
        status = "degraded"

    nexar = NexarProvider()
    nexar_configured = bool(settings.nexar_client_id and settings.nexar_client_secret)
    if nexar_configured:
        try:
            token_ok = await nexar.health_check()
            checks["nexar"] = {"configured": True, "token_ok": token_ok}
        except Exception as e:
            checks["nexar"] = {"configured": True, "token_ok": False, "error": str(e)}
            status = "degraded"
    else:
        checks["nexar"] = {"configured": False, "token_ok": False}

    checks["siliconexpert"] = {
        "api_key_configured": bool(settings.siliconexpert_api_key),
        "lookup_path_set": bool(settings.siliconexpert_lookup_path.strip()),
    }
    checks["z2data"] = {
        "api_key_configured": bool(settings.z2data_api_key),
        "lookup_path_set": bool(settings.z2data_lookup_path.strip()),
    }

    checks["mouser"] = {"api_key_configured": bool((settings.mouser_api_key or "").strip())}
    dk = DigiKeyProvider()
    dk_creds = bool((settings.digikey_client_id or "").strip() and (settings.digikey_client_secret or "").strip())
    if dk_creds:
        try:
            tok_ok = await dk.health_check()
            checks["digikey"] = {"configured": True, "token_ok": tok_ok}
        except Exception as e:
            checks["digikey"] = {"configured": True, "token_ok": False, "error": str(e)}
    else:
        checks["digikey"] = {"configured": False, "token_ok": False}

    checks["fred"] = {
        "api_key_configured": bool((settings.fred_api_key or "").strip()),
        "default_series": settings.fred_series_list(),
    }

    checks["enrichment_priority"] = list(settings.enrichment_priority_tuple())

    checks["intelligence"] = {
        "llm_enabled": settings.llm_enabled,
        "llm_provider": settings.llm_provider,
        "llm_base_url_configured": bool(settings.llm_base_url),
        "llm_model": settings.llm_model,
        "llm_api_key_configured": bool(settings.llm_api_key),
    }

    return {"status": status, "checks": checks}
