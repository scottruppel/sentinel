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

## Architecture

- **Backend**: Python / FastAPI / SQLAlchemy (async) / PostgreSQL
- **Frontend**: React / TypeScript / Vite / Tailwind CSS
- **Enrichment**: Nexar (primary), SiliconExpert, Z2Data (stubs for PoC)
- **Risk Engine**: Rule-based scoring across 5 dimensions with configurable weight profiles
- **What-If Engine**: 5 scenario types for supply chain disruption simulation
