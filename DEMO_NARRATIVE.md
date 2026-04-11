# SENTINEL Demo Narrative — VC Due Diligence Use Case

## Opening (2 min)

**Setup**: Three BOMs loaded in SENTINEL dashboard.

---

## Act 1: The Problem (3 min)

**[Show Dashboard with aggregate risk across 3 BOMs]**

"As a VC, you've invested in three hardware companies in your portfolio. Each one has a product with a bill of materials — anywhere from 30 to 150+ components. Your standard diligence checklist includes: 'Is the supply chain at risk?'

But here's what you usually get:
- A spreadsheet of part numbers
- A shrug from the engineering team: 'We source from distributors. It should be fine.'
- Maybe a name-dropping of Nexar or SiliconExpert, but no actual integration
- No way to quantify risk or compare across companies

So you're betting on supply chain health with almost no visibility."

**[Zoom into CN0566 BOM]**

"Let's take the first company: a defense RF platform with 60 components. Looks like standard stuff — ICs, passives, connectors. Manufactured primarily by Analog Devices and Xilinx."

---

## Act 2: Discovery (5 min)

**[Show Risk Dashboard + Heatmap for CN0566]**

"Now we run SENTINEL's risk scoring. Five dimensions: lifecycle, supply availability, geographic concentration, supplier dependency, and regulatory compliance.

**Overall Risk Score: 42/100 — Medium risk.** But let's dig deeper."

**[Highlight top 5 high-risk components]**

1. **XC7Z010-1CLG225C (Xilinx Zynq FPGA)**: 78/100 risk
   - Status: NRFND (Not Recommended for New Designs)
   - Manufactured in: Taiwan
   - Lead time: 84 days
   - Only 1 distributor has meaningful stock
   - *What does this mean?* Your beamformer's brain is on borrowed time. If Taiwan goes offline — geopolitical crisis, natural disaster — you lose the ability to source this chip. And there's only one manufacturer globally.

2. **HMC637ALP5E (Power Amplifier)**: 72/100 risk
   - Status: Last Time Buy window CLOSED
   - Inventory: 450 units (declining)
   - No qualified alternates
   - *What does this mean?* They missed the window to buy lifetime stock. Now they're scrounging from secondary markets at inflated prices.

3. **ADF4159CCPZ (Synthesizer)**: 65/100 risk
   - Status: NRFND
   - Single source (Analog Devices)
   - *What does this mean?* If ADI exits this product line or faces production constraints, there's no Plan B.

**[Drill into radar chart for one component]**

"See this radar? Lifecycle risk is high (obsolescence). Supply risk is high (low inventory, long lead time). Supplier risk is high (single source). Geographic risk is elevated (Taiwan concentration). Regulatory is clean (RoHS/REACH compliant).

This is the risk profile of a company that's using mature, well-proven components — great for performance, terrible for supply chain resilience."

---

## Act 3: The Differentiator — What-If Analysis (5 min)

**[Run Taiwan Disruption Scenario]**

"Now for the VC angle: **What-if analysis.**

Scenario: Taiwan goes offline due to geopolitical tension. No manufacturing. No exports. Total disruption.

**Before**: CN0566 overall risk = 42/100 (Medium)  
**After**: CN0566 overall risk = 78/100 (Critical)

**Affected components: 12 out of 60** (20% of the BOM)  
**Components with no alternate source: 5**

Here's what happens to their product:
- Zynq FPGA: No replacement path (score: 100)
- 5x passives and support ICs: Can substitute but need redesign (score: 75–90)
- 6x other components: Alternates exist but higher cost/performance tradeoff

**Cost of redesign (engineering + validation): $150K–500K**  
**Time to market delay: 4–8 months**  
**Risk to Series B funding? Critical.**"

**[Switch to PLUTO SDR BOM]**

"Let's compare to their sister company, the PlutoSDR. Same Zynq FPGA, but different overall design philosophy.

**Before**: PlutoSDR overall risk = 35/100 (Low-Medium)  
**After Taiwan scenario**: 68/100 (High)

**Fewer components affected (8 vs. 12)** because they use more multi-source parts and commodity ICs. The redesign effort is lower. Still a crisis, but more manageable."

**[Switch to Industrial Edge IoT Platform]**

"Third portfolio company: IoT edge compute platform. Lower-cost design, intentional geographic diversity.

**Before**: Industrial Edge risk = 52/100 (Medium)  
**After Taiwan**: 71/100 (High)

**Why the different impact?** They're using more Chinese-sourced components (GigaDevice, Espressif) and more distributors, so Taiwan concentration is naturally lower. But they've got a different problem:

One component — the **XC3S500E FPGA** — is already **Obsolete** (score: 100). No Taiwan needed to kill this one. It's dead. And with only 45 units available globally, they have months of runway, not years.

