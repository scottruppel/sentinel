# SENTINEL Demo — Quick Start Guide

## Pre-Demo Checklist (Run This 1 Hour Before)

```bash
# 1. Start the stack
cd /home/scott/sentinel
docker-compose down && docker-compose up -d  # Fresh DB
sleep 5

# 2. Backend
cd backend
pip install -e ".[dev]"  # if needed
alembic upgrade head
uvicorn sentinel.main:app --reload --port 8001 &

# 3. Seed data
python -m scripts.seed_demo_bom
# Should see:
#   enrichment_complete for CN0566
#   pluto_bom_created
#   industrial_edge_bom_created
#   scenario_seeded x 3

# 4. Frontend
cd ../frontend
npm install  # if needed
npm run dev
# Should be running on http://localhost:5173

# 5. API health check
curl -s http://localhost:8001/docs  # Should load Swagger UI
curl -s http://localhost:8001/api/health  # Should return OK
```

**Wait for all services to be healthy before proceeding.**

---

## Demo Sequence (20 Minutes)

### Stage 1: Dashboard Overview (2 min)

1. **Open browser**: `http://localhost:5173`
2. **Take screenshot**: Dashboard showing 3 BOMs with aggregate stats
   - Total components tracked
   - Overall risk distribution (pie chart)
   - Recent activity
3. **Narrate**: "Three portfolio companies, all hardware-based. Our job is to assess supply chain risk."

### Stage 2: CN0566 Exploration (5 min)

1. **Click on CN0566** in the BOM list (left sidebar)
2. **Wait for component table to load**
3. **Show the heatmap** (should be color-coded by risk):
   - Green (low) → Yellow (medium) → Red (high/critical)
   - XC7Z010 should be RED (high risk)
4. **Click on XC7Z010 component**:
   - Should show detail panel with:
     - Risk breakdown (5-axis radar chart)
     - Lifecycle status: NRFND
     - Geographic: Taiwan
     - Lead time: 84 days
     - Risk factors list
     - Recommendation: "Consider alternative FPGA or lifetime buy"
5. **Narrate**: "This is the brain of their product. It's on borrowed time — 2.5 years until end of life, single manufacturer, manufactured in Taiwan only, 84-day lead time."

### Stage 3: What-If Scenario (6 min)

1. **Click "Scenarios"** or "Run Scenario" button
2. **Select scenario type**: "Country Disruption"
3. **Configure**:
   - Country: "Taiwan"
   - Severity: "total_loss"
   - Affected BOMs: Select "CN0566"
4. **Click "Run Scenario"** (should take 5–10 sec)
5. **Show results**:
   - **Before**: Overall risk 42/100
   - **After**: Overall risk 78/100
   - **Delta**: +36 points (moved to Critical)
   - **Affected components**: 12 of 60 (20%)
   - **Components with no alternate**: 5
6. **Click on impacted component** (e.g., Zynq):
   - Should show:
     - Baseline score: 25
     - Scenario score: 100
     - Delta: +75
     - Reason: "Taiwan manufactures 100% of supply; no alternates available"
7. **Narrate**: "Their risk quintupled. They've got 4–8 months to redesign, assuming they can even find alternates. At this point, they're probably looking at 3–6 months of engineering work and a 6-month market delay."

### Stage 4: Cross-BOM Comparison (4 min)

1. **Close the scenario detail panel**
2. **Return to Dashboard or BOM List**
3. **Run the same Taiwan scenario for PLUTO and Industrial Edge BOMs** (or pre-run these):
   - **CN0566**: +36 risk delta, 12 affected, HIGH redesign effort
   - **PLUTO**: +33 risk delta, 8 affected, MEDIUM redesign effort
   - **Industrial Edge**: +19 risk delta, 5 affected, LOW redesign effort (but has obsolete FPGA issue)
4. **Show comparison table or side-by-side heatmaps**
5. **Narrate**: "Same crisis, but different impact across the portfolio. Company A needs 6 months to pivot. Company B needs 3. Company C is already dead (obsolete FPGA). If you're the VC, you now know to de-prioritize Company C and accelerate funding to A and B."

### Stage 5: Cross-BOM Exposure (2 min)

