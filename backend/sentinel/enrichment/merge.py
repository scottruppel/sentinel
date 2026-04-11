"""Field-level merge of enrichment records by configurable source priority."""
from __future__ import annotations

from dataclasses import dataclass, field

from sentinel.config import settings
from sentinel.db.models import EnrichmentRecord


def _has_value(val) -> bool:
    if val is None:
        return False
    if isinstance(val, bool):
        return True
    if isinstance(val, str):
        return bool(val.strip())
    if isinstance(val, (int, float)):
        return True
    return True


def _source_rank(source: str, priority: tuple[str, ...]) -> int:
    s = (source or "").lower()
    try:
        return priority.index(s)
    except ValueError:
        return len(priority)


@dataclass
class MergedEnrichment:
    """Effective enrichment for scoring and UI after merging providers."""

    lifecycle_status: str | None = None
    yteol: float | None = None
    total_inventory: int | None = None
    avg_lead_time_days: int | None = None
    distributor_count: int | None = None
    num_alternates: int | None = None
    country_of_origin: str | None = None
    single_source: bool | None = None
    rohs_compliant: bool | None = None
    reach_compliant: bool | None = None
    field_sources: dict[str, str] = field(default_factory=dict)


_FIELD_NAMES = (
    "lifecycle_status",
    "yteol",
    "total_inventory",
    "avg_lead_time_days",
    "distributor_count",
    "num_alternates",
    "country_of_origin",
    "single_source",
    "rohs_compliant",
    "reach_compliant",
)


def merge_enrichment_records(
    records: list[EnrichmentRecord],
    priority: tuple[str, ...] | None = None,
) -> MergedEnrichment | None:
    """
    Merge multiple EnrichmentRecord rows into one effective view.
    Records are ordered by source priority (first in list wins per field).
    For each field, the first provider in that order that supplies a value is used.
    """
    if not records:
        return None

    prio = priority if priority is not None else settings.enrichment_priority_tuple()
    sorted_recs = sorted(records, key=lambda r: _source_rank(r.source, prio))

    out = MergedEnrichment()
    for fname in _FIELD_NAMES:
        for rec in sorted_recs:
            val = getattr(rec, fname)
            if not _has_value(val):
                continue
            setattr(out, fname, val)
            out.field_sources[fname] = rec.source
            break

    return out


def merge_for_component(records: list[EnrichmentRecord]) -> MergedEnrichment | None:
    """Convenience: merge records attached to one component."""
    return merge_enrichment_records(records)
