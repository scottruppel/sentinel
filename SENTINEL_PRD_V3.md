# SENTINEL PRD — Version 3 (Draft)

**ERP / operational data integration**

**Status:** Draft — requirements capture only. **No implementation commitment.** Revisit before build.

**Related documents:** [SENTINEL_PRD.md](SENTINEL_PRD.md) (baseline PoC), [SUMMARY.md](SUMMARY.md) (system summary).

---

## 1. Purpose

This PRD defines how SENTINEL should integrate **enterprise operational data** (typically sourced from an ERP, MRP, or PLM-adjacent system) so that **program-specific context**—forecasts, procurement history, on-hand inventory, replacement complexity—feeds **standardized inputs** into risk analysis. The goal is a **scalable, vendor-agnostic interface**: customers map their native fields to a **canonical schema** once; SENTINEL remains ERP-agnostic.

**Out of scope for V3 definition (unless explicitly added later):**

- Building specific connectors for SAP, Oracle NetSuite, Microsoft Dynamics, etc. (those are *integration implementations* atop this PRD).
- Replacing market enrichment (Nexar, SiliconExpert, etc.); operational data **complements** market truth, not replaces it.

---

## 2. Problem statement

Today, line-level risk is driven primarily by **market enrichment** (lifecycle, distributor inventory, geography) and **static BOM fields** (MPN, quantity, ref des). Customers already hold richer data in ERP: **how much they expect to consume**, **what they last bought**, **how painful a redesign is**. Ignoring that data limits **business-relevant prioritization** (e.g., a medium market-risk part with huge forecast + high redesign complexity may deserve more attention than a high market-risk part with negligible usage).

---

## 3. Design principles

1. **Canonical contract, not raw ERP shapes** — Every ERP maps to one versioned SENTINEL operational profile; no hard-coded SAP field names in core logic.
2. **Separation of concerns** — **Market intelligence** = external part/supply truth. **Operational profile** = *this program’s* exposure and engineering reality. Merge for scoring and UX; keep provenance clear.
3. **Graceful degradation** — If operational data is absent or partial, scoring and UI behave as today (baseline PoC), with clear “data missing” indicators where relevant.
4. **Auditability** — Know **source system**, **sync time**, and **match method** for each operational attach.
5. **Privacy** — Operational payloads may include internal IDs, costs, and plant codes; treat as **Tier A/B** per internal data-tiering policy; redact in exports/LLM as configured.

---

## 4. Current system baseline (reference)

| Area | Behavior relevant to V3 |
|------|-------------------------|
| `Component` model | Core BOM columns + `metadata` JSONB ([`backend/sentinel/db/models.py`](backend/sentinel/db/models.py)). |
| Risk engine | Five dimensions from merged enrichment + `manufacturer`; no ERP fields today ([`backend/sentinel/risk/scorer.py`](backend/sentinel/risk/scorer.py)). |
| BOM ingest | Fuzzy column mapping for CSV/XLSX ([`backend/sentinel/ingest/parser.py`](backend/sentinel/ingest/parser.py)). |

---

## 5. Canonical operational profile (requirements)

Operational data MUST be expressible as a **versioned** payload. The following **field groups** are **required to be representable** in V3; individual fields may be optional per line, unless noted.

### 5.1 Schema versioning

- **Requirement:** Every payload carries `operational_profile_version` (string, e.g. `"2026.1"`).
- **Requirement:** SENTINEL rejects or warns on unknown major versions per product policy (TBD: strict reject vs. best-effort parse).

### 5.2 Identity and provenance (for matching and audit)

| Field | Req | Notes |
|-------|-----|--------|
| `source_system` | Recommended | e.g. `"sap_s4"`, `"netsuite"`, `"manual_csv"` |
| `erp_item_id` | Optional | Customer’s stable part/material ID |
| `erp_plant` / `site_code` | Optional | Multi-plant programs |
| `last_synced_at` | Recommended | ISO-8601 timestamp |
| `sync_job_id` | Optional | Correlation id for bulk loads |

### 5.3 Demand / planning

