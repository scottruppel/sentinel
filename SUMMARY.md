# SENTINEL — System Summary

## Supply Chain Exposure & DMSMS Intelligence Tool

SENTINEL is a local-first BOM (Bill of Materials) management and DMSMS (Diminishing Manufacturing Sources and Material Shortages) risk intelligence tool. It ingests hardware BOMs, enriches each component with lifecycle and supply chain data, scores risk across five dimensions, and provides interactive what-if analysis for supply chain disruption scenario planning.

This document explains the data model, scoring mechanics, scenario engine, and how they satisfy the requirements defined in the PRD.

---

## 1. Input Data

### 1.1 BOM Files

The primary input is a hardware Bill of Materials uploaded as an Excel (`.xlsx`) or CSV (`.csv`) file. Each BOM represents a single hardware design and contains line items for electronic components.

**Seed BOMs included for demo:**

| BOM | Description | Components | Purpose |
|-----|-------------|------------|---------|
| CN0566 Phased Array | Analog Devices X-band phased array radar/comms eval board | ~60 unique MPNs | Primary demo BOM with defense-relevant RF, digital, and passive components |
| ADALM-PLUTO (PlutoSDR) | Analog Devices software-defined radio platform | ~45 unique MPNs | Secondary BOM demonstrating cross-BOM exposure (shares AD9363, passives) |

**What a BOM row looks like:**

| Reference | MPN | Manufacturer | Description | Qty | Package | Category |
|-----------|-----|-------------|-------------|-----|---------|----------|
| U1,U2,U3,U4 | ADAR1000BCPZ | Analog Devices | X-Band 4-Channel Beamformer RFIC | 4 | LFCSP-52 | IC |
| U7 | ADF4159CCPZ | Analog Devices | 13 GHz Fractional-N Frequency Synthesizer | 1 | LFCSP-24 | IC |
| C1-C47 | GRM155R71C104KA88D | Murata | 100nF MLCC | 47 | 0402 | Capacitor |

### 1.2 Column Auto-Detection

BOMs from different organizations use wildly inconsistent column headers. The parser uses fuzzy matching against a dictionary of known aliases to automatically map incoming headers to internal fields:

- **MPN**: "mpn", "manufacturer part number", "mfr part", "part number", "mfg pn", ...
- **Manufacturer**: "manufacturer", "mfr", "mfg", "vendor", ...
- **Reference Designator**: "reference", "ref des", "refdes", "designator", ...
- **Quantity**: "qty", "quantity", "count", "amount"

If no exact match is found for the MPN column, a secondary heuristic searches for any header containing both "part" and "number". Parse warnings are returned to the user indicating any ambiguities.

### 1.3 MPN Normalization

Raw manufacturer part numbers from different sources often include packaging codes, distributor suffixes, and formatting inconsistencies. Before storage, every MPN is normalized:

1. Convert to uppercase
2. Strip DigiKey ordering suffixes (`-ND`, `-1-ND`)
3. Strip lead-free suffixes (`#PBF`)
4. Strip packaging descriptors (`REEL`, `TAPE`, `CUT`, `BULK`)
5. Collapse all whitespace

This ensures that `ADAR1000BCPZ-ND`, `ADAR1000BCPZ-REEL`, and `ADAR1000BCPZ` all resolve to the same normalized MPN `ADAR1000BCPZ`. Cross-BOM exposure detection depends on this normalization — when two BOMs reference the same physical part under slightly different ordering codes, the system recognizes them as identical.

### 1.4 Enrichment Data

Each component is enriched with market intelligence from external APIs (or synthetic data for offline development). The enrichment record captures:

| Field | Description | Example |
|-------|-------------|---------|
| `lifecycle_status` | Where the part sits in its product lifecycle | Active, NRFND, Last Time Buy, Obsolete |
| `yteol` | Years to End of Life (estimated remaining production) | 3.0 |
| `total_inventory` | Sum of stock across authorized distributors | 2,500 |
| `avg_lead_time_days` | Average factory lead time | 56 |
| `distributor_count` | Number of distributors carrying the part | 4 |
| `num_alternates` | Count of form-fit-function cross-references | 2 |
| `country_of_origin` | Where the part is manufactured | Taiwan, USA, China |
| `single_source` | Whether only one manufacturer makes this part globally | true/false |
| `rohs_compliant` | EU RoHS directive compliance | true/false |
| `reach_compliant` | EU REACH regulation compliance | true/false |

