# Product Requirements Document: SENTINEL
## Supply Chain Exposure & DMSMS Intelligence Tool — Proof of Concept

**Version**: 0.1.0-PoC
**Date**: 2026-03-22

---

## 1. Overview

SENTINEL is a local-first BOM management and DMSMS risk intelligence tool. It ingests hardware Bills of Materials, enriches each component with lifecycle, supply chain, and sub-tier supplier data from commercial APIs, scores risk across multiple dimensions, and provides an interactive "what-if" analysis capability for supply chain disruption scenario planning.

This PRD defines the PoC scope: a Python backend with a browser-based dashboard, running entirely on a single laptop, designed from day one for multi-BOM scalability.

---

## 2. Architecture

### 2.1 System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        SENTINEL PoC                             │
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │  BOM     │───▶│  Enrichment  │───▶│  PostgreSQL           │  │
│  │  Ingest  │    │  Pipeline    │    │  ┌─────────────────┐  │  │
│  │  Module  │    │              │    │  │ boms             │  │  │
│  └──────────┘    │  ┌────────┐  │    │  │ components       │  │  │
│                  │  │ Nexar  │  │    │  │ enrichment_cache │  │  │
│  ┌──────────┐    │  │ SilExp │  │    │  │ risk_scores      │  │  │
│  │  Risk    │◀──▶│  │ Z2Data │  │    │  │ snapshots        │  │  │
│  │  Engine  │    │  └────────┘  │    │  │ scenarios        │  │  │
│  └──────────┘    └──────────────┘    │  └─────────────────┘  │  │
│       │                              └───────────────────────┘  │
│       ▼                                         ▲               │
│  ┌──────────┐                                   │               │
│  │ What-If  │───────────────────────────────────┘               │
│  │ Engine   │                                                   │
│  └──────────┘                                                   │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              FastAPI Backend (REST)                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              React Dashboard (Vite + Tailwind)            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Directory Structure

```
sentinel/
├── README.md
├── docker-compose.yml              # PostgreSQL + app services
├── .env.example                    # API keys template
├── backend/
│   ├── pyproject.toml              # Python project config (use uv or pip)
│   ├── alembic/                    # Database migrations
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── sentinel/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry
│   │   ├── config.py               # Settings from env vars
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py           # SQLAlchemy async engine
│   │   │   ├── models.py           # ORM models
│   │   │   └── session.py          # Session factory
│   │   ├── ingest/
│   │   │   ├── __init__.py
│   │   │   ├── parser.py           # BOM file parsers (Excel, CSV)
│   │   │   ├── normalizer.py       # MPN normalization logic
│   │   │   └── router.py           # /api/boms upload endpoints
│   │   ├── enrichment/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Abstract enrichment provider
│   │   │   ├── nexar.py            # Nexar/Octopart GraphQL client
│   │   │   ├── siliconexpert.py    # SiliconExpert REST client
│   │   │   ├── z2data.py           # Z2Data client (stub for PoC)
│   │   │   ├── orchestrator.py     # Parallel enrichment coordinator
│   │   │   └── router.py           # /api/enrichment endpoints
│   │   ├── risk/
│   │   │   ├── __init__.py
│   │   │   ├── scorer.py           # Rule-based risk scoring engine
│   │   │   ├── weights.py          # Configurable risk weight profiles
│   │   │   └── router.py           # /api/risk endpoints
│   │   ├── whatif/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py           # Scenario simulation engine
│   │   │   ├── scenarios.py        # Pre-built scenario templates
│   │   │   └── router.py           # /api/scenarios endpoints
│   │   └── export/
│   │       ├── __init__.py
│   │       └── report.py           # Markdown/PDF report generation
│   └── tests/
│       ├── conftest.py
│       ├── test_ingest.py
│       ├── test_enrichment.py
│       ├── test_risk.py
│       └── test_whatif.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts            # Typed API client (fetch wrapper)
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Sidebar.tsx
│       │   │   └── TopBar.tsx
│       │   ├── bom/
│       │   │   ├── BomUpload.tsx     # Drag-and-drop BOM upload
│       │   │   ├── BomList.tsx       # Multi-BOM browser
│       │   │   └── BomDetail.tsx     # Component table for a BOM
│       │   ├── risk/
│       │   │   ├── RiskDashboard.tsx  # Aggregate risk overview
│       │   │   ├── RiskHeatmap.tsx    # Risk matrix visualization
│       │   │   └── ComponentCard.tsx  # Per-component risk detail
│       │   ├── whatif/
│       │   │   ├── ScenarioBuilder.tsx  # What-if scenario UI
│       │   │   ├── ImpactView.tsx       # Before/after comparison
│       │   │   └── ScenarioList.tsx     # Saved scenarios
│       │   └── common/
│       │       ├── DataTable.tsx
│       │       ├── Badge.tsx
│       │       └── Charts.tsx        # Recharts wrapper components
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── BomManager.tsx
│       │   ├── RiskAnalysis.tsx
│       │   └── WhatIf.tsx
│       └── types/
│           └── index.ts              # Shared TypeScript types
└── scripts/
    ├── seed_demo_bom.py              # Load CN0566 BOM for demo
    └── generate_synthetic_enrichment.py  # Generate mock API data for offline dev
```

