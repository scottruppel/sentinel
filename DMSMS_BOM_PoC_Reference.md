# DMSMS BOM Management PoC — Seed Dataset & API Reference

## 1. Recommended Seed BOM: ADI CN0566 (ADALM-PHASER)

The **Analog Devices CN0566 Phased Array Development Platform** is the best candidate for a seed BOM. It's a real, defense-relevant hardware design (X-band phased array radar/comms) with a rich, multi-vendor component set that spans the lifecycle spectrum.

### Why CN0566

- **Defense-relevant**: 8-element phased array operating at 10-10.5 GHz — directly maps to radar, EW, and SATCOM subsystems
- **Component diversity**: Includes RF beamformers (ADAR1000), transceivers (AD9363 via PlutoSDR), synthesizers (ADF4159), LNAs, mixers, power management ICs, passives, connectors — a realistic cross-section of a defense electronics BOM
- **Multi-vendor**: Components span Analog Devices, Xilinx/AMD, Micron, plus passive component vendors — gives you multi-tier supplier exposure
- **Full BOM published**: Schematic, BOM, PCB layout, and Gerber files are freely downloadable
- **Known component lifecycle issues**: Some components in the design (e.g., Zynq 7010 variant, specific LNA/mixer parts) are at various lifecycle stages — you'll immediately have real DMSMS cases to work with

### How to Get the BOM

1. Go to the ADI downloads page: `https://www.analog.com/en/resources/evaluation-hardware-and-software/evaluation-boards-kits/EVAL-CN0566-RPIZ.html`
2. Navigate to **Design & Integration Files** (may require free ADI account registration)
3. Download the package — it includes:
   - Bill of Materials (Excel/CSV format with MPNs, manufacturer names, reference designators, quantities)
   - Full schematic (PDF)
   - PCB layout (Allegro format)
4. The BOM will contain ~80-120 unique line items with real manufacturer part numbers (MPNs)

### Alternate / Supplemental BOMs

| Source | What You Get | Why It's Useful |
|--------|-------------|-----------------|
| **ADALM-PLUTO (PlutoSDR)** | ~50-60 unique MPNs, SDR platform | Subset of CN0566; simpler starting point. BOM on ADI wiki: `wiki.analog.com/university/tools/pluto/hacking/hardware` |
| **TI TIDA-01570** | 76-81 GHz radar sensor module | Automotive radar but component types overlap defense. Full BOM downloadable from `ti.com/tool/TIDA-01570` |
| **Build-a-CubeSat (open source)** | Modular CubeSat BOMs (MCU, power, comms boards) | Space-grade/rad-tolerant parts with known DMSMS issues. Repo: `codeberg.org/buildacubesat-project/bac-hardware` |

---

## 2. APIs to Establish

### Tier 1: Component Lifecycle & Market Data (Core — establish first)

#### SiliconExpert P5 API
- **What it provides**: Lifecycle status (Active, NRFND, Last-Time-Buy, Obsolete), estimated Years-to-End-of-Life (YTEOL), PCN history, cross-references (FFF alternates), environmental compliance (RoHS, REACH, conflict minerals), GIDEP alerts, multi-source pricing, counterfeit risk data
- **Access model**: Annual subscription, tiered by unique part count. Silver and Gold packages available. REST API with JSON/XML responses
- **How to get started**: Contact their API sales team at `siliconexpert.com/contact-api/`. Request evaluation access for PoC
- **Key endpoints for PoC**: Part search by MPN → lifecycle status, YTEOL, cross-references, compliance data
- **Integration notes**: Authenticate via HTTPS POST, session-based. Pre-built integrations exist for Altium 365, PTC Windchill, Zuken — useful if you scale into PLM integration later