**Enrichment sources (pluggable provider architecture):**

| Provider | Data Strength | Status |
|----------|--------------|--------|
| **Nexar** (Octopart) | Real-time inventory, pricing, lead times, specs via GraphQL | Implemented — OAuth2 client with token management |
| **SiliconExpert** | Lifecycle forecasting (YTEOL), PCN history, cross-references | Stub — awaiting API trial access |
| **Z2Data** | Sub-tier supplier mapping, manufacturing site locations, geographic risk | Stub — awaiting API trial access |
| **Synthetic** | Realistic mock data generated from statistical distributions | Implemented — used for offline/demo development |

The enrichment orchestrator fans out to all configured providers concurrently per component, respects a configurable cache window (default: 7 days), and applies rate limiting between API calls to stay within provider quotas.

### 1.5 Synthetic Data Generation

For demo and offline development, the synthetic enrichment generator produces statistically plausible data:

**Lifecycle distribution** (models a ~5-year-old design):
- 55% Active, 15% Active (single source), 12% NRFND, 8% Last Time Buy, 10% Obsolete

**Category-aware profiles** tune inventory, lead time, and distributor ranges:
- ICs: lower inventory (50–50,000), longer leads (7–120 days), fewer distributors
- Passives (capacitors/resistors): massive inventory (10K–10M), short leads (3–28 days), many distributors

**Hand-tuned overrides** for key components ensure realistic demo results. For example, the Xilinx Zynq FPGA (`XC7Z010-1CLG225C`) is explicitly set to NRFND status with Taiwan as country of origin, making it a natural candidate to highlight in the Taiwan disruption scenario.

---

## 2. Risk Scoring Engine

### 2.1 Overview

Every component is scored on a 0–100 scale across five independent risk dimensions. These dimension scores are then combined into a single composite score using a configurable weight profile. The system also generates human-readable risk factor explanations and actionable recommendations.

### 2.2 Risk Dimensions

#### Lifecycle Risk (default weight: 30%)

Measures how close a component is to end-of-life or obsolescence.

| Condition | Score | Rationale |
|-----------|-------|-----------|
| Obsolete, no alternates | 100 | Maximum risk — no replacement path |
| Obsolete, alternates exist | 80 | Severe but manageable with redesign |
| Last Time Buy, window expired | 90 | Missed the buy window |
| Last Time Buy, window open | 70 | Urgent action needed |
| NRFND, YTEOL < 2 years | 60 | Near-term obsolescence likely |
| NRFND, YTEOL 2–5 years | 40 | Medium-term planning needed |
| Active, single manufacturer | 25 | Low immediate risk but fragile |
| Active, multi-source | 5 | Healthy |

#### Supply Risk (default weight: 25%)

Evaluates current market availability and procurement difficulty.

| Condition | Score |
|-----------|-------|
| Zero distributor inventory | 100 |
| Very low inventory (< 100 units) | 75 |
| Limited inventory (< 1,000 units) | 50 |
| Lead time > 52 weeks | 80 |
| Lead time 26–52 weeks | 50 |
| Lead time > 90 days | 30 |
| Only 0–1 distributors | 40 |
| Healthy supply | 5 |

Multiple conditions can compound — a part with low inventory AND long lead time receives the highest applicable score.

#### Geographic Risk (default weight: 20%)

Assesses geopolitical concentration and exposure to disruption based on manufacturing location.

| Condition | Score |
|-----------|-------|
| Sanctioned country (Russia, Iran, N. Korea, Syria, Cuba) | 100 |
| High-risk country (China, + sanctioned set) | 60 |
| Taiwan (specific geopolitical risk) | 55 |
| Unknown country of origin | 50 |
| Standard low-risk country | 10 |

#### Supplier Risk (default weight: 15%)

Evaluates dependency on a single manufacturer or limited supply base.

