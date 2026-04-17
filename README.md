# SENTINEL

**Supply Chain Exposure & DMSMS Intelligence Tool**

SENTINEL is a local-first BOM management and DMSMS risk intelligence tool. It ingests hardware Bills of Materials, enriches each component with lifecycle, supply chain, and sub-tier supplier data, scores risk across multiple dimensions, and provides interactive "what-if" analysis for supply chain disruption scenario planning.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for PostgreSQL)

### 1. Start the database

```bash
docker-compose up -d
```

### 2. Backend setup

```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn sentinel.main:app --reload
```

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

### 4. Seed demo data

```bash
cd backend
python -m scripts.seed_demo_bom
```

The dashboard will be available at `http://localhost:5173` and the API at `http://localhost:8001/docs`.

After seeding, run the app once so SQLAlchemy can create new tables (`market_events`, `llm_audit_logs`) if your process uses `create_all`, or apply your usual migration workflow.

## Architecture

- **Backend**: Python / FastAPI / SQLAlchemy (async) / PostgreSQL
- **Frontend**: React / TypeScript / Vite / Tailwind CSS
- **Enrichment**: Nexar (primary), SiliconExpert, Z2Data (stubs for PoC)
- **Risk Engine**: Rule-based scoring across 5 dimensions with configurable weight profiles
- **What-If Engine**: 5 scenario types for supply chain disruption simulation
- **Intelligence (optional)**: Tier B/C packaging with default redaction of BOM/program metadata; public RSS/CSV market events stored locally; optional OpenAI-compatible LLM (e.g. Ollama) for structured narrative + citations. See `backend/sentinel/intelligence/` and `GET /api/intelligence/settings`.

### Optional: local LLM (Ollama)

Set in `backend/.env`:

```env
LLM_ENABLED=true
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_MODEL=llama3.2
```

Start Ollama and pull a model. Use **Intelligence analysis** on an expanded BOM row in the UI, or `POST /api/intelligence/narrative/{component_id}` with JSON body `{"use_llm": true, "allow_remote_llm": false}`.

### Optional: market headlines

Ingest public feeds only (no BOM upload):

```bash
curl -X POST "http://localhost:8001/api/intelligence/market-events/ingest-rss?url=https://example.com/feed.xml"
```
