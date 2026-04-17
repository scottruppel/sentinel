# SENTINEL — Supply Chain Risk Intelligence for Hardware VCs

## The Problem

**Hardware supply chains are opaque.** Your portfolio companies get asked: "Is supply chain risk a concern?" and shrug. Engineers say "we source from distributors" with no evidence of resilience.

Meanwhile:
- Taiwan manufactures 60% of semiconductor capacity
- Lead times for specialty components: 6–24 months
- Geopolitical tensions are rising
- Your portfolio companies share suppliers without knowing it

**You're making $10–50M bets on hardware with near-zero supply chain visibility.**

---

## The Solution: SENTINEL

**A SaaS platform that quantifies supply chain risk and models disruption scenarios.**

### Three Core Capabilities

#### 1. Component Risk Scoring
Input: Bill of Materials (BOM)  
Output: Risk score (0–100) for each component across 5 dimensions:
- **Lifecycle Risk**: How close is it to obsolescence? (NRFND, Last Time Buy, Obsolete, Active)
- **Supply Risk**: How available is it? (Inventory, lead time, distributor count)
- **Geographic Risk**: Where is it manufactured? (Taiwan, China, high-risk, sanctions)
- **Supplier Risk**: How dependent are you? (Sole source, single source, multi-source)
- **Regulatory Risk**: Compliance issues? (RoHS, REACH, ITAR)

**Result**: A risk profile for each component and aggregate risk for the entire product.

#### 2. What-If Scenario Modeling
Run disruption scenarios and see the impact:
- **Country Disruption**: "What if Taiwan goes offline?"
- **Supplier Failure**: "What if Analog Devices exits this product line?"
- **Obsolescence Wave**: "What if all NRFND parts go obsolete?"
- **Demand Spike**: "What if demand doubles and supply stays flat?"
- **Component Removal**: "What if one part becomes unavailable/sanctioned?"

**Result**: Before/after risk comparison, redesign effort estimate, alternates analysis.

#### 3. Portfolio-Level Exposure
**See which companies share supply chain risk.** All three of your hardware companies use the Xilinx Zynq? Taiwan crisis = portfolio crisis.

**Result**: Cross-BOM exposure map, correlated risk, portfolio-level impact modeling.

---

## Why VCs Need This

### Due Diligence
- **Pre-investment**: Quantify supply chain risk as part of diligence. Flag portfolio risk early.
- **Ongoing monitoring**: Re-score BOMs quarterly. Alert when components go NRFND.
- **Appraisal**: Use SENTINEL's scenario analysis in pitch deck/website. Shows founders thought about resilience.

### Portfolio Management
- **Risk scoring**: Know which companies have fragile supply chains before they're in crisis.
- **Scenario planning**: Model what happens to your portfolio in a Taiwan scenario, sanctions event, or demand shock.
- **Capital allocation**: De-risk high-exposure companies or accelerate funding to those with resilient designs.

### Exit Value
- Acquirers care about supply chain resilience (especially in defense/aerospace).
- Show that you've modeled risk and have a mitigation plan. Increases valuation.

---

## The Differentiation

### vs. Manual Spreadsheets
- **Spreadsheets**: Hundreds of part numbers. "Is it fine?" No automation.
- **SENTINEL**: Automatic risk scoring. What-if modeling. Portfolio view.

### vs. APIs Alone (Nexar, SiliconExpert)
- **APIs**: "Here's lifecycle data for this part." No aggregation, no scenarios.
- **SENTINEL**: Risk scoring + what-if + portfolio insights.

### vs. Competitors
- No other tool connects component-level risk to portfolio strategy.
- Specifically built for the VC use case (not procurement, not design teams).

---

## How It Works

