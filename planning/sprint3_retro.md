# Sprint 3 Retrospective — Screener & Peer Comparison Engine

This document provides a summary of the technical achievements, design decisions, mathematical formulas, and testing validation for **Sprint 3 (Days 15–21)**.

---

## 🚀 Key Achievements

1. **Screener Filter Engine & Presets**:
   - Developed a configuration-driven filter engine (`src/screener/engine.py`) loading analyst-editable criteria from `config/screener_config.yaml`.
   - Coded 15 modular metric filters.
   - Handled banking/insurance structural differences (exempting the `Financials` sector from standard leverage criteria) and treated `"Debt Free"` interest coverage as infinity.
   - Successfully validated all 6 preset screeners (Quality Compounder, Value Pick, Growth Accelerator, Dividend Champion, Debt-Free Blue Chip, and Turnaround Watch) on the Nifty 100 universe.

2. **Sector-Relative Winsorised Quality Rating**:
   - Implemented a relative performance rating on a 0–100 scale:
     - **Profitability (35%)**: ROE (15%), ROCE (10%), NPM (10%)
     - **Cash Quality (30%)**: FCF CAGR 5yr (15%), CFO/PAT ratio (10%), FCF > 0 flag (5%)
     - **Growth (20%)**: Revenue CAGR 5yr (10%), PAT CAGR 5yr (10%)
     - **Leverage (15%)**: D/E score (10%), ICR score (5%)
   - Extrapolated absolute leverage curves linearly:
     - D/E score: $0 \to 100$, $0.5 \to 85$, $1 \to 70$, $2 \to 50$, $>5 \to 0$
     - ICR score: $>10 \to 100$, $5 \to 75$, $3 \to 50$, $<1.5 \to 0$
   - Applied P10/P90 winsorisation to relative metrics and scaled 0–100 within each `broad_sector` to reflect performance vs. sector peers.

3. **Peer Percentile Rankings**:
   - Created the database loader `src/analytics/peer.py` to calculate Excel-matching `PERCENTRANK.INC` percentiles for 10 metrics across all 11 peer groups:
     $$\text{Percentile Rank} = \frac{\text{Rank} - 1}{N - 1}$$
   - Inverted D/E rankings so that lower leverage has a higher percentile.
   - Populated the new SQLite table `peer_percentiles` with **7,060 records** and supported non-mapped fallback strings.

4. **Visualisation and Reporting**:
   - **Radar Charts**: Rendered 8-axis polar radar charts (company polygon filled vs. peer group average dashed outline) for all constituent companies. Exported **91 PNG files** to `reports/radar_charts/`.
   - **Excel Exports**:
     - `screener_output.xlsx` (6 sheets): Sorted by Composite Score descending, cell fill formatting applied (light green for passing thresholds, light red for failing).
     - `peer_comparison.xlsx` (11 sheets): Exported 20 metrics and 10 percentile rankings, featuring percentile color ranges (green/yellow/red), gold benchmark highlights, and peer group medians.

---

## 📈 Quality Assurance & Test Coverage

- Created `tests/kpi/test_screener.py` and `tests/kpi/test_peer.py` to cover all new filters, presets, percent ranks, and database insertions.
- Executed the full test suite showing **114 passed tests** and **0 failures** (100% green).
- Confirmed that the `financial_ratios` table's `"Debt Free"` labels are fully generated and active.

---

## 🎯 Verification Spot-Check

- **Screener Counts (Latest Year 2024-03)**:
  - Quality Compounder: 20 companies
  - Value Pick: 8 companies
  - Growth Accelerator: 19 companies
  - Dividend Champion: 29 companies
  - Debt-Free Blue Chip: 18 companies
  - Turnaround Watch: 31 companies
- **Peer Group Coverage**: `peer_comparison.xlsx` contains exactly 11 sheets covering all 11 peer groups, with medians and benchmark gold highlights fully styled.
