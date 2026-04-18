import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sentinel.ingest.router import router as ingest_router
from sentinel.enrichment.router import router as enrichment_router
from sentinel.risk.router import router as risk_router
from sentinel.whatif.router import router as whatif_router
from sentinel.export.router import router as export_router
from sentinel.intelligence.router import router as intelligence_router
from sentinel.db.engine import engine
from sentinel.db.models import Base
from sentinel.health import readiness

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
)

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create any missing tables (e.g. market_events, llm_audit_logs) for DBs seeded before intelligence shipped.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("sentinel_starting")
    yield
    log.info("sentinel_shutting_down")


app = FastAPI(
    title="SENTINEL",
    description="Supply Chain Exposure & DMSMS Intelligence Tool",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router, prefix="/api")
app.include_router(enrichment_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(whatif_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(intelligence_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/ready")
async def ready():
    return await readiness()