| Condition | Score |
|-----------|-------|
| Sole source — one manufacturer, no alternates | 85 |
| Single source — one manufacturer, alternates exist | 65 |
| Dual source (1+ alternates) | 15 |
| Multi-source (3+ alternates) | 5 |
| Unknown sourcing | 50 |

#### Regulatory Risk (default weight: 10%)

Flags environmental and trade compliance concerns.

| Condition | Score |
|-----------|-------|
| Non-RoHS compliant | 60 |
| REACH SVHC listed | 50 |
| Fully compliant | 5 |

Non-compliance flags are additive — a part that fails both RoHS and REACH receives the higher individual score (60), not a sum.

### 2.3 Composite Score Calculation

The composite score is a weighted sum of the five dimension scores:

```
composite = (lifecycle × 0.30) + (supply × 0.25) + (geographic × 0.20)
          + (supplier × 0.15) + (regulatory × 0.10)
```

The weights are defined by a **Risk Weight Profile**. Two profiles ship by default:

| Profile | Lifecycle | Supply | Geographic | Supplier | Regulatory |
|---------|-----------|--------|------------|----------|------------|
| `default` | 0.30 | 0.25 | 0.20 | 0.15 | 0.10 |
| `supply_chain_focus` | 0.15 | 0.30 | 0.30 | 0.20 | 0.05 |

Users can create custom profiles via the API. The `supply_chain_focus` profile, for example, doubles the emphasis on geographic and supply risk — useful for organizations primarily concerned with geopolitical disruptions.

### 2.4 Risk Level Classification

| Level | Score Range | Color |
|-------|------------|-------|
| Critical | ≥ 70 | Red |
| High | 50–69 | Orange |
| Medium | 30–49 | Yellow |
| Low | < 30 | Green |

### 2.5 BOM-Level Aggregation

After scoring individual components, the system rolls up to a BOM-level summary:

- **Overall Score**: mean of all component composite scores
- **Max Component Risk**: highest single component score (identifies worst-case exposure)
- **Distribution Counts**: how many components fall in each risk level
- **Top 10 Risks**: the 10 highest-scoring components for triage

The overall score is cached on the `boms` table for fast retrieval in list views.

### 2.6 Recommendations

For any component scoring ≥ 30, the engine generates actionable recommendations based on the dominant risk factors:

| Dominant Factor | Generated Recommendation |
|----------------|------------------------|
| Obsolete | Initiate lifetime buy or identify form-fit-function alternate |
| Last Time Buy | Execute last-time buy before window closes |
| NRFND | Plan migration to next-generation part |
| Sole/single source | Qualify second source to reduce supplier dependency |
| Low inventory / long lead | Build safety stock buffer; negotiate supply agreements |
| Geographic concentration | Identify alternate manufacturing sources outside risk region |

---

## 3. What-If Scenario Engine

The what-if engine is SENTINEL's differentiating feature. It lets users simulate hypothetical supply chain disruptions and immediately see the projected impact on their BOMs — before the disruption occurs.

### 3.1 How It Works

1. **User defines a scenario** — selects a type and configures parameters (e.g., "What if we lose Taiwan?")
2. **Engine loads baseline** — retrieves current risk scores for all components in the targeted BOMs
3. **Engine applies perturbation** — modifies the relevant risk dimensions based on the scenario rules
4. **Engine recomputes composite** — calculates new composite scores using the same weight profile
5. **Engine calculates deltas** — for each affected component, computes `delta = scenario_score - baseline_score`
6. **Results stored** — full impact analysis is persisted as JSON on the scenario record

### 3.2 Scenario Types

#### A. Country Disruption

*"What happens if we lose access to components manufactured in [country]?"*

**Parameters**: country name, severity level (total_loss / partial_disruption / tariff_increase)

**Mechanics by severity**:
- `total_loss`: Supply risk → 100, Geographic risk → 100 for all components manufactured in that country
- `partial_disruption`: Supply risk × 2.0 (capped at 100), Geographic risk + 30
- `tariff_increase`: Supply risk + 20, Geographic risk + 20

**Example**: A Taiwan total-loss scenario sets the Xilinx Zynq FPGA from a baseline composite of ~42 to ~85, pushing it from Medium to Critical.