| Field | Req | Notes |
|-------|-----|--------|
| `demand_forecast_units_6m` | Optional | Non-negative number |
| `demand_forecast_units_12m` | Optional | Non-negative number |
| `forecast_confidence` | Optional | Enum TBD: e.g. `high` / `medium` / `low` or numeric |

### 5.4 Procurement

| Field | Req | Notes |
|-------|-----|--------|
| `last_order_quantity` | Optional | Non-negative |
| `last_order_date` | Optional | Date |
| `open_po_quantity` | Optional | Sum of open POs in ERP units |
| `avg_unit_cost` | Optional | Sensitive; may be omitted by policy |

### 5.5 Inventory (customer position)

| Field | Req | Notes |
|-------|-----|--------|
| `on_hand_quantity` | Optional | Distinct from Nexar “market” inventory |
| `safety_stock` | Optional | |
| `allocated_quantity` | Optional | If available |

### 5.6 Engineering / program impact

| Field | Req | Notes |
|-------|-----|--------|
| `replacement_complexity` | Optional | Enum: **`low` \| `medium` \| `high`** (required set for V3) |
| `estimated_redesign_weeks` | Optional | Integer |
| `qualification_required` | Optional | Boolean (TBD) |
| `is_critical_path` | Optional | Boolean (TBD) |

### 5.7 Extensibility

- **Requirement:** Allow **`extras`** object for vendor-specific keys that do not affect core scoring until explicitly mapped in a later version.

---

## 6. Storage model (design choices — not decided)

**Option A — JSONB on `Component.metadata_`**

- Embed under a reserved key, e.g. `metadata.operational` or `metadata.operational_v2026_1`.
- **Pros:** Fast to ship, no migration.
- **Cons:** Weaker DB constraints; heavier reporting queries.

**Option B — Dedicated table `component_operational`**

- Columns: `component_id` FK, `schema_version`, typed columns for “hot” fields, `extras JSONB`, timestamps.
- **Pros:** Indexable, clear lifecycle, optional history rows.
- **Cons:** Migration, more CRUD code.

**Decision required before implementation:** Phase A only, Phase B only, or **A then migrate to B** (recommended in planning notes).

---

## 7. Integration interfaces (requirements)

### 7.1 REST API (required capability)

- **Single line:** Upsert operational profile for one `component_id` (after BOM exists).
- **Bulk:** Upsert many lines for one `bom_id` using **match keys** (see §8).
- **Responses:** Per-row status: `matched`, `ambiguous`, `not_found`, `validation_error` with machine-readable codes.

**Authentication / authorization:** TBD (API keys, OAuth2 client credentials, mTLS). Not defined in this PRD.

### 7.2 File-based ingest (required capability)

- Second-pass CSV (or sheet) uploaded **after** BOM ingest, with **column alias map** analogous to existing BOM [`COLUMN_MAPPINGS`](backend/sentinel/ingest/parser.py).
- **Requirement:** Documented template + example file in repo/docs when implemented.

### 7.3 Future (non-requirements for V3 closure)

- Scheduled pull from ERP, iPaaS (Boomi, MuleSoft), webhooks — **capture as roadmap**, not V3 must-have.

---

## 8. Matching rules (requirements + TBD)

**Requirement:** Support matching a customer row to exactly one `Component` when possible.

**Preferred order (subject to product decision):**

1. `erp_item_id` if previously stored on the component during BOM upload, OR
2. Composite: `(mpn_normalized, manufacturer, reference_designator, bom_id)`, OR
3. Composite: `(mpn_normalized, manufacturer, bom_id)` with **ambiguity** flagged if multiple hits.

**TBD:** Exact precedence, maximum ambiguity tolerance, and whether to allow **fuzzy** MPN match (risky; default should be **exact normalized MPN**).

---

## 9. Risk engine integration (design choices — not decided)

Operational data must feed into risk **without conflating** market-derived scores. Candidate approaches (pick one or combine in phases):

