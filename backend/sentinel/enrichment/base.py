from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EnrichmentResult:
    source: str
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
    raw_data: dict = field(default_factory=dict)


class EnrichmentProvider(ABC):
    @abstractmethod
    async def enrich(self, mpn: str, manufacturer: str | None = None) -> EnrichmentResult | None:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        ...