#### Nexar API (formerly Octopart)
- **What it provides**: Real-time distributor inventory levels, pricing across authorized distributors, lead times, lifecycle status, technical specs, datasheets, RoHS/REACH compliance
- **Access model**: GraphQL-based API. Free tier gives 1,000 matched parts. Paid tiers scale from there. Part of Altium Ltd
- **How to get started**: Sign up at `nexar.com/api`, create an organization, generate OAuth2 credentials (Client ID + Secret). Free playground for initial testing
- **Key queries for PoC**:
  ```graphql
  query {
    supSearchMpn(q: "ADAR1000BCPZ", limit: 1) {
      results {
        part {
          mpn
          manufacturer { name }
          bestDatasheet { url }
          specs { attribute { name } displayValue }
          sellers { company { name } offers { inventoryLevel prices { price } } }
        }
      }
    }
  }
  ```
- **Integration notes**: Rate-limited by matched parts, not API calls. GitHub examples available at `github.com/NexarDeveloper`

### Tier 2: Sub-Tier Supplier & Site Mapping (Critical differentiator)

#### Z2Data
- **What it provides**: Part-to-site mapping (which FAB, EMS, assembly site manufactures each part), sub-tier supplier relationships (Tier 1 → Tier 2 → Tier 3), geographic risk scoring, supplier financial health, PCN/EOL management, lifecycle forecasting, UFLPA/conflict mineral compliance
- **Access model**: Platform subscription with API access. Offers free trial for Supply Chain Watch
- **How to get started**: Request trial at `z2data.com`. Their sub-tier intelligence and Supply Chain Watch modules are what you need
- **Why this is critical**: This is the API that gets you below Tier 1. SiliconExpert and Nexar tell you about the component. Z2Data tells you where it's actually manufactured, who the sub-tier suppliers are, and what the geographic/geopolitical exposure is. Their mapping methodology uses database analysis rather than supplier surveys, so you get results immediately rather than waiting months for supplier responses
- **Key capabilities for PoC**: Upload BOM → get back manufacturing site locations at Tier 1/2/3, single-source/single-site risk flags, country-of-origin data, supplier financial risk scores

### Tier 3: Government Data (Free, requires membership)

#### GIDEP (Government-Industry Data Exchange Program)
- **What it provides**: DMSMS notices, Product Change Notices (PCNs), suspect counterfeit alerts, failure experience data, engineering data
- **Access model**: Free membership for US government agencies and their industry partners. Web-based access (recently modernized to cloud platform). CAC or username/password login
- **How to get started**: Apply for membership at `gidep.org`. As a DoD-affiliated entity (or former), you may already have access or be eligible
- **Integration notes**: GIDEP does not offer a modern REST API — data access is primarily through their web portal with search/export capabilities. For the PoC, this would be a manual enrichment step or a periodic batch export. A key value-add of your tool would be automating GIDEP data fusion with commercial API data
- **What's available**: DMSMS notices with affected NSNs and part numbers, resolution data from other programs, PCN archive

### Tier 4: Supplemental Data Sources (Phase 2)

| Source | Data | Access |
|--------|------|--------|
| **IHS Markit (now S&P Global)** | Component lifecycle, parametric data, PCN archive, environmental compliance | Commercial subscription; enterprise-grade API |
| **DLA Federal Logistics Data** | NSN-to-part-number cross-references, federal supply catalog data | Public data, various download formats |
| **SEC EDGAR API** | Supplier financial filings (10-K, 10-Q) for financial health monitoring | Free REST API at `efts.sec.gov/LATEST/` |
| **GDELT / news APIs** | Real-time geopolitical event monitoring for supply chain disruption signals | Free/open data |

---

## 3. Agentic Workflow Architecture

### Workflow 1: BOM Ingestion & Initial Enrichment
```
[User uploads BOM (Excel/CSV)]
        │
        ▼
[Parse BOM] → Extract unique MPNs + Manufacturer names
        │
        ▼
[Parallel API enrichment]
   ├── SiliconExpert → Lifecycle status, YTEOL, cross-refs, compliance
   ├── Nexar → Current inventory, pricing, lead times, distributor count
   └── Z2Data → Manufacturing sites, sub-tier suppliers, geo risk
        │
        ▼
[Normalize & merge] → Unified component record per MPN
        │
        ▼
[Store enriched BOM] → Database / structured output
```