---

## 3. Data Model

### 3.1 Core Tables

```sql
-- A BOM represents a single uploaded bill of materials
CREATE TABLE boms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,               -- e.g., "CN0566 Phased Array"
    description TEXT,
    program VARCHAR(255),                      -- e.g., weapon system or project name
    version VARCHAR(50),                       -- BOM revision
    source_filename VARCHAR(255),
    uploaded_at TIMESTAMPTZ DEFAULT now(),
    component_count INTEGER DEFAULT 0,
    risk_score_overall FLOAT,                  -- cached aggregate risk
    metadata JSONB DEFAULT '{}'                -- extensible: org, POC, notes
);

-- A component is a unique line item within a BOM
CREATE TABLE components (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bom_id UUID NOT NULL REFERENCES boms(id) ON DELETE CASCADE,
    reference_designator VARCHAR(100),          -- e.g., "U1, U2" or "R1-R47"
    mpn VARCHAR(255) NOT NULL,                 -- manufacturer part number
    mpn_normalized VARCHAR(255) NOT NULL,      -- cleaned/uppercased for matching
    manufacturer VARCHAR(255),
    description TEXT,
    quantity INTEGER DEFAULT 1,
    category VARCHAR(100),                     -- e.g., "IC", "Capacitor", "Connector"
    package VARCHAR(100),                      -- e.g., "LFCSP-40", "0402"
    value VARCHAR(100),                        -- e.g., "100nF", "10kΩ"
    is_critical BOOLEAN DEFAULT false,         -- user-flagged criticality
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(bom_id, mpn_normalized, reference_designator)
);
CREATE INDEX idx_components_mpn ON components(mpn_normalized);
CREATE INDEX idx_components_bom ON components(bom_id);

-- Enrichment data from external APIs, versioned by snapshot
CREATE TABLE enrichment_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component_id UUID NOT NULL REFERENCES components(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,               -- 'nexar', 'siliconexpert', 'z2data'
    fetched_at TIMESTAMPTZ DEFAULT now(),
    data JSONB NOT NULL,                       -- full API response payload
    lifecycle_status VARCHAR(50),              -- extracted: Active, NRFND, LTB, Obsolete
    yteol FLOAT,                               -- years to end of life (SiliconExpert)
    total_inventory INTEGER,                   -- sum across distributors
    avg_lead_time_days INTEGER,
    distributor_count INTEGER,
    num_alternates INTEGER,                    -- count of FFF cross-refs
    country_of_origin VARCHAR(100),
    single_source BOOLEAN,
    rohs_compliant BOOLEAN,
    reach_compliant BOOLEAN,
    metadata JSONB DEFAULT '{}'
);
CREATE INDEX idx_enrichment_component ON enrichment_records(component_id);
CREATE INDEX idx_enrichment_source ON enrichment_records(source, fetched_at);

-- Computed risk scores per component, per scoring run
CREATE TABLE risk_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component_id UUID NOT NULL REFERENCES components(id) ON DELETE CASCADE,
    scored_at TIMESTAMPTZ DEFAULT now(),
    profile VARCHAR(50) DEFAULT 'default',     -- scoring profile name
    -- Individual dimension scores (0-100)
    lifecycle_risk FLOAT NOT NULL,
    supply_risk FLOAT NOT NULL,
    geographic_risk FLOAT NOT NULL,
    supplier_risk FLOAT NOT NULL,
    regulatory_risk FLOAT NOT NULL,
    -- Weighted composite
    composite_score FLOAT NOT NULL,
    -- What drove the score
    risk_factors JSONB DEFAULT '[]',           -- array of {factor, detail, contribution}
    recommendation TEXT                         -- generated action recommendation
);
CREATE INDEX idx_risk_component ON risk_scores(component_id, scored_at DESC);

-- Point-in-time snapshots for trend tracking
CREATE TABLE snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bom_id UUID NOT NULL REFERENCES boms(id) ON DELETE CASCADE,
    taken_at TIMESTAMPTZ DEFAULT now(),
    summary JSONB NOT NULL                     -- aggregate stats at snapshot time
);

-- What-if scenarios
CREATE TABLE scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    scenario_type VARCHAR(50) NOT NULL,        -- see Section 6 for types
    parameters JSONB NOT NULL,                 -- scenario-specific config
    affected_bom_ids UUID[],                   -- which BOMs to evaluate against
    results JSONB,                             -- computed impact results
    status VARCHAR(20) DEFAULT 'draft'         -- draft, running, complete
);

-- Cross-BOM component view (which MPNs appear in multiple BOMs)
CREATE VIEW cross_bom_exposure AS
SELECT
    mpn_normalized,
    manufacturer,
    COUNT(DISTINCT bom_id) AS bom_count,
    ARRAY_AGG(DISTINCT bom_id) AS bom_ids,
    SUM(quantity) AS total_quantity
FROM components
GROUP BY mpn_normalized, manufacturer
HAVING COUNT(DISTINCT bom_id) > 1;
```

