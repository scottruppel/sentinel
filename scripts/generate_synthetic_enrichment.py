"""Generate realistic synthetic enrichment data for offline development."""
from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)
log = structlog.get_logger()

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from sentinel.db.engine import engine
from sentinel.db.models import Component, EnrichmentRecord
from sentinel.db.session import async_session_factory

LIFECYCLE_DISTRIBUTION = {
    "Active": 0.55,
    "Active (single source)": 0.15,
    "NRFND": 0.12,
    "Last Time Buy": 0.08,
    "Obsolete": 0.10,
}

COUNTRY_POOL = [
    "China", "Taiwan", "South Korea", "Japan", "USA",
    "Germany", "Malaysia", "Philippines", "Thailand", "Singapore",
]

CATEGORY_PROFILES: dict[str, dict] = {
    "IC": {
        "countries": ["Taiwan", "China", "South Korea", "USA", "Japan", "Malaysia"],
        "inventory_range": (50, 50000),
        "lead_time_range": (7, 120),
        "distributor_range": (2, 12),
        "alternate_range": (0, 5),
    },
    "Capacitor": {
        "countries": ["Japan", "South Korea", "China", "Taiwan"],
        "inventory_range": (10000, 5000000),
        "lead_time_range": (3, 28),
        "distributor_range": (5, 20),
        "alternate_range": (3, 15),
    },
    "Resistor": {
        "countries": ["China", "Taiwan", "Japan"],
        "inventory_range": (50000, 10000000),
        "lead_time_range": (3, 21),
        "distributor_range": (8, 25),
        "alternate_range": (5, 20),
    },
    "Connector": {
        "countries": ["China", "Japan", "USA", "Taiwan"],
        "inventory_range": (100, 100000),
        "lead_time_range": (7, 56),
        "distributor_range": (3, 10),
        "alternate_range": (1, 8),
    },
    "Inductor": {
        "countries": ["Japan", "China", "Philippines"],
        "inventory_range": (5000, 2000000),
        "lead_time_range": (5, 35),
        "distributor_range": (4, 15),
        "alternate_range": (2, 10),
    },
}

DEFAULT_PROFILE = {
    "countries": ["China", "Taiwan", "Japan", "USA"],
    "inventory_range": (100, 200000),
    "lead_time_range": (7, 60),
    "distributor_range": (2, 10),
    "alternate_range": (0, 5),
}

HAND_TUNED: dict[str, dict] = {
    "ADAR1000BCPZ": {
        "lifecycle_status": "Active (single source)",
        "country_of_origin": "USA",
        "single_source": True,
        "total_inventory": 2500,
        "avg_lead_time_days": 56,
        "distributor_count": 4,
        "num_alternates": 0,
        "yteol": 8.0,
    },
    "ADAR3000BCPZ": {
        "lifecycle_status": "Active (single source)",
        "country_of_origin": "USA",
        "single_source": True,
        "total_inventory": 800,
        "avg_lead_time_days": 70,
        "distributor_count": 3,
        "num_alternates": 0,
        "yteol": 10.0,
    },
    "AD9363BBCZ": {
        "lifecycle_status": "Active",
        "country_of_origin": "USA",
        "single_source": True,
        "total_inventory": 5200,
        "avg_lead_time_days": 42,
        "distributor_count": 6,
        "num_alternates": 1,
        "yteol": 6.0,
    },
    "ADF4159CCPZ": {
        "lifecycle_status": "NRFND",
        "country_of_origin": "USA",
        "single_source": True,
        "total_inventory": 1800,
        "avg_lead_time_days": 35,
        "distributor_count": 5,
        "num_alternates": 2,
        "yteol": 3.0,
    },
    "HMC1119LP4CE": {
        "lifecycle_status": "Active",
        "country_of_origin": "USA",
        "single_source": True,
        "total_inventory": 3200,
        "avg_lead_time_days": 28,
        "distributor_count": 4,
        "num_alternates": 1,
        "yteol": 7.0,
    },
    "HMC637ALP5E": {
        "lifecycle_status": "Last Time Buy",
        "country_of_origin": "USA",
        "single_source": True,
        "total_inventory": 450,
        "avg_lead_time_days": 90,
        "distributor_count": 2,
        "num_alternates": 1,
        "yteol": 1.0,
    },
    "XC7Z010-1CLG225C": {
        "lifecycle_status": "NRFND",
        "country_of_origin": "Taiwan",
        "single_source": True,
        "total_inventory": 3800,
        "avg_lead_time_days": 84,
        "distributor_count": 5,
        "num_alternates": 2,
        "yteol": 2.5,
    },
    "MT41K256M16TW-107:P": {
        "lifecycle_status": "NRFND",
        "country_of_origin": "South Korea",
        "single_source": False,
        "total_inventory": 12000,
        "avg_lead_time_days": 21,
        "distributor_count": 8,
        "num_alternates": 4,
        "yteol": 2.0,
    },
    "LTC6655BHMS8-3.3": {
        "lifecycle_status": "Active",
        "country_of_origin": "USA",
        "single_source": True,
        "total_inventory": 6500,
        "avg_lead_time_days": 28,
        "distributor_count": 6,
        "num_alternates": 2,
        "yteol": 8.0,
    },
}


