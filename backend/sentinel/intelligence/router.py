from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.db.session import get_session
from sentinel.intelligence.narrative import build_narrative
from sentinel.intelligence.schemas import IngestResult, MarketEventPublic, NarrativeRequest, NarrativeResponse
from sentinel.intelligence.signals import (
    ingest_csv_bytes,
    ingest_fred_observations,
    ingest_rss_url,
    list_recent_events,
)

router = APIRouter(tags=["intelligence"])


@router.post("/intelligence/narrative/{component_id}", response_model=NarrativeResponse)
async def post_narrative(
    component_id: UUID,
    body: NarrativeRequest | None = None,
    session: AsyncSession = Depends(get_session),
):
    req = body or NarrativeRequest()
    try:
        return await build_narrative(session, component_id, req)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/intelligence/market-events", response_model=list[MarketEventPublic])
async def get_market_events(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(100, ge=1, le=500),
):
    events = await list_recent_events(session, limit=limit)
    return [
        MarketEventPublic(
            id=str(e.id),
            title=e.title,
            summary=e.summary,
            source_url=e.source_url,
            published_at=e.published_at.isoformat() if e.published_at else None,
            event_type=e.event_type,
            region_tags=list(e.region_tags or []),
            keywords=list(e.keywords or []),
        )
        for e in events
    ]


@router.post("/intelligence/market-events/ingest-rss", response_model=IngestResult)
async def post_ingest_rss(
    url: str = Query(..., description="RSS or Atom feed URL"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    stats = await ingest_rss_url(session, url, limit=limit)
    return IngestResult(
        inserted=stats.get("inserted", 0),
        skipped=stats.get("skipped", 0),
        errors=stats.get("errors", []),
    )


@router.post("/intelligence/market-events/ingest-fred", response_model=IngestResult)
async def post_ingest_fred(
    series_ids: str | None = Query(
        None,
        description="Comma-separated FRED series ids (default: FRED_DEFAULT_SERIES in settings)",
    ),
    limit_per_series: int = Query(1, ge=1, le=24, description="Latest N observations per series"),
    session: AsyncSession = Depends(get_session),
):
    """Ingest macroeconomic observations from FRED into ``market_events`` (``event_type=fred``)."""
    ids = None
    if series_ids and series_ids.strip():
        ids = [s.strip() for s in series_ids.split(",") if s.strip()]
    stats = await ingest_fred_observations(session, series_ids=ids, limit_per_series=limit_per_series)
    return IngestResult(
        inserted=stats.get("inserted", 0),
        skipped=stats.get("skipped", 0),
        errors=stats.get("errors", []),
    )


@router.post("/intelligence/market-events/ingest-csv", response_model=IngestResult)
async def post_ingest_csv(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    data = await file.read()
    stats = await ingest_csv_bytes(session, data)
    return IngestResult(
        inserted=stats.get("inserted", 0),
        skipped=stats.get("skipped", 0),
        errors=stats.get("errors", []),
    )


@router.get("/intelligence/settings")
async def intelligence_settings():
    from sentinel.config import settings

    return {
        "llm_enabled": settings.llm_enabled,
        "llm_provider": settings.llm_provider,
        "llm_base_url": settings.llm_base_url,
        "llm_model": settings.llm_model,
        "policy_version": __import__("sentinel.intelligence.policy", fromlist=["POLICY_VERSION"]).POLICY_VERSION,
    }