### 3.2 MPN Normalization Rules

Implement in `normalizer.py`. These rules ensure the same physical part matches across different BOM formats:

```python
def normalize_mpn(raw_mpn: str) -> str:
    """Normalize manufacturer part number for consistent matching."""
    mpn = raw_mpn.strip().upper()
    # Remove common suffixes that don't affect the base part
    # e.g., packaging codes: -ND (DigiKey), -1-ND, #PBF (lead-free)
    mpn = re.sub(r'[-/]\d*ND$', '', mpn)          # DigiKey suffixes
    mpn = re.sub(r'#PBF$', '', mpn)                # Lead-free suffix
    mpn = re.sub(r'[-/]?(REEL|TAPE|CUT|BULK)$', '', mpn)  # Packaging
    # Collapse multiple spaces/hyphens
    mpn = re.sub(r'[\s]+', '', mpn)
    return mpn
```

---

## 4. BOM Ingestion Module

### 4.1 Supported Formats

The parser must handle:

1. **Excel (.xlsx)** — Most common. Columns vary wildly between vendors/orgs. The parser should auto-detect columns by header name matching.
2. **CSV (.csv)** — Same column detection logic.

### 4.2 Column Auto-Detection

Map incoming headers to internal fields using fuzzy matching:

```python
COLUMN_MAPPINGS = {
    "mpn": ["mpn", "manufacturer part number", "mfr part", "mfg part", 
             "part number", "mfr pn", "mfg pn", "component part number"],
    "manufacturer": ["manufacturer", "mfr", "mfg", "vendor", "mfr name",
                      "manufacturer name"],
    "reference_designator": ["reference", "ref des", "refdes", "designator",
                              "ref designator", "references"],
    "quantity": ["qty", "quantity", "count", "amount"],
    "description": ["description", "desc", "part description", "component description"],
    "value": ["value", "val", "nominal"],
    "package": ["package", "footprint", "case", "case/package", "pkg"],
    "category": ["category", "type", "part type", "component type"],
}
```

### 4.3 Upload Flow

```
POST /api/boms/upload
Content-Type: multipart/form-data

Request:
  - file: BOM file (xlsx or csv)
  - name: string (BOM display name)
  - program: string (optional, associated program/weapon system)
  - description: string (optional)

Response: {
  "bom_id": "uuid",
  "name": "CN0566 Phased Array",
  "component_count": 87,
  "parse_warnings": [
    {"row": 14, "warning": "Could not identify MPN column — used 'Part Number'"},
    {"row": 45, "warning": "Duplicate MPN: ADP7118ACPZN-3.3-R7 (merged quantities)"}
  ],
  "status": "ingested"
}
```

### 4.4 Multi-BOM Design

Every component belongs to exactly one BOM via `bom_id`. The `cross_bom_exposure` view automatically surfaces MPNs shared across multiple BOMs. The UI must support:

- Uploading multiple BOMs independently
- Viewing a single BOM's components
- Viewing cross-BOM exposure (which parts appear in >1 BOM)
- Filtering and comparing risk across BOMs

---

## 5. Enrichment Pipeline

### 5.1 Provider Interface

All enrichment providers implement a common base:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class EnrichmentResult:
    source: str
    lifecycle_status: str | None
    yteol: float | None
    total_inventory: int | None
    avg_lead_time_days: int | None
    distributor_count: int | None
    num_alternates: int | None
    country_of_origin: str | None
    single_source: bool | None
    rohs_compliant: bool | None
    reach_compliant: bool | None
    raw_data: dict  # full API response for storage