1. **Upload BOM**: Drag-drop Excel/CSV of bill of materials
2. **Enrich**: SENTINEL pulls lifecycle, supply, geographic data from Nexar / SiliconExpert / Z2Data (your choice)
3. **Score**: Automatic risk calculation across 5 dimensions
4. **Scenario**: Run disruption scenarios (Taiwan, supplier exit, etc.)
5. **Intelligence (optional)**: Ingest public market headlines locally; optional local LLM (e.g. Ollama) explains risk in context with citations—BOM data stays on your machine by default
6. **Export**: Markdown report with findings and recommendations
7. **Monitor**: Re-score quarterly or on-demand

**Time from BOM to risk report**: 10 minutes.

---

## Demo Results (Today)

Three portfolio companies, three different risk profiles:

| Company | Design Type | BOM Risk | Taiwan Scenario | Key Finding |
|---------|------------|----------|-----------------|------------|
| CN0566 | Defense RF Platform | 42/100 (Medium) | 78/100 (Critical) | 5 components have no alternates; redesign needed |
| PLUTO | Software-Defined Radio | 35/100 (Low) | 68/100 (High) | Fewer Taiwan dependencies; shorter redesign cycle |
| Industrial Edge | IoT Compute | 52/100 (Medium) | 71/100 (High) | Different risk: already has obsolete FPGA (XC3S500E) |

**Cross-BOM finding**: All three use the Xilinx Zynq FPGA. Taiwan disruption = portfolio crisis.

---

## Pricing & Roadmap

### MVP (Today)
- ✅ Component risk scoring (Nexar + synthetic data)
- ✅ 5 scenario types (Country, Supplier, Obsolescence, Component removal, Demand spike)
- ✅ Portfolio exposure analysis
- ✅ Export (markdown reports)
- ✅ Local intelligence layer: Tier B/C narrative (optional LLM + rules fallback), public RSS/CSV market events, redacted prompts by default

### Q2 2026 (Next)
- SiliconExpert integration (lifecycle forecasting)
- Z2Data integration (sub-tier supplier mapping)
- GIDEP alerts (counterfeit, obsolescence notices)
- PDF export + branded reports

### H2 2026 (Vision)
- ML obsolescence prediction
- Real-time monitoring + alerts
- PLM/ERP integration (PTC Windchill, SAP)
- Multi-tenancy for larger investors

---

## Pricing Model (TBD — Options)

- **Per-BOM**: $500–2K per analysis
- **Annual Subscription**: $10K–50K depending on # of BOMs
- **API Access**: Pay-as-you-go for programmatic access

*Negotiate based on pilot success.*

---

## Next Steps

1. **Pilot**: Let us analyze one of your portfolio companies' BOMs (real data, real Nexar enrichment)
2. **Feedback**: Tell us what worked, what's missing for your workflow
3. **Integration**: Propose integrating SENTINEL into your diligence process
4. **Expansion**: Scale to full portfolio (10–50 companies) and ongoing monitoring

---

## Contact

**Scott [Last Name]**  
[Email] | [Phone]  
Chief Technology Officer, [Company]

**Let's talk about supply chain resilience in your portfolio. When is good?**

---

## Appendix: Sample Risk Factors

**Component: XC7Z010-1CLG225C (Xilinx Zynq FPGA)**

| Dimension | Score | Reason |
|-----------|-------|--------|
| Lifecycle | 60 | NRFND (Not Recommended for New Designs); 2.5 years until EOLD |
| Supply | 85 | Very limited inventory (3,800 units); long lead time (84 days) |
| Geographic | 100 | Taiwan-only manufacturing; no multi-site option |
| Supplier | 85 | Single manufacturer (Xilinx/AMD); no alternates identified |
| Regulatory | 5 | RoHS/REACH compliant; no issues |
| **Composite** | **78** | **Critical Risk** |

**Recommendation**: Evaluate Zynq UltraScale+ FPGA family as migration path, or begin qualification of Lattice iCE40 / Actel FPGA alternates. Initiate lifetime buy negotiation with distributor. Plan 6-month redesign effort.

---

**SENTINEL: Risk Intelligence Before the Crisis Hits.**