#### B. Supplier Failure

*"What if [manufacturer] exits the market or goes bankrupt?"*

**Parameters**: manufacturer name, failure mode (bankruptcy / exit_product_line / force_majeure)

**Mechanics**:
- Sole source (no alternates): Lifecycle risk → 100, Supply risk → 100
- Sole source (has alternates): Lifecycle risk → 80, Supply risk → 70
- Multi-source: Supply risk + 20
- All affected: Supplier risk + 30

**Example**: An Analog Devices exit scenario hits the CN0566 BOM hard — the ADAR1000 beamformers, AD9363 transceiver, and ADF4159 synthesizer are all ADI parts, many sole-sourced. The ADALM-PLUTO BOM shares only the AD9363, showing differential cross-BOM impact.

#### C. Obsolescence Wave

*"What if all NRFND parts go obsolete within 12 months?"*

**Parameters**: target lifecycle statuses (e.g., ["NRFND", "Last Time Buy"]), time horizon

**Mechanics**: All components matching the target statuses get Lifecycle risk → 95. Other dimensions are unchanged. This models the cascade effect of accelerated end-of-life.

#### D. Component Removal

*"What if I can no longer use [specific MPN]?"*

**Parameters**: list of MPNs, reason (obsolete / counterfeit_alert / sanction / custom)

**Mechanics**: Named components receive a composite score of 100 (maximum risk across all dimensions). Cross-BOM impact is surfaced if the MPN appears in multiple BOMs.

#### E. Demand Spike

*"What if demand doubles across all programs?"*

**Parameters**: multiplier (e.g., 2.0), optionally scoped to specific BOMs

**Mechanics**: For each component, projected demand (`quantity × multiplier`) is compared against `total_inventory`:
- If demand > inventory: Supply risk + 30
- If demand > 50% of inventory: Supply risk + 15
- Long lead-time parts with demand spikes are flagged as highest concern

### 3.3 Result Structure

Every scenario produces:

| Field | Description |
|-------|-------------|
| `total_components_affected` | Count of components whose risk changed |
| `boms_affected` | Count of BOMs containing affected components |
| `avg_risk_delta` | Average risk score increase across affected components |
| `components_at_critical` | Components reaching Critical level (≥ 70) post-scenario |
| `components_with_no_alternate_source` | Components at ≥ 95 (no viable path forward) |
| `baseline_bom_risk` | Per-BOM average risk before the scenario |
| `scenario_bom_risk` | Per-BOM average risk after the scenario |
| `affected_components` | Sorted list with per-component baseline, scenario score, delta, factors, and recommendations |

### 3.4 Pre-Built Demo Scenarios

Three scenarios are seeded for immediate demo use:

1. **Taiwan Semiconductor Disruption** — `country_disruption`, Taiwan, `total_loss`
2. **ADI Market Exit — Beamformer Product Line** — `supplier_failure`, Analog Devices, `exit_product_line`
3. **NRFND Accelerated Obsolescence** — `obsolescence_wave`, ["NRFND"], 12 months

---

## 4. Data Model

### 4.1 Entity Relationships

```
BOM (1) ──────── (*) Component
                      │
                      ├── (*) EnrichmentRecord   (versioned by fetched_at)
                      └── (*) RiskScoreRecord     (versioned by scored_at)

BOM (1) ──────── (*) Snapshot                     (point-in-time summaries)

Scenario                                          (standalone, references BOMs by ID array)
```

### 4.2 Key Design Decisions

- **Enrichment is versioned**: Multiple enrichment records per component (one per provider per fetch). The system always uses the most recent record. This enables trend tracking when re-enrichment runs periodically.
- **Risk scores are versioned**: Each scoring run creates new records rather than overwriting. This supports snapshot comparisons over time.
- **Cross-BOM exposure** is derived at query time by grouping on `mpn_normalized` across all BOMs, eliminating the need for a separate linking table.
- **Scenarios are self-contained**: The `results` JSONB column stores the full impact analysis inline, allowing scenario results to be served without re-computation.

---

## 5. PRD Compliance Matrix