class EnrichmentProvider(ABC):
    @abstractmethod
    async def enrich(self, mpn: str, manufacturer: str | None = None) -> EnrichmentResult:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
```

### 5.2 Nexar Implementation (Primary for PoC)

```python
# Key GraphQL query template
NEXAR_MPN_QUERY = """
query SearchMPN($mpn: String!) {
  supSearchMpn(q: $mpn, limit: 3) {
    results {
      part {
        mpn
        manufacturer { name }
        manufacturerUrl
        bestDatasheet { url }
        totalAvail
        medianPrice1000 { price currency }
        specs { attribute { name shortname } displayValue }
        sellers {
          company { name isDistributorApi isAuthorized }
          offers {
            inventoryLevel
            moq
            prices { price quantity currency }
            factoryLeadDays
          }
        }
        descriptions { text }
        category { name parentId }
      }
    }
  }
}
"""
```

### 5.3 Enrichment Orchestrator

```python
class EnrichmentOrchestrator:
    """Coordinates enrichment across all configured providers."""
    
    def __init__(self, providers: list[EnrichmentProvider]):
        self.providers = providers
    
    async def enrich_bom(self, bom_id: UUID, force_refresh: bool = False):
        """Enrich all components in a BOM. Respects cache unless force_refresh."""
        components = await get_components_by_bom(bom_id)
        
        for component in components:
            # Check cache: skip if enriched within last 7 days
            if not force_refresh and await has_recent_enrichment(component.id, days=7):
                continue
            
            # Fan out to all providers concurrently
            results = await asyncio.gather(
                *[p.enrich(component.mpn, component.manufacturer) 
                  for p in self.providers],
                return_exceptions=True
            )
            
            for result in results:
                if isinstance(result, EnrichmentResult):
                    await store_enrichment(component.id, result)
            
            # Rate limiting: configurable delay between components
            await asyncio.sleep(self.delay_between_parts)
```

### 5.4 Synthetic/Mock Data for Offline Development

For developing without live API access, `scripts/generate_synthetic_enrichment.py` should create realistic mock enrichment data:

```python
# Distribution of lifecycle statuses (realistic for a ~5-year-old design)
LIFECYCLE_DISTRIBUTION = {
    "Active": 0.55,
    "Active (single source)": 0.15,
    "NRFND": 0.12,        # Not Recommended for New Designs
    "Last Time Buy": 0.08,
    "Obsolete": 0.10,
}

# Generate plausible inventory and lead time data
# Active parts: high inventory, short lead times
# NRFND/LTB: declining inventory, increasing lead times
# Obsolete: near-zero inventory or broker-only
```

This is critical — Cursor can build the entire UI and risk engine against synthetic data before any API keys are acquired.

---

## 6. Risk Scoring Engine

### 6.1 Risk Dimensions

Each component is scored 0-100 on five dimensions:

#### Lifecycle Risk
| Condition | Score |
|-----------|-------|
| Obsolete, no alternates identified | 100 |
| Obsolete, alternates available | 80 |
| Last Time Buy window open | 70 |
| Last Time Buy expired | 90 |
| NRFND, YTEOL < 2 years | 60 |
| NRFND, YTEOL 2-5 years | 40 |
| Active, single manufacturer | 25 |
| Active, multi-source | 5 |

#### Supply Risk
| Condition | Score |
|-----------|-------|
| Zero authorized distributor inventory | 100 |
| Total inventory < 6 months demand | 75 |
| Lead time > 52 weeks | 80 |
| Lead time 26-52 weeks | 50 |
| Lead time increasing (>25% vs. baseline) | +20 bonus |
| Inventory declining (>25% vs. baseline) | +20 bonus |
| Healthy inventory, short lead time | 5 |

#### Geographic Risk
| Condition | Score |
|-----------|-------|
| 100% manufacturing in single high-risk country | 90 |
| >50% single-country concentration (any) | 60 |
| Manufacturing in sanctioned/embargoed region | 100 |
| Multi-region manufacturing | 10 |
| Unknown/unmapped | 50 |

#### Supplier Risk
| Condition | Score |
|-----------|-------|
| Sole source (one manufacturer globally) | 85 |
| Single source (one qualified in the program) | 65 |
| Manufacturer financial distress signals | 75 |
| Dual source, both stable | 15 |
| Multi-source (3+) | 5 |

#### Regulatory Risk
| Condition | Score |
|-----------|-------|
| Non-RoHS compliant (if required) | 60 |
| REACH SVHC listed substance | 50 |
| Conflict mineral exposure (unverified) | 40 |
| ITAR controlled | 30 |
| Fully compliant, all documentation available | 5 |

### 6.2 Composite Scoring

```python
@dataclass
class RiskWeightProfile:
    """Configurable weight profiles for different use cases."""
    name: str
    lifecycle: float
    supply: float
    geographic: float
    supplier: float
    regulatory: float

