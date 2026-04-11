"""Readiness checks for operations and demo prep."""
from __future__ import annotations

from sqlalchemy import text

from sentinel.config import settings
from sentinel.db.session import async_session_factory
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

    checks["enrichment_priority"] = list(settings.enrichment_priority_tuple())

    return {"status": status, "checks": checks}
