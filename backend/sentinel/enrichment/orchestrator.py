from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.config import settings
from sentinel.db.models import Component, EnrichmentRecord
from sentinel.enrichment.base import EnrichmentProvider, EnrichmentResult

log = structlog.get_logger()


class EnrichmentOrchestrator:
    """Coordinates enrichment across all configured providers."""

    def __init__(self, providers: list[EnrichmentProvider]):
        self.providers = providers
        self.delay_between_parts = settings.enrichment_rate_limit_delay
        self.cache_days = settings.enrichment_cache_days

    async def enrich_bom(
        self, session: AsyncSession, bom_id: UUID, force_refresh: bool = False
    ) -> dict:
        result = await session.execute(
            select(Component).where(Component.bom_id == bom_id)
        )
        components = result.scalars().all()

        stats = {"total": len(components), "enriched": 0, "cached": 0, "failed": 0}
        log.info("enrichment_starting", bom_id=str(bom_id), component_count=len(components))

        for component in components:
            if not force_refresh and await self._has_recent_enrichment(session, component.id):
                stats["cached"] += 1
                continue

            results = await asyncio.gather(
                *[p.enrich(component.mpn, component.manufacturer) for p in self.providers],
                return_exceptions=True,
            )

            for res in results:
                if isinstance(res, EnrichmentResult):
                    await self._store_enrichment(session, component.id, res)
                    stats["enriched"] += 1
                elif isinstance(res, Exception):
                    log.error("enrichment_provider_error", mpn=component.mpn, error=str(res))
                    stats["failed"] += 1

            if self.delay_between_parts > 0:
                await asyncio.sleep(self.delay_between_parts)

        await session.commit()
        log.info("enrichment_complete", bom_id=str(bom_id), **stats)
        return stats

    async def _has_recent_enrichment(self, session: AsyncSession, component_id: UUID) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.cache_days)
        result = await session.execute(
            select(EnrichmentRecord)
            .where(
                EnrichmentRecord.component_id == component_id,
                EnrichmentRecord.fetched_at >= cutoff,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _store_enrichment(
        self, session: AsyncSession, component_id: UUID, result: EnrichmentResult
    ):
        record = EnrichmentRecord(
            component_id=component_id,
            source=result.source,
            data=result.raw_data,
            lifecycle_status=result.lifecycle_status,
            yteol=result.yteol,
            total_inventory=result.total_inventory,
            avg_lead_time_days=result.avg_lead_time_days,
            distributor_count=result.distributor_count,
            num_alternates=result.num_alternates,
            country_of_origin=result.country_of_origin,
            single_source=result.single_source,
            rohs_compliant=result.rohs_compliant,
            reach_compliant=result.reach_compliant,
        )
        session.add(record)