| Approach | Description | Pros / cons |
|----------|-------------|-------------|
| **A — Impact multiplier** | Derive `business_exposure_score` 0–100 from operational fields; combine with existing composite via documented formula (e.g. weighted blend or max). | Simple; one headline number. |
| **B — Sixth dimension** | Add `operational_risk` dimension + weight profile alongside lifecycle/supply/geo/supplier/regulatory. | Explainable; more UI work. |
| **C — Scenario-only first** | Use ERP fields only in what-if / demand scenarios before changing baseline composite. | Safest rollout; less baseline value. |

**Formulas TBD:** How `replacement_complexity`, forecasts, and inventory interact (e.g., shortage risk when `on_hand + open_po < f(forecast horizon)`).

**Requirement:** Whatever is chosen, **risk_factors** (or equivalent) must cite **operational** inputs distinctly from **market** inputs.

---

## 10. API sketch (non-binding)

Illustrative only; final paths and bodies TBD.

- `PUT /api/components/{component_id}/operational` — body = canonical operational profile + version.
- `POST /api/boms/{bom_id}/operational/bulk` — body = `{ items: [ { match: {...}, operational: {...} } ] }`.
- `POST /api/boms/{bom_id}/operational/upload` — multipart CSV for file-based merge.

---

## 11. Security, compliance, and governance

- Classify ERP payloads per internal **Tier A/B** policy; never send raw ERP IDs to LLM/export without explicit config.
- **Audit:** Log bulk job id, row counts, errors; optional `operational_sync_log` table for enterprise (TBD).
- **Retention:** TBD alignment with customer DPA.

---

## 12. Documentation deliverables (when implemented)

- Canonical field dictionary (single source of truth).
- Integration guide: REST + CSV, matching rules, error codes.
- Update [SUMMARY.md](SUMMARY.md) and main [SENTINEL_PRD.md](SENTINEL_PRD.md) cross-reference.

---

## 13. Work breakdown — full to-do list (checklist)

Use this as the implementation backlog when V3 is approved.

| ID | Task | Notes |
|----|------|--------|
| V3-1 | Define **Pydantic** (or equivalent) models + **JSON Schema** for operational profile version `2026.1` (or chosen id). | Includes validation rules, enums. |
| V3-2 | Decide **storage**: metadata JSONB vs dedicated table vs hybrid; document migration path. | Gates DB work. |
| V3-3 | Implement **REST** single + bulk upsert with validation and match resolution. | Includes error model. |
| V3-4 | Implement **CSV second-pass** ingest with **OPERATIONAL_COLUMN_MAPPINGS** and merge to components. | Template + example. |
| V3-5 | Decide and implement **risk integration** (A/B/C from §9) + factor strings. | Backward compatible default. |
| V3-6 | **UI:** Show operational inputs and effect on score (or multiplier) on BOM detail / risk views. | Empty state when no data. |
| V3-7 | **Tests:** Matching edge cases (duplicate MPN, missing manufacturer, ambiguous ref des). | |
| V3-8 | **Auth** for integration endpoints (API key or OAuth). | Product/security decision. |
| V3-9 | **Docs:** Integration guide + PRD cross-links. | |

---

## 14. Open design questions (summary)

Capture these in grooming before build:

1. Storage: JSONB only vs dedicated table vs phased migration?
2. Risk: multiplier vs sixth dimension vs scenario-only phase 1?
3. Exact formulas linking forecast, inventory, open PO, and `replacement_complexity`.
4. Matching: strict keys only vs allow erp_item_id without prior BOM stamp?
5. Versioning: reject unknown schema vs soft accept with warnings?
6. Cost fields: supported in v1 operational profile or excluded for sensitivity?
7. Multi-currency / UoM: required normalization or out of scope?
8. Authentication model for enterprise ERP push.

---

## 15. Success criteria (when implemented)

- A customer can attach operational data **without** SENTINEL knowing their ERP vendor, using the canonical schema.
- Scores or derived “business exposure” **change predictably** when operational inputs change, with explainable factors.
- No operational data **required** for the product to function as the v0.1 PoC does today.

---

*End of SENTINEL PRD V3 (Draft).*