DEFAULT_PROFILE = RiskWeightProfile(
    name="default",
    lifecycle=0.30,
    supply=0.25,
    geographic=0.20,
    supplier=0.15,
    regulatory=0.10,
)

# Alternative profile emphasizing supply chain resilience
SUPPLY_CHAIN_PROFILE = RiskWeightProfile(
    name="supply_chain_focus",
    lifecycle=0.15,
    supply=0.30,
    geographic=0.30,
    supplier=0.20,
    regulatory=0.05,
)
```

The composite score is a weighted sum, normalized to 0-100. Each scoring run stores the individual dimension scores AND a `risk_factors` JSON array explaining what drove each score — this is essential for the UI to show *why* something is high risk.

### 6.3 BOM-Level Aggregate Risk

```python
def compute_bom_risk(component_scores: list[RiskScore]) -> dict:
    """Roll up component risk to BOM-level metrics."""
    return {
        "overall_score": weighted_mean([s.composite_score for s in component_scores]),
        "max_component_risk": max(s.composite_score for s in component_scores),
        "critical_count": sum(1 for s in component_scores if s.composite_score >= 70),
        "high_count": sum(1 for s in component_scores if 50 <= s.composite_score < 70),
        "medium_count": sum(1 for s in component_scores if 30 <= s.composite_score < 50),
        "low_count": sum(1 for s in component_scores if s.composite_score < 30),
        "top_risks": sorted(component_scores, key=lambda s: s.composite_score, reverse=True)[:10],
        "risk_by_category": group_and_average_by(component_scores, "category"),
    }
```

---

## 7. What-If Analysis Engine

This is the differentiating feature for the PoC demo. The what-if engine lets users simulate supply chain disruption scenarios and see the projected impact across their BOMs.

### 7.1 Scenario Types

#### Scenario A: Country Disruption
*"What happens if we lose access to components manufactured in [country]?"*

```python
@dataclass
class CountryDisruptionScenario:
    type: str = "country_disruption"
    country: str                     # e.g., "China", "Taiwan"
    severity: str                    # "total_loss" | "partial_disruption" | "tariff_increase"
    tariff_pct: float | None = None  # for tariff_increase type
```

**Computation**: Query all components where `country_of_origin` matches. For each affected component:
- `total_loss`: Set supply_risk and geographic_risk to 100, recompute composite
- `partial_disruption`: Multiply supply_risk by 2.0 (cap at 100), add geographic_risk penalty
- `tariff_increase`: Flag cost impact, escalate supplier_risk if single-country-source

**Output**: List of affected components, delta in composite risk scores, count of components with no alternative manufacturing site.

#### Scenario B: Supplier Failure
*"What if [manufacturer] exits the market or goes bankrupt?"*

```python
@dataclass
class SupplierFailureScenario:
    type: str = "supplier_failure"
    manufacturer: str               # e.g., "Analog Devices", "Texas Instruments"
    failure_mode: str               # "bankruptcy" | "exit_product_line" | "force_majeure"
```

**Computation**: Query all components where `manufacturer` matches. For each:
- If sole source: lifecycle_risk → 100, supply_risk → 100
- If dual source: supply_risk → 70 (lost redundancy)
- If multi-source: supply_risk += 20

**Output**: Affected component list, cross-BOM impact (which BOMs are exposed), recommended actions per component.

#### Scenario C: Component Obsolescence Wave
*"What if all NRFND parts go obsolete within 12 months?"*

```python
@dataclass
class ObsolescenceWaveScenario:
    type: str = "obsolescence_wave"
    target_statuses: list[str]      # e.g., ["NRFND", "Last Time Buy"]
    time_horizon_months: int        # Simulate obsolescence within this window
```

**Computation**: All components matching target lifecycle statuses get lifecycle_risk set to 90-100. Recompute composites. Show the cascade effect on BOM-level risk.

#### Scenario D: Custom Component Removal
*"What if I can no longer use [specific MPN]?"*

```python
@dataclass
class ComponentRemovalScenario:
    type: str = "component_removal"
    mpns: list[str]                 # one or more specific MPNs to remove
    reason: str                     # "obsolete" | "counterfeit_alert" | "sanction" | "custom"
