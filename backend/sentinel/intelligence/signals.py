"""Public market events: ingest (RSS, CSV) and relevance matching to components."""
from __future__ import annotations

import csv
import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.db.models import Component, MarketEvent
from sentinel.enrichment.merge import MergedEnrichment

log = structlog.get_logger()

# Regions and topics for naive keyword overlap with titles/summaries
DEFAULT_KEYWORD_SEEDS = (
    "semiconductor",
    "supply chain",
    "sanctions",
    "tariff",
    "export control",
    "Taiwan",
    "China",
    "memory",
    "foundry",
)


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.split(r"\W+", text) if len(t) > 2}


def _local_tag(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _atom_child_text(entry: ET.Element, name: str) -> str | None:
    for el in entry:
        if _local_tag(el.tag) == name:
            return (el.text or "").strip() or None
    return None


def _atom_child_link_href(entry: ET.Element) -> str | None:
    for el in entry:
        if _local_tag(el.tag) == "link":
            return (el.get("href") or el.text or "").strip() or None
    return None


async def ingest_rss_url(session: AsyncSession, url: str, limit: int = 50) -> dict[str, Any]:
    """Fetch RSS or Atom feed and upsert market_events by source_url."""
    inserted = 0
    skipped = 0
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            content = r.text
        except Exception as e:
            return {"inserted": 0, "skipped": 0, "errors": [str(e)]}

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        return {"inserted": 0, "skipped": 0, "errors": [f"XML parse: {e}"]}

    items: list[tuple[str, str, str | None, str | None]] = []

    if _local_tag(root.tag) == "feed":  # Atom
        for el in root:
            if _local_tag(el.tag) != "entry":
                continue
            t = _atom_child_text(el, "title") or ""
            href = _atom_child_link_href(el) or ""
            s = _atom_child_text(el, "summary") or _atom_child_text(el, "content")
            u = _atom_child_text(el, "updated") or _atom_child_text(el, "published")
            if t and href:
                items.append((t.strip(), href.strip(), s, u))
    else:  # RSS 2.0
        channel = root.find("channel")
        if channel is None:
            return {"inserted": 0, "skipped": 0, "errors": ["No channel in RSS"]}
        for item in channel.findall("item")[:limit]:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            pub_el = item.find("pubDate")
            t = title_el.text if title_el is not None else ""
            href = link_el.text if link_el is not None else ""
            s = desc_el.text if desc_el is not None else None
            u = pub_el.text if pub_el is not None else None
            if t and href:
                items.append((t.strip(), href.strip(), s, u))

    for title, href, summary, pub in items[:limit]:
        existing = await session.execute(select(MarketEvent).where(MarketEvent.source_url == href))
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        region_tags, keywords = _derive_tags_keywords(title, summary or "")
        published_at = _parse_pub_date(pub)
        ev = MarketEvent(
            title=title[:500],
            summary=(summary or "")[:8000],
            source_url=href[:2000],
            published_at=published_at,
            event_type="rss",
            region_tags=region_tags,
            keywords=keywords,
        )
        session.add(ev)
        inserted += 1

    await session.commit()
    log.info("rss_ingest_done", url=url, inserted=inserted, skipped=skipped)
    return {"inserted": inserted, "skipped": skipped, "errors": errors}


def _parse_pub_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    raw = raw.strip()
    try:
        from email.utils import parsedate_to_datetime

        return parsedate_to_datetime(raw)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _derive_tags_keywords(title: str, summary: str) -> tuple[list[str], list[str]]:
    text = f"{title} {summary}"
    regions: list[str] = []
    for r in ("Taiwan", "China", "USA", "Europe", "Japan", "South Korea", "Malaysia", "Vietnam"):
        if r.lower() in text.lower():
            regions.append(r)
    kw = [k for k in DEFAULT_KEYWORD_SEEDS if k.lower() in text.lower()]
    tokens = list(_tokenize(text))[:30]
    return regions, kw + tokens[:15]


async def ingest_csv_bytes(session: AsyncSession, data: bytes) -> dict[str, Any]:
    """CSV columns: title, source_url, summary (optional), published_at (optional), event_type (optional)."""
    inserted = 0
    skipped = 0
    errors: list[str] = []
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")

    rows = list(csv.DictReader(io.StringIO(text)))
    for row in rows:
        keymap = {k.strip().lower(): v for k, v in row.items()}
        title = (keymap.get("title") or "").strip()
        url = (keymap.get("source_url") or keymap.get("url") or "").strip()
        if not title or not url:
            errors.append("skip row: missing title or source_url")
            continue
        existing = await session.execute(select(MarketEvent).where(MarketEvent.source_url == url))
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        summary = (keymap.get("summary") or "").strip() or None
        pub_raw = keymap.get("published_at") or ""
        published_at = _parse_pub_date(pub_raw) if pub_raw else None
        et = (keymap.get("event_type") or "csv").strip() or "csv"
        region_tags, keywords = _derive_tags_keywords(title, summary or "")
        ev = MarketEvent(
            title=title[:500],
            summary=(summary or "")[:8000],
            source_url=url[:2000],
            published_at=published_at,
            event_type=et[:50],
            region_tags=region_tags,
            keywords=keywords,
        )
        session.add(ev)
        inserted += 1

    await session.commit()
    return {"inserted": inserted, "skipped": skipped, "errors": errors}


def match_events_for_component(
    component: Component,
    merged: MergedEnrichment | None,
    events: list[MarketEvent],
    max_events: int = 8,
) -> list[MarketEvent]:
    """Keyword / region overlap between Tier B fields and Tier C events."""
    hay_parts = [
        component.mpn or "",
        component.manufacturer or "",
        component.category or "",
    ]
    if merged and merged.country_of_origin:
        hay_parts.append(merged.country_of_origin)
    hay = " ".join(hay_parts).lower()
    hay_tokens = _tokenize(hay)

    scored: list[tuple[float, MarketEvent]] = []
    for ev in events:
        text = f"{ev.title} {ev.summary or ''}".lower()
        score = 0.0
        if merged and merged.country_of_origin:
            if merged.country_of_origin.lower() in text:
                score += 3.0
        for tag in ev.region_tags or []:
            if tag.lower() in hay or tag.lower() in text:
                score += 1.5
        for kw in ev.keywords or []:
            kl = kw.lower()
            if len(kl) > 2 and (kl in text and (kl in hay or kl in " ".join(hay_tokens))):
                score += 2.0
        mpn_tok = (component.mpn or "").lower()
        if mpn_tok and len(mpn_tok) > 4 and mpn_tok in text:
            score += 2.5
        manu = (component.manufacturer or "").lower()
        if manu and len(manu) > 3 and manu in text:
            score += 1.0
        if score > 0:
            scored.append((score, ev))

    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:max_events]]


async def list_recent_events(session: AsyncSession, limit: int = 200) -> list[MarketEvent]:
    q = select(MarketEvent).order_by(MarketEvent.created_at.desc()).limit(limit)
    r = await session.execute(q)
    return list(r.scalars().all())
