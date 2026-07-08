# Nifty 100 Financial Intelligence Platform

This repository houses the production-grade data foundation, ETL ingestion pipeline, and financial ratio analysis engine for the **Nifty 100 Financial Intelligence Platform**. The platform processes, normalises, and validates financial statement data (~11,000+ data points across P&L, Balance Sheet, Cash Flow, and supplementary datasets) for 92 Nifty 100 index constituent companies, generating advanced financial metrics and diagnostic analysis.

---

## 🚀 Features

### Sprint 1: Foundation & ETL (Completed)
- **Data Ingestion Engine**: Automated ingestion of 7 core and 5 supplementary Excel spreadsheets.
- **Data Quality Validator**: Strict validation of 16 custom data quality rules (DQ-01 to DQ-16), logging warnings and error details to a structured CSV.
- **Relational Storage**: Initialized SQLite database (`data/nifty100.db`) with 12 structured tables enforcing relational integrity and foreign keys.
- **Data Normalisation**: Standardized company tickers and year identifiers (mapping diverse date strings to YYYY-MM format).

### Sprint 2: Financial Ratio Engine (Completed)
- **Advanced KPI Calculations**: Computes profitability (NPM, OPM, ROE, ROCE, ROA), leverage & efficiency (D/E, ICR, Asset Turnover, Net Debt), growth (CAGR for Sales, PAT, and EPS), and cash flow KPIs (FCF, CFO Quality, CapEx Intensity, FCF Conversion).
- **Relational Database Orchestrator**: Automatically populates the `financial_ratios` table in SQLite with **1,155 records** containing all 17 computed KPIs and leverage/ICR flags.
- **Capital Allocation Matrix**: Sign-based 8-pattern classifier mapping sign combinations of CFO, CFI, and CFF to strategic corporate states (e.g. *Reinvestor*, *Shareholder Returns*, *Liquidating Assets*, *Distress Signal*, *Growth Funded by Debt*, *Cash Accumulator*, *Pre-Revenue*, *Mixed*).
- **Winsorised Composite Quality Score**: Calculates a relative performance rating ($0.30 \times \text{ROE} + 0.25 \times \text{FCF} + 0.25 \times \text{ROCE} + 0.20 \times \text{D/E}$) using P10/P90 winsorisation.
- **Automated Column-Shift Auto-Healer**: Dynamically detects and heals **88 shifted records** in raw spreadsheet loads on the fly.
- **Cross-Validation Anomaly Log**: Compares computed values against master pre-computed indices, logging and categorizing deviations ($>5\%$) into `output/ratio_edge_cases.log` (categories: `data source issue`, `formula discrepancy`, `version difference`).

### Sprint 3: Screener & Peer Comparison Engine (In Progress)
- **Dynamic Filter Engine**: Filters companies dynamically across 15 financial metrics based on analyst-defined thresholds in `config/screener_config.yaml`.
- **6 Preset Screeners**: Implements and validates Quality Compounder, Value Pick, Growth Accelerator, Dividend Champion, Debt-Free Blue Chip, and Turnaround Watch presets.
- **Winsorised Sector-Relative Quality Rating**: Calculates per-sector relative composite ratings (Profitability 35%, Cash Quality 30%, Growth 20%, Leverage 15%).
- **Screener Output**: Generates `output/screener_output.xlsx` containing 6 sheets, color-coded with green/red cells for active thresholds.

---

## 📁 Repository Structure
```text
ProjectNifty/
├── config/
│   └── .env.template          # Environment configuration template
├── src/
│   ├── etl/
│   │   ├── loader.py          # Database loading engine and insert pipeline
│   │   ├── normaliser.py      # Year and ticker formatting functions
│   │   ├── validator.py       # Data Quality rules check engine
│   │   └── schema.sql         # Relational database DDL schema
│   └── analytics/
│       ├── ratios.py          # Profitability, leverage, and efficiency ratio calculator
│       ├── cagr.py            # CAGR engine with 6 edge case handlers
│       ├── cashflow_kpis.py   # CFO Quality, CapEx Intensity, and Capital Allocation
│       └── sector_roce.py     # Sector-relative ROCE and NBFC analysis
├── tests/
│   ├── etl/
│   │   ├── test_loader.py     # Loader & cleaning unit tests
│   │   ├── test_normalise.py  # Year/ticker normalisation unit tests
│   │   └── test_rules.py      # 16 Data Quality rules unit tests
│   └── kpi/
│       ├── test_cagr.py       # 6-edge case CAGR unit tests
│       ├── test_cashflow.py   # CFO Quality and allocation sign unit tests
│       ├── test_leverage.py   # Leverage, ICR labels, and Net Debt unit tests
│       ├── test_profitability.py # Profitability and ROA unit tests
│       └── test_orchestration.py # Integration count and sector ROCE tests
├── planning/                  # Sprint logs and roadmap plans
│   ├── spring_log.md          # Daily standup logs
│   ├── sprint_1_master_plan.md
│   └── sprint2_retro.md       # Sprint 2 final retrospective report
├── output/                    # Sprint 2 generated deliverables
│   ├── capital_allocation.csv  # 8-pattern classification labels
│   └── ratio_edge_cases.log   # Detailed anomaly and turnaround logs
├── Makefile                   # Utility targets (load, ratios, test, clean)
├── requirements.txt           # Python dependencies file
└── README.md                  # Project overview and setup guide
```

---

## 🛠️ Installation & Setup

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/Mercer18/Bluestock-Project-Nifty.git
    cd Bluestock-Project-Nifty
    ```

2.  **Set Up Virtual Environment**:
    ```bash
    python -m venv .venv
    # On Windows PowerShell:
    .venv\Scripts\Activate.ps1
    # On macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Install Pinned Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Copy `config/.env.template` to a local `.env` file:
    ```bash
    copy config\.env.template .env
    ```

---

## 💻 Usage

### Run Ingestion Pipeline (Sprint 1)
To clean, normalise, validate, and load all datasets into the SQLite database:
```bash
python src/etl/loader.py
# Or using the Makefile:
make load
```

### Run Financial Ratio Engine (Sprint 2)
To calculate and populate all ratios, CAGR values, composite scores, and flags into the database:
```bash
python src/analytics/ratios.py
# Or using the Makefile:
make ratios
```
This updates `data/nifty100.db` and writes:
- `output/capital_allocation.csv` (Capital Allocation patterns)
- `output/ratio_edge_cases.log` (All anomalies and CAGR turnaround flags)

### Run Preset Screeners & Exports (Sprint 3)
To execute filters, calculate composite scores, and export `output/screener_output.xlsx`:
```bash
python src/screener/engine.py
# Or using the Makefile:
make screener
```

### Run Unit Tests
To execute all 106 unit and integration tests:
```bash
pytest tests/
# Or using the Makefile:
make test
```

---

## 🎯 Day-by-Day Sprint Log
Refer to the **[Daily Sprint Log](file:///x:/CODING/PROJECTS/InternshipWork/Bluestock/ProjectNifty/planning/spring_log.md)** for detailed standup descriptions and task completions.