### Workflow 2: Risk Scoring (Rule-Based for PoC)
```
[Enriched BOM data]
        │
        ▼
[Score each component across risk dimensions]
   ├── Lifecycle Risk: Obsolete=10, LTB=8, NRFND=6, Active(single-source)=4, Active(multi)=1
   ├── Supply Risk: (low inventory + increasing lead time) = high
   ├── Geographic Risk: Concentration in single country/region, conflict zone exposure
   ├── Supplier Risk: Single-source MPN, supplier financial health
   └── Regulatory Risk: ITAR, REACH, conflict mineral flags
        │
        ▼
[Weighted composite score] → Normalize 0-100
        │
        ▼
[Rank & prioritize] → Top-N at-risk components
```

### Workflow 3: Proactive Monitoring (Scheduled Agent)
```
[Cron: daily/weekly]
        │
        ▼
[For each watched BOM]
   ├── Re-query Nexar for inventory/lead time deltas
   ├── Check SiliconExpert for new PCNs or lifecycle changes
   ├── Check Z2Data for site-level event alerts
   └── (Optional) Scan news feeds for supplier disruption signals
        │
        ▼
[Compare to baseline] → Flag changes exceeding thresholds
        │
        ▼
[Generate alert] → "AD9363 lead time increased 40% in 30 days — 3 of 5 distributors at zero stock"
```

### Workflow 4: Alternative Part Recommendation (AI-Assisted)
```
[Flagged at-risk component]
        │
        ▼
[Pull cross-references from SiliconExpert + Nexar]
        │
        ▼
[Filter by: active lifecycle, multi-source, in-stock, compliant]
        │
        ▼
[Rank alternatives by: parametric similarity, availability, price, supplier diversity]
        │
        ▼
[LLM agent] → Generate human-readable recommendation with trade-off analysis
        │
        ▼
[Output] → "Recommend replacing X with Y. FFF match confirmed. 
            3 distributors with >10K units in stock. 
            Estimated qualification effort: [low/med/high]"
```

---

## 4. PoC Tech Stack (Minimal)

| Layer | Tool | Why |
|-------|------|-----|
| BOM Parser | Python (pandas, openpyxl) | Read Excel/CSV BOMs, normalize MPN formats |
| API Client | Python (requests/httpx + gql for Nexar) | Hit all enrichment APIs |
| Data Store | SQLite (Phase 1) or PostgreSQL | Store enriched component records, historical snapshots |
| Risk Engine | Python (rule-based scoring) | Composite risk scoring per component |
| Output | Markdown report + optional Streamlit dashboard | Ranked risk register, exportable |
| Orchestration | Python scripts (Phase 1), n8n or Prefect (Phase 2) | Schedule monitoring workflows |

### PoC Milestone Sequence

1. **Week 1**: Download CN0566 BOM. Parse and normalize MPNs. Stand up Nexar API (free tier). Enrich BOM with lifecycle + inventory data
2. **Week 2**: Add SiliconExpert enrichment (pending trial access). Implement rule-based risk scoring. Generate first risk report
3. **Week 3**: Add Z2Data enrichment (pending trial). Incorporate sub-tier supplier and geographic risk into scoring. Build comparative baseline snapshot
4. **Week 4**: Build monitoring workflow (delta detection on re-query). Polish output report. Demo to stakeholders

---

## 5. Key API Contact Points

| API | Signup URL | Access Type | Cost for PoC |
|-----|-----------|-------------|--------------|
| Nexar | `nexar.com/api` | Self-service signup | Free tier (1K parts) |
| SiliconExpert | `siliconexpert.com/contact-api/` | Sales contact required | Request eval/trial |
| Z2Data | `z2data.com` | Request demo/trial | Free trial available |
| GIDEP | `gidep.org` | Membership application | Free (gov/contractor) |
