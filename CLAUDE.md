# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All backend commands run from `backend/` with the virtualenv active (`.venv/bin/python` or `source .venv/bin/activate`).

```bash
# One-time setup
cd backend
uv venv && uv pip install -e ".[dev]"

# Start DB (required before backend)
docker-compose up -d

# Run backend (API at http://localhost:8001/docs)
.venv/bin/uvicorn sentinel.main:app --reload --port 8001

# Apply DB migrations
.venv/bin/alembic upgrade head

# Seed demo BOM data
.venv/bin/python -m scripts.seed_demo_bom

# Run all tests
.venv/bin/pytest

# Run a single test file
.venv/bin/pytest tests/test_enrichment.py

# Run a single test by name
.venv/bin/pytest tests/test_risk.py -k "test_lifecycle"

# Verify live API connectivity (skip mouser until key approved)
.venv/bin/python scripts/verify_api_connections.py --only nexar,digikey,fred

# Frontend (http://localhost:5173)
cd frontend && npm install && npm run dev
```

## Environment

`.env` lives at the repo root (`/root/sentinel/.env`). The backend loads repo-root `.env` first, then `backend/.env` if present (later file wins on duplicates). Never commit real keys — `extra="ignore"` in `config.py` means unknown vars are silently dropped rather than raising.

Key optional features gated by `.env`:
- `LLM_ENABLED=true` + `LLM_PROVIDER=anthropic` — enables Claude narrative generation
- `TAILSCALE_ENABLED=true` + `SENTINEL_API_KEY=<secret>` — enforces `X-API-Key` on all `/api/*` routes (except `/api/health` and `/api/ready`)
- `DIGIKEY_USE_SANDBOX=true` — switches DigiKey to sandbox endpoint

## Architecture

### Data flow

```
CSV/XLSX upload → ingest (parse + normalize) → BOM + Component rows
                                                      ↓
                                            enrichment (per-component)
                                         Mouser | DigiKey | Nexar | SE | Z2Data
                                                      ↓
                                           EnrichmentRecord rows (one per source)
                                                      ↓
                                            merge (source priority order)
                                                      ↓
                                          risk scoring (5 dimensions)
                                                      ↓
                                        RiskScoreRecord + BOM overall score
```

### Enrichment pipeline

`EnrichmentProvider` (ABC in `enrichment/base.py`) defines the interface — `enrich(mpn, manufacturer) -> EnrichmentResult | None`. Each provider returns `None` when unconfigured or on failure; the orchestrator silently skips `None` results.

`EnrichmentOrchestrator` (`enrichment/orchestrator.py`) fans out all providers concurrently via `asyncio.gather()` per component, stores each `EnrichmentResult` as a separate `EnrichmentRecord`, then sleeps `ENRICHMENT_RATE_LIMIT_DELAY` between components.

**Important:** providers are module-level singletons in `enrichment/router.py` (`_PROVIDERS` list). DigiKey and Nexar cache OAuth tokens in instance state — do not create new provider instances per request or token caching breaks.

Merging (`enrichment/merge.py`) applies source priority order from `ENRICHMENT_SOURCE_PRIORITY` (default: `mouser,digikey,nexar,siliconexpert,z2data,synthetic`) — first non-null value per field wins.

### Risk scoring

Five independent dimension functions in `risk/scorer.py`, each returning a `DimensionScore(score: float, factors: list[RiskFactor])`:
- `score_lifecycle_risk` — lifecycle status + YTEOL + alternates
- `score_supply_risk` — inventory + lead time + distributor count
- `score_geographic_risk` — country of origin (sanctioned/high-risk/Taiwan/other)
- `score_supplier_risk` — single-source / alternates count
- `score_regulatory_risk` — RoHS + REACH compliance

Composite = weighted sum via `RiskWeightProfile` (`risk/weights.py`). Multiple named profiles exist; default is `"default"`. Composite thresholds: ≥70 critical, 50–69 high, 30–49 medium, <30 low.

### Intelligence layer

`intelligence/signals.py` — ingests public market events from RSS feeds, FRED API (macroeconomic time series), or CSV upload into the `market_events` table.

`intelligence/narrative.py` — builds a per-component intelligence brief by packaging enrichment + risk data (`context_packager.py`), optionally calling an LLM (`llm_client.py`) for a structured narrative. The LLM call goes to Anthropic's Messages API (`/v1/messages`), not OpenAI's `/chat/completions` — both require the `allow_remote_llm: true` flag in the request body when the base URL is not localhost.

`intelligence/policy.py` — governs redaction of BOM/program metadata before LLM submission (Tier B/C packaging).

### Auth

`ApiKeyMiddleware` (`auth.py`) is a no-op when `TAILSCALE_ENABLED=false` (local dev default). When enabled, every `/api/*` request requires `X-API-Key: <SENTINEL_API_KEY>` header.

### Frontend

React + TypeScript + Vite + Tailwind. API base URL defaults to `http://localhost:8001`. Pages and components live under `frontend/src/pages/` and `frontend/src/components/`.

### Database

PostgreSQL via SQLAlchemy async + asyncpg. Schema managed by Alembic (`backend/alembic/`). On startup, `main.py` runs `create_all` to add any tables missing from the migration history (covers `market_events`, `llm_audit_logs` added post-seed).