1. **Click "Cross-BOM Exposure"** or similar view
2. **Show which MPNs appear in multiple BOMs**:
   - XC7Z010 (all 3 BOMs)
   - AD9363 (CN0566 + PLUTO)
   - Memory, passives, voltage regulators
3. **Narrate**: "This is portfolio risk. If the Zynq supply dries up, it hits all three companies. That's your hidden correlation. Most VCs don't see this until it's too late."

### Stage 6: Export & Close (1 min)

1. **Click "Export Report"** on CN0566
2. **Show markdown report** with:
   - BOM summary
   - Top 10 at-risk components
   - Recommendations per component
3. **Narrate**: "You can email this to the company's engineering team or your investment committee. Clear, actionable intelligence."

---

## Keyboard Shortcuts & Tips

- **Tab navigation**: Use arrow keys to scroll through BOM list
- **Search**: Many tables have search/filter; use them to highlight a specific component
- **Zoom**: Browser zoom (Cmd+/-) makes the heatmap easier to see
- **Export**: PDF export should work; if not, fallback to markdown
- **Performance**: If the UI feels slow with 150+ components, refresh the page and re-select the BOM

---

## Fallback Scenarios (If Something Breaks)

### UI doesn't load
```bash
# Check frontend
curl -s http://localhost:5173
# If blank, restart frontend:
cd frontend && npm run dev
```

### API errors
```bash
# Check backend health
curl -s http://localhost:8001/health
# If down, restart:
uvicorn sentinel.main:app --reload --port 8001
```

### No data in UI
```bash
# Re-seed
python -m scripts.seed_demo_bom
# If seed fails, nuke DB and restart:
docker-compose down -v
docker-compose up -d
# Then re-seed
```

### Scenario doesn't run
- Backend might be slow; wait 10 sec and retry
- Check browser console for errors (Cmd+Option+I → Console tab)
- If stuck, refresh page

---

## Demo Narrative Cue Cards

**[During Dashboard overview]**
"We've got three companies: defense RF platform, software-defined radio, and industrial IoT. Different categories, all hardware-centric, all vulnerable to supply chain disruption."

**[During CN0566 deep dive]**
"This FPGA is the linchpin. Single manufacturer, single country, 84-day lead time. If Xilinx sneezes, the whole product line can't scale."

**[During Taiwan scenario]**
"Watch the risk score. It's not a linear relationship — when you lose Taiwan, you lose not just availability but also alternates and manufacturing optionality. The risk multiplies."

**[During cross-BOM comparison]**
"Same geopolitical crisis, three different company impacts. This is why portfolio-level supply chain analysis matters. You can't just look at each company in isolation."

**[Closing]**
"SENTINEL gives you the visibility to make smarter bets on supply chain resilience. Instead of asking 'Is it fine?' and hoping, you ask 'What's the exposure?' and plan accordingly."

---

## Post-Demo Follow-Up

**If VC is interested**:
1. Offer to analyze one of their portfolio companies' BOMs (if they share it)
2. Discuss pricing model and integration into diligence process
3. Talk about roadmap (Z2Data sub-tier supplier mapping, GIDEP alerts, etc.)

**If VC wants to see more**:
1. Show real Nexar API data (vs. synthetic) if you've got live keys configured
2. Show scenario library (pre-built crisis playbooks)
3. Demo PDF export

---

## System Requirements During Demo

- **Bandwidth**: None required (fully local)
- **Browser**: Chrome/Safari/Firefox (tested on Chrome)
- **Hardware**: Works fine on laptop; 8GB RAM recommended
- **Internet**: Only for initial Nexar API calls; scenarios are all local

---

## Timing

- **Setup time**: 5–10 min (docker, seed data)
- **Demo duration**: 15–20 min (comfortable pace)
- **Q&A**: 10–15 min (allow for interruptions)

**Total: 40–45 min for a full session**

---

## Feedback Capture

During/after demo, note:
1. Which feature resonated most? (Scenarios? Cross-BOM view? Risk scoring?)
2. What was confusing or unclear?
3. What's missing for their use case?
4. Would they pay for this? At what price point?

Good luck! 🚀