def _pick_lifecycle() -> str:
    rand = random.random()
    cumulative = 0.0
    for status, prob in LIFECYCLE_DISTRIBUTION.items():
        cumulative += prob
        if rand <= cumulative:
            return status
    return "Active"


def _generate_for_component(mpn_normalized: str, category: str | None) -> dict:
    if mpn_normalized in HAND_TUNED:
        base = HAND_TUNED[mpn_normalized].copy()
        base.setdefault("rohs_compliant", True)
        base.setdefault("reach_compliant", True)
        return base

    profile = CATEGORY_PROFILES.get(category or "", DEFAULT_PROFILE)
    lifecycle = _pick_lifecycle()

    inv_lo, inv_hi = profile["inventory_range"]
    lead_lo, lead_hi = profile["lead_time_range"]
    dist_lo, dist_hi = profile["distributor_range"]
    alt_lo, alt_hi = profile["alternate_range"]

    if lifecycle == "Obsolete":
        total_inventory = random.randint(0, max(50, inv_lo // 10))
        avg_lead_time_days = random.randint(lead_hi, lead_hi * 3)
        num_alternates = random.randint(0, 2)
        yteol = 0.0
    elif lifecycle == "Last Time Buy":
        total_inventory = random.randint(inv_lo // 5, inv_lo)
        avg_lead_time_days = random.randint(lead_hi // 2, lead_hi * 2)
        num_alternates = random.randint(0, 3)
        yteol = round(random.uniform(0.5, 2.0), 1)
    elif lifecycle == "NRFND":
        total_inventory = random.randint(inv_lo, inv_hi // 2)
        avg_lead_time_days = random.randint(lead_lo * 2, lead_hi)
        num_alternates = random.randint(alt_lo, alt_hi)
        yteol = round(random.uniform(1.0, 5.0), 1)
    elif lifecycle == "Active (single source)":
        total_inventory = random.randint(inv_lo, inv_hi // 3)
        avg_lead_time_days = random.randint(lead_lo, lead_hi)
        num_alternates = 0
        yteol = round(random.uniform(5.0, 15.0), 1)
    else:
        total_inventory = random.randint(inv_hi // 4, inv_hi)
        avg_lead_time_days = random.randint(lead_lo, lead_hi // 2)
        num_alternates = random.randint(alt_lo, alt_hi)
        yteol = round(random.uniform(5.0, 15.0), 1)

    single_source = lifecycle == "Active (single source)" or random.random() < 0.15
    country = random.choice(profile["countries"])

    return {
        "lifecycle_status": lifecycle,
        "yteol": yteol,
        "total_inventory": total_inventory,
        "avg_lead_time_days": avg_lead_time_days,
        "distributor_count": random.randint(dist_lo, dist_hi),
        "num_alternates": num_alternates,
        "country_of_origin": country,
        "single_source": single_source,
        "rohs_compliant": random.random() > 0.05,
        "reach_compliant": random.random() > 0.08,
    }


async def generate_synthetic_enrichment(session: AsyncSession, bom_id: UUID):
    result = await session.execute(
        select(Component).where(Component.bom_id == bom_id)
    )
    components = result.scalars().all()
    log.info("generating_synthetic_enrichment", bom_id=str(bom_id), count=len(components))

    random.seed(42)

    for comp in components:
        data = _generate_for_component(comp.mpn_normalized, comp.category)
        record = EnrichmentRecord(
            component_id=comp.id,
            source="synthetic",
            data={"synthetic": True, "mpn": comp.mpn, **data},
            lifecycle_status=data["lifecycle_status"],
            yteol=data.get("yteol"),
            total_inventory=data.get("total_inventory"),
            avg_lead_time_days=data.get("avg_lead_time_days"),
            distributor_count=data.get("distributor_count"),
            num_alternates=data.get("num_alternates"),
            country_of_origin=data.get("country_of_origin"),
            single_source=data.get("single_source"),
            rohs_compliant=data.get("rohs_compliant"),
            reach_compliant=data.get("reach_compliant"),
        )
        session.add(record)

    await session.commit()
    log.info("synthetic_enrichment_complete", bom_id=str(bom_id), count=len(components))


async def main():
    from sentinel.db.models import Bom

    async with async_session_factory() as session:
        result = await session.execute(select(Bom).limit(1))
        bom = result.scalar_one_or_none()
        if not bom:
            log.error("no_bom_found", hint="Run seed_demo_bom.py first")
            return
        await generate_synthetic_enrichment(session, bom.id)


if __name__ == "__main__":
    asyncio.run(main())
