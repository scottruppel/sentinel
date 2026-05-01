#!/usr/bin/env python3
"""
Probe external APIs using the same .env loading as the Sentinel app.

Run from the ``backend`` directory::

    cd backend
    python scripts/verify_api_connections.py

Optional::

    python scripts/verify_api_connections.py --mpn RC0603FR-0710KL
    python scripts/verify_api_connections.py --only mouser,digikey,fred

Digi-Key OAuth2 requires **both** ``DIGIKEY_CLIENT_ID`` and ``DIGIKEY_CLIENT_SECRET`` (same names as in ``.env.example``).
If only one is set, the probe reports skipped — not a bug.

Env files are loaded in order: repo-root ``.env`` first, then ``backend/.env`` if present (**later file wins** on duplicate keys).

Does not print secrets. Exit code 0 if all *configured* providers pass; 1 if any configured provider fails.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Resolve package root (backend/) when run as a script
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Quiet structlog from enrichment modules (this script prints its own summary lines)
import logging

import structlog  # noqa: E402

# CRITICAL (50): hide info/warning/error from providers for a clean CLI summary
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=False),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL),
)

import httpx  # noqa: E402

from sentinel.config import _resolved_env_files, settings  # noqa: E402
from sentinel.enrichment.digikey import DigiKeyProvider  # noqa: E402
from sentinel.enrichment.mouser import MouserProvider  # noqa: E402
from sentinel.enrichment.nexar import NexarProvider  # noqa: E402
from sentinel.enrichment.siliconexpert import SiliconExpertProvider  # noqa: E402
from sentinel.enrichment.z2data import Z2DataProvider  # noqa: E402


def _line(name: str, configured: bool, ok: bool | None, detail: str) -> None:
    if not configured:
        print(f"  {name}: skipped (not configured in .env)")
        return
    status = "OK" if ok else "FAIL"
    print(f"  {name}: {status} - {detail}")


async def _test_nexar(mpn: str) -> tuple[bool, str]:
    p = NexarProvider()
    try:
        r = await p.enrich(mpn)
    except Exception as e:
        return False, str(e)
    if r is None:
        return False, "no response (check credentials or network)"
    inv = r.total_inventory
    life = r.lifecycle_status or "—"
    return True, f"lifecycle={life}, total_inventory={inv}"


async def _test_mouser(mpn: str) -> tuple[bool, str]:
    p = MouserProvider()
    try:
        r = await p.enrich(mpn)
    except Exception as e:
        return False, str(e)
    if r is None:
        return False, "no response"
    inv = r.total_inventory
    life = r.lifecycle_status or "—"
    return True, f"lifecycle={life}, total_inventory={inv}"


async def _test_digikey(mpn: str) -> tuple[bool, str]:
    p = DigiKeyProvider()
    try:
        r = await p.enrich(mpn)
    except Exception as e:
        return False, str(e)
    if r is None:
        return False, "no response (token or search failed)"
    inv = r.total_inventory
    life = r.lifecycle_status or "—"
    return True, f"lifecycle={life}, total_inventory={inv}"


async def _test_siliconexpert(mpn: str) -> tuple[bool, str]:
    p = SiliconExpertProvider()
    try:
        r = await p.enrich(mpn)
    except Exception as e:
        return False, str(e)
    if r is None:
        return False, "no response (check lookup path + key)"
    return True, f"lifecycle={r.lifecycle_status!r}, inventory={r.total_inventory}"


async def _test_z2data(mpn: str) -> tuple[bool, str]:
    p = Z2DataProvider()
    try:
        r = await p.enrich(mpn)
    except Exception as e:
        return False, str(e)
    if r is None:
        return False, "no response (check lookup path + key)"
    return True, f"country={r.country_of_origin!r}, lifecycle={r.lifecycle_status!r}"


async def _test_fred() -> tuple[bool, str]:
    key = (settings.fred_api_key or "").strip()
    if not key:
        return False, "missing key"
    series = settings.fred_series_list()
    sid = series[0] if series else "INDPRO"
    url = "https://api.stlouisfed.org/fred/series/observations"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                url,
                params={
                    "series_id": sid,
                    "api_key": key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 1,
                },
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return False, str(e)
    obs = data.get("observations") or []
    if not obs:
        return False, "empty observations"
    o0 = obs[0]
    return True, f"series={sid}, latest date={o0.get('date')}, value={o0.get('value')}"


async def run_all(mpn: str, only: set[str] | None) -> int:
    def want(name: str) -> bool:
        return only is None or name in only

    failures = 0

    ef = _resolved_env_files()
    if ef:
        print("Sentinel API probe — env files:", " -> ".join(ef), "(later overrides earlier)\n")
    else:
        print("Sentinel API probe (no .env files found next to the app — using process env only)\n")

    # Nexar (OAuth: client id + secret — not a single API key)
    if want("nexar"):
        has_nid = bool((settings.nexar_client_id or "").strip())
        has_nsec = bool((settings.nexar_client_secret or "").strip())
        cfg = has_nid and has_nsec
        if cfg:
            ok, detail = await _test_nexar(mpn)
            _line("nexar", True, ok, detail)
            if not ok:
                failures += 1
        else:
            missing = []
            if not has_nid:
                missing.append("NEXAR_CLIENT_ID")
            if not has_nsec:
                missing.append("NEXAR_CLIENT_SECRET")
            print(
                f"  nexar: skipped (needs both id and secret; missing or empty: {', '.join(missing)})"
            )

    if want("mouser"):
        has_mk = bool((settings.mouser_api_key or "").strip())
        if has_mk:
            ok, detail = await _test_mouser(mpn)
            _line("mouser", True, ok, detail)
            if not ok:
                failures += 1
        else:
            print(
                "  mouser: skipped (set MOUSER_API_KEY or MOUSER_KEY in .env — not MOUSER_API_SECRET)"
            )

    if want("digikey"):
        has_id = bool((settings.digikey_client_id or "").strip())
        has_sec = bool((settings.digikey_client_secret or "").strip())
        cfg = has_id and has_sec
        if cfg:
            ok, detail = await _test_digikey(mpn)
            _line("digikey", True, ok, detail)
            if not ok:
                failures += 1
        else:
            missing = []
            if not has_id:
                missing.append("DIGIKEY_CLIENT_ID")
            if not has_sec:
                missing.append("DIGIKEY_CLIENT_SECRET")
            print(
                f"  digikey: skipped (OAuth needs both id and secret; missing or empty: {', '.join(missing)})"
            )

    if want("siliconexpert"):
        cfg = bool(settings.siliconexpert_api_key and settings.siliconexpert_lookup_path.strip())
        if cfg:
            ok, detail = await _test_siliconexpert(mpn)
            _line("siliconexpert", True, ok, detail)
            if not ok:
                failures += 1
        else:
            _line("siliconexpert", False, None, "")

    if want("z2data"):
        cfg = bool(settings.z2data_api_key and settings.z2data_lookup_path.strip())
        if cfg:
            ok, detail = await _test_z2data(mpn)
            _line("z2data", True, ok, detail)
            if not ok:
                failures += 1
        else:
            _line("z2data", False, None, "")

    if want("fred"):
        cfg = bool((settings.fred_api_key or "").strip())
        if cfg:
            ok, detail = await _test_fred()
            _line("fred", True, ok, detail)
            if not ok:
                failures += 1
        else:
            _line("fred", False, None, "")

    print()
    if failures:
        print(f"Done: {failures} configured provider(s) failed.")
        return 1
    print("Done: all configured providers responded successfully.")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify .env API connectivity for Sentinel.")
    ap.add_argument(
        "--mpn",
        default="RC0603FR-0710KL",
        help="Manufacturer part number to search (default: common Yageo resistor)",
    )
    ap.add_argument(
        "--only",
        type=str,
        default="",
        help="Comma-separated subset: nexar,mouser,digikey,siliconexpert,z2data,fred",
    )
    args = ap.parse_args()
    only = None
    if args.only.strip():
        only = {x.strip().lower() for x in args.only.split(",") if x.strip()}

    code = asyncio.run(run_all(args.mpn, only))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