```

**Computation**: Targeted — set the named components to maximum risk across all applicable dimensions. Show cross-BOM impact if the MPN appears in multiple BOMs.

#### Scenario E: Demand Spike
*"What if demand doubles across all programs using this BOM?"*

```python
@dataclass
class DemandSpikeScenario:
    type: str = "demand_spike"
    multiplier: float               # e.g., 2.0 for double demand
    affected_bom_ids: list[UUID] | None  # None = all BOMs
```

**Computation**: For each component, compare `quantity * multiplier` against `total_inventory`. Components where projected demand exceeds available inventory get supply_risk escalated. Highlight parts with long lead times where stockpiling is impractical.

### 7.2 Scenario Execution Flow

```
POST /api/scenarios
Request: {
    "name": "Taiwan Strait Crisis",
    "description": "Model loss of Taiwan-manufactured semiconductors",
    "scenario_type": "country_disruption",
    "parameters": {
        "country": "Taiwan",
        "severity": "total_loss"
    },
    "affected_bom_ids": ["uuid1", "uuid2"]  // null = all BOMs
}

Response: {
    "scenario_id": "uuid",
    "status": "running"
}
```

```
GET /api/scenarios/{id}/results
Response: {
    "scenario_id": "uuid",
    "name": "Taiwan Strait Crisis",
    "summary": {
        "total_components_affected": 23,
        "boms_affected": 2,
        "avg_risk_delta": +34.2,
        "components_at_critical": 18,
        "components_with_no_alternate_source": 7
    },
    "baseline_bom_risk": { "bom_uuid_1": 32.5, "bom_uuid_2": 28.1 },
    "scenario_bom_risk": { "bom_uuid_1": 78.3, "bom_uuid_2": 61.7 },
    "affected_components": [
        {
            "mpn": "XC7Z010-1CLG225C",
            "manufacturer": "AMD/Xilinx",
            "boms": ["CN0566 Phased Array"],
            "baseline_risk": 25.0,
            "scenario_risk": 100.0,
            "delta": +75.0,
            "risk_factors": ["Sole source from Taiwan fab", "No alternate manufacturer"],
            "recommendation": "Evaluate Zynq UltraScale+ alternatives; initiate lifetime buy"
        }
    ]
}
```

### 7.3 Comparison View

The UI must support side-by-side comparison:

```
┌─────────────────────────┬─────────────────────────┐
│     BASELINE STATE      │   SCENARIO: Taiwan      │
├─────────────────────────┼─────────────────────────┤
│ BOM Risk Score: 32.5    │ BOM Risk Score: 78.3    │
│ Critical: 3 components  │ Critical: 18 components │
│ High: 8 components      │ High: 12 components     │
│ Medium: 22 components   │ Medium: 8 components    │
│ Low: 54 components      │ Low: 49 components      │
├─────────────────────────┼─────────────────────────┤
│        RISK HEATMAP (before)  →  (after)          │
│  [interactive component grid with color shift]     │
└─────────────────────────┴─────────────────────────┘
```

---

## 8. API Specification

### 8.1 Endpoints

```
# BOM Management
POST   /api/boms/upload              Upload new BOM file
GET    /api/boms                     List all BOMs
GET    /api/boms/{id}                Get BOM detail + component list
DELETE /api/boms/{id}                Delete BOM and associated data
GET    /api/boms/{id}/components     Paginated component list with filters
GET    /api/boms/cross-exposure      Cross-BOM component exposure report

# Enrichment
POST   /api/enrichment/run/{bom_id}  Trigger enrichment for a BOM
GET    /api/enrichment/status/{bom_id}  Check enrichment progress
GET    /api/components/{id}/enrichment  Get enrichment data for one component

# Risk Scoring
POST   /api/risk/score/{bom_id}      Run risk scoring for a BOM
GET    /api/risk/scores/{bom_id}     Get all risk scores for a BOM
GET    /api/risk/summary/{bom_id}    Get BOM-level risk summary
GET    /api/risk/profiles             List available scoring profiles
PUT    /api/risk/profiles/{name}      Create/update a scoring profile

# What-If Scenarios
POST   /api/scenarios                 Create and run a scenario
GET    /api/scenarios                 List all scenarios
GET    /api/scenarios/{id}            Get scenario detail
GET    /api/scenarios/{id}/results    Get scenario results
DELETE /api/scenarios/{id}            Delete scenario
GET    /api/scenarios/templates       Get pre-built scenario templates