| PRD Requirement | Implementation | Status |
|----------------|---------------|--------|
| Local-first, single-laptop deployment | Python/FastAPI backend + React/Vite frontend + local PostgreSQL | Done |
| BOM upload (Excel/CSV) with column auto-detection | `ingest/parser.py` with fuzzy header matching | Done |
| MPN normalization | `ingest/normalizer.py` with regex-based cleaning | Done |
| Multi-BOM support with cross-exposure detection | Components scoped by `bom_id`, cross-exposure query groups by `mpn_normalized` | Done |
| Nexar GraphQL integration | `enrichment/nexar.py` with OAuth2, token refresh, response parsing | Done |
| SiliconExpert / Z2Data integration | Stub providers returning `None` (ready for API keys) | Done (stubs) |
| Enrichment orchestrator with caching and rate limiting | `enrichment/orchestrator.py` with concurrent fan-out, 7-day cache, configurable delay | Done |
| Synthetic enrichment for offline dev | `scripts/generate_synthetic_enrichment.py` with lifecycle distributions and hand-tuned overrides | Done |
| 5-dimension risk scoring (0–100) | `risk/scorer.py` with lifecycle, supply, geographic, supplier, regulatory scorers | Done |
| Configurable weight profiles | `risk/weights.py` with default and supply_chain_focus profiles | Done |
| Composite score with risk factor explanations | `compute_composite()` + `risk_factors` JSONB array on each score record | Done |
| BOM-level risk aggregation | `compute_bom_risk()` with overall/max/distribution/top-10 | Done |
| What-if: Country disruption | `_handle_country_disruption()` with 3 severity levels | Done |
| What-if: Supplier failure | `_handle_supplier_failure()` with sole/single/multi-source logic | Done |
| What-if: Obsolescence wave | `_handle_obsolescence_wave()` with configurable target statuses | Done |
| What-if: Component removal | `_handle_component_removal()` with cross-BOM impact | Done |
| What-if: Demand spike | `_handle_demand_spike()` with inventory comparison | Done |
| Before/after comparison view | Frontend `ImpactView.tsx` with baseline vs. scenario side-by-side | Done |
| Risk heatmap visualization | Frontend `RiskHeatmap.tsx` (color-coded component grid) | Done |
| Radar chart per component | Frontend `ComponentCard.tsx` with Recharts `RadarChart` | Done |
| Dashboard with aggregate stats | Frontend `Dashboard.tsx` with risk distribution cards | Done |
| Scenario builder UI | Frontend `ScenarioBuilder.tsx` with dynamic parameter forms | Done |
| Markdown report export | `export/report.py` for risk and scenario impact reports | Done |
| Seed BOM (CN0566) | `scripts/data/cn0566_bom.csv` with ~60 curated components | Done |
| Second BOM (ADALM-PLUTO) | `scripts/data/pluto_bom.csv` with ~45 components, shared MPNs | Done |
| Pre-built scenarios seeded | 3 scenarios created and executed by `seed_demo_bom.py` | Done |
| Unit tests (ingest, enrichment, risk, what-if) | `backend/tests/test_*.py` — all passing | Done |
| REST API (BOM, enrichment, risk, scenarios, export) | FastAPI routers in each module | Done |
| Structured logging | `structlog` configured throughout backend | Done |
| CORS configuration | FastAPI middleware configured in `main.py` | Done |

---

## 6. Ideas for Scaling

### 6.1 Near-Term Enhancements (Next 1–3 Months)

**Live API Integration**
- Acquire SiliconExpert and Z2Data trial access. The stub providers are wired and ready — adding real implementations requires filling in HTTP calls and response mapping. Z2Data in particular unlocks sub-tier supplier and manufacturing site data, which would make geographic risk scores far more granular (per-fabrication-site rather than per-company-headquarters).

**Trend Tracking**
- The data model already supports versioned enrichment and risk scores. Build a scheduled re-enrichment job (daily or weekly) and a Snapshot comparison view showing how component risk scores drift over time. Alert when a component's composite score crosses a threshold boundary (e.g., Medium → High).

