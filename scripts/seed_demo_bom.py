"""Seed the database with the CN0566 demo BOM and synthetic enrichment data."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import structlog
from sqlalchemy import text
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
from sentinel.db.models import Base, Bom, Component
from sentinel.db.session import async_session_factory
from sentinel.ingest.parser import parse_csv


async def seed_cn0566(session: AsyncSession) -> Bom:
    csv_path = ROOT / "scripts" / "data" / "cn0566_bom.csv"
    log.info("loading_seed_bom", path=str(csv_path))

    content = csv_path.read_bytes()
    result = parse_csv(content)
    log.info("parsed_seed_bom", component_count=len(result.components), warnings=len(result.warnings))

    bom = Bom(
        name="CN0566 Phased Array Radar — EVAL Board",
        description="Analog Devices CN0566 ADALM-PHASER 8-element X-band phased array development platform",
        program="ADALM-PHASER Evaluation",
        source_filename="cn0566_bom.csv",
        component_count=len(result.components),
    )
    session.add(bom)
    await session.flush()

    for pc in result.components:
        session.add(Component(
            bom_id=bom.id,
            mpn=pc.mpn,
            mpn_normalized=pc.mpn_normalized,
            manufacturer=pc.manufacturer,
            reference_designator=pc.reference_designator,
            quantity=pc.quantity,
            description=pc.description,
            value=pc.value,
            package=pc.package,
            category=pc.category,
        ))

    await session.commit()
    log.info("seed_bom_created", bom_id=str(bom.id), name=bom.name)
    return bom


async def seed_scenarios(session: AsyncSession, bom: Bom):
    from sentinel.db.models import Scenario
    from sentinel.whatif.engine import run_scenario

    prebuilt = [
        {
            "name": "Taiwan Semiconductor Disruption",
            "description": "Model loss of Taiwan-manufactured semiconductors",
            "scenario_type": "country_disruption",
            "parameters": {"country": "Taiwan", "severity": "total_loss"},
        },
        {
            "name": "ADI Market Exit — Beamformer Product Line",
            "description": "Model Analog Devices exiting the beamformer product line",
            "scenario_type": "supplier_failure",
            "parameters": {"manufacturer": "Analog Devices", "failure_mode": "exit_product_line"},
        },
        {
            "name": "NRFND Accelerated Obsolescence",
            "description": "Model all NRFND parts going obsolete within 12 months",
            "scenario_type": "obsolescence_wave",
            "parameters": {"target_statuses": ["NRFND"], "time_horizon_months": 12},
        },
    ]

    for s_def in prebuilt:
        scenario = Scenario(
            name=s_def["name"],
            description=s_def["description"],
            scenario_type=s_def["scenario_type"],
            parameters=s_def["parameters"],
            affected_bom_ids=[bom.id],
            status="draft",
        )
        session.add(scenario)
        await session.flush()
        results = await run_scenario(session, scenario)
        log.info("scenario_seeded", name=scenario.name, affected=results["summary"]["total_components_affected"])


async def seed_pluto(session: AsyncSession) -> Bom:
    csv_path = ROOT / "scripts" / "data" / "pluto_bom.csv"
    if not csv_path.exists():
        log.warning("pluto_bom_not_found", path=str(csv_path))
        return None

    content = csv_path.read_bytes()
    result = parse_csv(content)

    bom = Bom(
        name="ADALM-PLUTO (PlutoSDR)",
        description="Analog Devices ADALM-PLUTO Software Defined Radio platform",
        program="ADALM-PLUTO Evaluation",
        source_filename="pluto_bom.csv",
        component_count=len(result.components),
    )
    session.add(bom)
    await session.flush()

    for pc in result.components:
        session.add(Component(
            bom_id=bom.id,
            mpn=pc.mpn,
            mpn_normalized=pc.mpn_normalized,
            manufacturer=pc.manufacturer,
            reference_designator=pc.reference_designator,
            quantity=pc.quantity,
            description=pc.description,
            value=pc.value,
            package=pc.package,
            category=pc.category,
        ))

    await session.commit()
    log.info("pluto_bom_created", bom_id=str(bom.id), components=len(result.components))
    return bom


async def main():
    from scripts.generate_synthetic_enrichment import generate_synthetic_enrichment
    from sentinel.risk.scorer import score_bom

    log.info("creating_tables")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        bom = await seed_cn0566(session)
        log.info("running_synthetic_enrichment")
        await generate_synthetic_enrichment(session, bom.id)
        log.info("running_risk_scoring")
        summary = await score_bom(session, bom.id)
        log.info("risk_scoring_complete", overall=summary["overall_score"], critical=summary["critical_count"])

        pluto = await seed_pluto(session)
        if pluto:
            await generate_synthetic_enrichment(session, pluto.id)
            pluto_summary = await score_bom(session, pluto.id)
            log.info("pluto_risk_complete", overall=pluto_summary["overall_score"])

        log.info("seeding_scenarios")
        await seed_scenarios(session, bom)

    log.info("seed_complete", bom_id=str(bom.id))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