# Export
GET    /api/export/risk-report/{bom_id}     Generate risk report (markdown)
GET    /api/export/scenario-report/{id}     Generate scenario impact report
```

### 8.2 Common Query Parameters

All list endpoints support:
- `page` (int, default 1)
- `per_page` (int, default 50, max 200)
- `sort_by` (field name)
- `sort_order` (asc/desc)
- `search` (full-text search on relevant fields)

Component list endpoints additionally support:
- `lifecycle_status` (filter by status)
- `risk_min` / `risk_max` (filter by composite risk score range)
- `manufacturer` (filter by manufacturer)
- `category` (filter by component category)

---

## 9. Frontend Requirements

### 9.1 Pages

#### Dashboard (Landing Page)
- Aggregate stats across all BOMs: total components tracked, overall risk posture, trend sparkline (if snapshots exist)
- "At a Glance" cards: count of Critical/High/Medium/Low components across all BOMs
- Recent activity: latest BOM uploads, enrichment runs, scenario analyses
- Quick-action: "Upload BOM" button, "Run Scenario" button

#### BOM Manager
- Left panel: list of all uploaded BOMs with risk summary badges
- Main panel: component table for selected BOM with sortable/filterable columns (MPN, manufacturer, lifecycle status, composite risk score, inventory, lead time)
- Component row expansion: show enrichment detail, risk breakdown radar chart, alternates list
- Bulk actions: "Enrich All", "Score All", "Export Report"
- Upload modal: drag-and-drop with column mapping preview

#### Risk Analysis
- Heatmap: 2D grid of components, color-coded by risk score (green → yellow → red), groupable by category, manufacturer, or lifecycle status
- Risk distribution: histogram of component risk scores
- Top-10 risk table: highest risk components with drill-down to risk factors
- Cross-BOM exposure table: MPNs appearing in multiple BOMs, sorted by risk
- Scoring profile selector: switch between weight profiles and see risk recalculate

#### What-If Analysis
- Scenario builder: select scenario type from template, configure parameters
- Impact visualization: before/after comparison view (Section 7.3)
- Affected components table: sortable by risk delta, with recommendation column
- Scenario library: list of saved scenarios with summary stats
- "Compare scenarios": overlay two scenario results on the same visualization

### 9.2 UI Component Requirements

- **Risk Badge**: Color-coded pill (Critical=red, High=orange, Medium=yellow, Low=green) with score. Used throughout.
- **Risk Radar Chart**: 5-axis radar (lifecycle, supply, geographic, supplier, regulatory) per component. Recharts `RadarChart`.
- **Risk Heatmap**: Grid of colored cells, one per component. Interactive — hover shows detail, click drills down. Custom implementation or D3.
- **Delta Indicator**: Show before/after with arrow and color (↑ red for risk increase, ↓ green for decrease).
- **Data Table**: Sortable, filterable, paginated. Column visibility toggle. Export to CSV.

### 9.3 Technology Stack

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Framework | React 18+ with TypeScript | Standard, Cursor-friendly |
| Build | Vite | Fast dev server, HMR |
| Styling | Tailwind CSS | Rapid prototyping, no design system to build |
| Charts | Recharts | React-native, good radar/bar/line chart support |
| Heatmap | Custom SVG or D3 | Recharts heatmap is limited |
| Table | TanStack Table v8 | Sorting, filtering, pagination, column resize |
| HTTP | fetch + typed wrapper | No need for axios in PoC |
| State | React Query (TanStack Query) | Server state management, caching, refetch |
| Routing | React Router v6 | Standard |

---

## 10. Configuration & Environment

### 10.1 `.env.example`

```bash
# Database
DATABASE_URL=postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel

# Nexar API (required for live enrichment)
NEXAR_CLIENT_ID=
NEXAR_CLIENT_SECRET=

# SiliconExpert API (optional — stub if unavailable)
SILICONEXPERT_API_KEY=
SILICONEXPERT_API_URL=https://api.siliconexpert.com/

# Z2Data API (optional — stub if unavailable)
Z2DATA_API_KEY=

# App Settings
ENRICHMENT_CACHE_DAYS=7
ENRICHMENT_RATE_LIMIT_DELAY=0.5
RISK_DEFAULT_PROFILE=default
```

### 10.2 Docker Compose (Local Dev)

```yaml
version: "3.8"
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: sentinel
      POSTGRES_PASSWORD: sentinel
      POSTGRES_DB: sentinel
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

The backend and frontend run natively (not containerized) during development for faster iteration with Cursor.

---

## 11. Demo Script & Seed Data

### 11.1 CN0566 Seed BOM

The `scripts/seed_demo_bom.py` script should:

1. Load the CN0566 BOM (include a curated version in `scripts/data/cn0566_bom.csv` with columns pre-mapped)
2. Insert into the database as a BOM named "CN0566 Phased Array Radar — EVAL Board"
3. Run synthetic enrichment (Section 5.4) to populate all enrichment fields with realistic mock data
4. Run risk scoring to populate all risk scores
5. Create three pre-built scenarios:
   - "Taiwan Semiconductor Disruption" (country_disruption, Taiwan, total_loss)
   - "ADI Market Exit — Beamformer Product Line" (supplier_failure, Analog Devices, exit_product_line)
   - "NRFND Accelerated Obsolescence" (obsolescence_wave, ["NRFND"], 12 months)
6. Execute all three scenarios to pre-populate results

After seeding, the dashboard should immediately show a populated, interactive environment.

### 11.2 Demo Walkthrough

A successful PoC demo should show:

1. **Upload a second BOM** — Upload the ADALM-PLUTO BOM alongside the pre-loaded CN0566. Show that the system handles multiple BOMs and detects shared components.
2. **Cross-BOM exposure** — Show that the AD9363 (and other shared parts) are flagged as appearing in both BOMs.
3. **Risk dashboard** — Walk through the risk heatmap, drill into a high-risk component, show the radar chart of risk dimensions, explain the risk factors.
4. **What-if: Taiwan scenario** — Run the Taiwan disruption scenario. Show the before/after comparison. Point out that the Zynq FPGA (manufactured in Taiwan) goes to critical risk and cascades BOM-level risk.
5. **What-if: Supplier exit** — Run the ADI supplier exit scenario. Show the massive impact on the CN0566 BOM (heavily ADI-dependent) vs. moderate impact on the PLUTO BOM.
6. **Export** — Generate a risk report for the CN0566 BOM showing the top-10 at-risk components with recommendations.

---

## 12. Implementation Priority

### Phase 1: Core Loop (Weeks 1-2)
- [ ] PostgreSQL setup + Alembic migrations for all tables
- [ ] BOM upload + parser (Excel/CSV) with column auto-detection
- [ ] Nexar API client (or synthetic mock data generator)
- [ ] Enrichment orchestrator (single-provider)
- [ ] Risk scoring engine (rule-based, default profile)
- [ ] FastAPI endpoints: BOM CRUD, enrichment trigger, risk scores
- [ ] Seed script with CN0566 BOM + synthetic enrichment
- [ ] Frontend: BOM upload, component table, basic risk badges

### Phase 2: What-If & Visualization (Weeks 3-4)
- [ ] What-if engine: all 5 scenario types
- [ ] Scenario API endpoints
- [ ] Frontend: Risk heatmap, radar charts, risk analysis page
- [ ] Frontend: Scenario builder, impact comparison view
- [ ] Cross-BOM exposure view
- [ ] Scoring profile management (switch weight profiles)
- [ ] Export: Markdown risk report

### Phase 3: Polish & Scale (Week 5+)
- [ ] SiliconExpert integration (when API access acquired)
- [ ] Z2Data integration (when trial access acquired)
- [ ] Snapshot/trend tracking (delta between enrichment runs)
- [ ] Monitoring workflow (scheduled re-enrichment)
- [ ] Second demo BOM (ADALM-PLUTO)
- [ ] LLM-generated recommendations for high-risk components

---

## 13. Testing Strategy

### Unit Tests
- `test_ingest.py`: Column auto-detection, MPN normalization, duplicate handling, malformed file graceful failure
- `test_enrichment.py`: Mock API responses, cache hit/miss, rate limiting, provider failure isolation
- `test_risk.py`: Scoring determinism (same input → same output), weight profile application, edge cases (missing enrichment data → scored as "unknown" risk)
- `test_whatif.py`: Each scenario type produces expected risk deltas, cross-BOM propagation

### Integration Tests
- Upload BOM → enrich → score → export full pipeline
- Scenario creation → execution → results retrieval
- Multi-BOM: upload two BOMs, verify cross-exposure view

---

## 14. Future Considerations (Out of Scope for PoC)

These are recorded for architecture awareness — do not implement in PoC:

- **Graph database layer**: Neo4j for component → supplier → site → country traversal. The relational model works for PoC but graph queries become essential at scale.
- **ML obsolescence prediction**: Train on historical SiliconExpert lifecycle data. Requires 6+ months of snapshot data to be useful.
- **GIDEP integration**: Manual for now. Future: scheduled scrape/export from GIDEP portal.
- **Notification system**: Email/Slack alerts when monitoring detects threshold-crossing changes.
- **Multi-tenancy**: Not needed for single-laptop PoC. Required for any shared deployment.
- **SBOM correlation**: Map hardware BOM components to software supply chain for holistic risk.
- **PLM/ERP integration**: Push risk data into PTC Windchill, SAP, etc. via webhooks or batch export.