**LLM-Assisted Recommendations**
- Replace the rule-based recommendation generator with an LLM call that receives the component's risk factors, enrichment data, and known alternates, then produces a nuanced mitigation plan. The structured `risk_factors` JSON already provides the context an LLM would need.

**PDF Report Generation**
- Extend the Markdown export with a PDF renderer (e.g., WeasyPrint or ReportLab) for formal distribution to program managers and customers.

### 6.2 Medium-Term Architecture (3–6 Months)

**Graph Database Layer**
- Add Neo4j alongside PostgreSQL for supplier relationship traversal. Model: `Component → Manufacturer → Fab Site → Country`. Graph queries like "show me all components 2 hops from a Chinese fab" become natural. The relational model works for PoC but graph traversal becomes essential when mapping Tier 2/3 sub-suppliers.

**ML Obsolescence Prediction**
- Train a classifier on historical SiliconExpert lifecycle data to predict which currently-Active parts are likely to go NRFND within 12–24 months. Features: component age, category, manufacturer portfolio trends, inventory velocity, distributor coverage decline. Requires 6+ months of snapshot data to train effectively.

**GIDEP Integration**
- GIDEP (Government-Industry Data Exchange Program) publishes DMSMS notices, PCNs, and suspect counterfeit alerts. Currently manual. Build a batch import pipeline to ingest GIDEP exports and auto-match against stored MPNs, creating enrichment records flagged with GIDEP notices.

**Proactive Monitoring Agent**
- Scheduled background agent that re-queries enrichment providers on a cadence and compares to the stored baseline. Generates alerts like: "AD9363 lead time increased 40% in 30 days — 3 of 5 distributors at zero stock." Push to email, Slack, or Teams.

### 6.3 Long-Term Platform Vision (6–12+ Months)

**Multi-Tenancy**
- Add user authentication, organizations, and role-based access control. Each organization sees only its BOMs and scenarios. Required for any shared or hosted deployment.

**PLM/ERP Integration**
- Push risk data into Product Lifecycle Management tools (PTC Windchill, Siemens Teamcenter) and ERP systems (SAP) via webhooks or batch export. This lets program managers see DMSMS risk inside the tools they already use daily.

**SBOM Correlation**
- Map hardware BOM components to software supply chain data (SBOMs). A system-on-chip like the Zynq has both a hardware risk profile and a software/firmware dependency tree. Correlating these gives a holistic risk view.

**Alternative Part Recommendation Engine**
- When a high-risk component is flagged, automatically pull cross-references from SiliconExpert and Nexar, filter by (active lifecycle, multi-source, in-stock, compliant), rank by parametric similarity, and present a curated shortlist. An LLM agent generates the trade-off analysis.

**Real-Time Geopolitical Signal Monitoring**
- Integrate news feeds (GDELT, NewsAPI) and SEC EDGAR filings to detect early warning signals: factory fires, sanctions announcements, supplier financial distress, natural disasters. Correlate events to manufacturing sites via Z2Data's site mapping to predict which components are affected before the impact hits distributor inventory.

**Federated Deployment**
- Support air-gapped / classified enclaves with offline-capable operation. Periodically sync enrichment data bundles into isolated environments. Critical for defense programs operating on classified networks.

---

## 7. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | Python 3.11+, FastAPI, Uvicorn | REST API, async request handling |
| ORM | SQLAlchemy 2.0 (async) + asyncpg | Database access with type safety |
| Migrations | Alembic | Schema versioning |
| Database | PostgreSQL 16+ | Relational storage with JSONB for flexible metadata |
| Config | Pydantic-Settings | Environment-driven configuration |
| Logging | Structlog | Structured, contextual logging |
| HTTP Client | httpx | Async HTTP for enrichment API calls |
| GraphQL | gql | Nexar API client |
| Frontend | React 18, TypeScript, Vite | SPA with fast HMR |
| Styling | Tailwind CSS | Utility-first styling |
| Charts | Recharts | Radar, bar, pie chart visualizations |
| Tables | TanStack Table v8 | Sortable, filterable, paginated data tables |
| State | TanStack Query | Server state caching and synchronization |
| Routing | React Router v6 | Client-side navigation |

---

*SENTINEL v0.1.0-PoC*
