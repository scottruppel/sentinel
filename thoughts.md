start with user BOM
break into 3 categories
    # major redesign (MCUs - 5 components) with complexity scoring and timeline
    # suitable sub, but new FAB spin 
    # resistors/capacitors - many suitable subs on market - low risk

    Capacity planning
        500 unit scenario
        1000 unit scenario
        2000 unit scenario

Risk x build plan = forecast to pull trigger
interogate market availability and BOM costs - 

lifecycle - obsole/lifetime buys

Ability to create a BOM and expected price

running scenarios, don't have to think about it, highlight with timeline for action
GM Mack Technologies

---

## Posterboard: BOM Billing (ideas & future capabilities)

_Not product commitments — scratchpad for pricing, availability, and risk intersecting with commercial BOM views._

### Core questions
- What is **expected cost** for a BOM at **today’s** distributor pricing vs **risk-adjusted** cost (premium for sole-source, LTB, or long lead time)?
- How do **build quantity** (500 / 1k / 2k) and **yield/scrap** assumptions change line and total cost?
- Where does **lifecycle** (LTP, NRND, LTB windows) force **inventory buys** that don’t show up in “spot” pricing?

### Data inputs (conceptual)
- **Unit pricing** per MPN from distributor APIs or internal contracts (Mouser, Digi-Key, etc.); min/mult, price breaks, NCNR flags.
- **Stock / lead time** per source (or consolidated best-offer) — tie to enrichment and risk signals.
- **Internal** burden: overhead, NRE amortization, qualification cost spread across build volume.

### Calculations & views
- **Line extended price** = qty × effective unit price (respect MOQ, price breaks).
- **BOM rollup** with **availability-weighted** scenarios: “if primary source stocks out, next-best offer” (requires rules for tie-break).
- **Risk multiplier or surcharge model** (optional): e.g. sole-source → add virtual $ or flag for procurement; align with composite risk score without double-counting.
- **LTB / last-time-buy** mode: model **inventory cash-out** before EOL vs **redesign to alternate** NRE — compare total cost paths over a horizon.

### Automation & agents (ties to V2)
- Scheduled **digest**: top spend lines, top risk × spend, lines crossing price or lead-time thresholds.
- **No invented prices**: LLM narrates from Sentinel/computed JSON; numbers come from APIs or stored snapshots.

### Integrations (future)
- ERP / PLM push: **costed BOM** export, change deltas.
- Contract manufacturer quote packages: frozen BOM revision + assumed volumes + noted alternates.

### Open design choices
- **Snapshot vs live**: store price snapshots at enrichment time for auditability vs always-live calls (rate limits, volatility).
- **Multi-currency** and FX handling.
- **Approved vendor list** (AVL) constraints overriding cheapest price.