---

## Act 4: The Value Prop (3 min)

**[Return to dashboard, show cross-BOM exposure]**

"Here's where it gets interesting for your portfolio:

**Three companies, but only 10 unique MPNs shared across all three BOMs:**
- Zynq FPGA (all three use it)
- AD9363 Transceiver (two companies)
- Memory, passives, voltage regulators
- STM32 MCU (one uses it, becoming standard in defense/aerospace)

**Cross-BOM exposure risk: 35/100**

If Zynq hits a manufacturing crisis, you've got **cascading risk across 3 portfolio companies simultaneously.** This is a black swan event you weren't tracking.

**What you can do:**
1. **Negotiate early**: Talk to Xilinx about supply agreements before the crisis hits
2. **Diversify**: Fund re-designs to reduce Zynq dependency
3. **Timing**: Understand that Company A needs 4 months to pivot, Company B needs 2. Plan capital deployment accordingly.
4. **Portfolio rebalancing**: If Zynq supply tightens, which company do you de-prioritize? SENTINEL tells you the blast radius."

---

## Act 5: The Ask (2 min)

**[Close with company vision]**

"SENTINEL does three things VCs need:

1. **Risk Quantification**: No more 'probably fine' on supply chain. You get a number, breakdowns by dimension, and human-readable explanations.

2. **Scenario Modeling**: Before you get surprised by a crisis, model it. Taiwan, supplier bankruptcy, demand spike — run it and see the delta.

3. **Portfolio Intelligence**: See which companies are exposed to the same supply chain bottlenecks. This is your hidden portfolio risk.

For the three companies in this demo, SENTINEL surfaces that all three are Taiwan-dependent despite different product categories. No other tool gives you this view across your portfolio.

**The business**: Sell this to VCs, corporate investors, and program managers in defense/aerospace. They're drowning in supply chain risk and have no visibility."

---

## Demo Flow Checklist

- [ ] **0:00** — Dashboard loads with 3 BOMs; show aggregate stats
- [ ] **1:00** — Drill into CN0566, show risk heatmap
- [ ] **2:00** — Click one component (Zynq), show radar chart + risk factors + recommendation
- [ ] **3:30** — Click "Run Scenario", select "Taiwan Disruption"
- [ ] **4:00** — Before/after comparison view; highlight +36 risk delta
- [ ] **4:30** — Show affected components table with recommendations
- [ ] **5:00** — Switch to PlutoSDR BOM, run same scenario, show different impact
- [ ] **5:45** — Switch to Industrial Edge, show Obsolete FPGA issue
- [ ] **6:30** — Cross-BOM exposure view; show Zynq appearing in all 3
- [ ] **7:30** — Export risk report (markdown or PDF) showing findings
- [ ] **8:00** — Close with message: "Now you have visibility before the crisis hits"

---

## Talking Points for Questions

**"Isn't this just pulling data from Nexar/SiliconExpert?"**  
Partially. But the differentiation is:
- **Scoring**: Rule-based risk engine that reflects defense/aerospace priorities
- **Scenarios**: Generic enrichment APIs don't model what-if supply disruptions
- **Portfolio view**: No other tool connects component risk to portfolio strategy

**"How often do you update the data?"**  
Configurable. Every week, monthly, or on-demand. We can set up automated alerts if a component's status crosses a threshold (e.g., Active → NRFND).

**"What about counterfeit parts?"**  
We're integrating GIDEP (Government-Industry Data Exchange Program) counterfeit notices. When GIDEP flags a part, we auto-update and alert.

**"How do you handle sub-tier supplier risk?"**  
Z2Data integration (in progress). They map Tier 2/3 suppliers and manufacturing sites. Enables granular geographic risk scoring.

**"Can you correlate hardware BOM to software supply chain (SBOM)?"**  
Roadmap. A Zynq FPGA has both hardware risk and firmware/bootloader dependencies. Holistic risk requires both.

**"What's your pricing model?"**  
(Per your business strategy — options: SaaS per-BOM, annual subscription, API access tier)

---

## Closing Story

"Supply chain risk isn't new. But the tools are broken. Every company uses email and spreadsheets to track thousands of parts. The VC gets a briefing that says 'supply chain looks good' with no evidence.

SENTINEL changes that. It's the first tool that:
1. Quantifies component-level risk in a way portfolio managers understand
2. Models disruption scenarios without requiring an Excel hack
3. Connects individual company risk to portfolio strategy

Three companies, three different risk profiles, all visible in one dashboard. That's what we're building."

---

## Post-Demo: Next Steps

1. **Immediate**: Show SENTINEL analyzing a real customer BOM (if available)
2. **Follow-up**: Propose a 4-week pilot with one of their portfolio companies
3. **Expansion**: Talk about integration into their diligence process for new investments
