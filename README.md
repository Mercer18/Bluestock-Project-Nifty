# Nifty 100 Financial Intelligence Platform - Sprint 1 (Foundation & ETL)

This repository houses the production-grade data foundation and ETL ingestion pipeline for the **Nifty 100 Financial Intelligence Platform**. The platform processes, normalises, and validates financial statement data (~11,000+ data points across P&L, Balance Sheet, Cash Flow, and supplementary datasets) for 92 Nifty 100 index constituent companies.

---

## 🚀 Features (Sprint 1)
- **Data Ingestion Engine**: Automated ingestion of 7 core and 5 supplementary Excel spreadsheets.
- **Data Quality Validator**: Strict validation of 16 custom data quality rules (DQ-01 to DQ-16), logging warnings and error details to a structured CSV.
- **Relational Storage**: Initialized SQLite database (`data/nifty100.db`) with 12 structured tables enforcing relational integrity and foreign keys.
- **Data Normalisation**: Standardized company tickers and year identifiers (mapping diverse date strings to YYYY-MM format).
- **Unit Testing**: Over 60+ pytest unit tests validating the normaliser logic, data quality rules, and cleaning routines.

---

## 📁 Repository Structure
```text
ProjectNifty/
├── config/
│   └── .env.template          # Environment configuration template
├── src/
│   └── etl/
│       ├── loader.py          # Database loading engine and insert pipeline
│       ├── normaliser.py      # Year and ticker formatting functions
│       ├── validator.py       # Data Quality rules check engine
│       └── schema.sql         # Relational database DDL schema
├── tests/
│   └── etl/
│       ├── test_loader.py     # Loader & cleaning unit tests
│       ├── test_normalise.py  # Year/ticker normalisation unit tests
│       └── test_rules.py      # 16 Data Quality rules unit tests
├── planning/                  # Sprint logs and roadmap plans
│   ├── spring_log.md          # Daily standup logs
│   └── sprint_1_master_plan.md
├── Makefile                   # Utility targets (load, test, clean)
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

### Run Ingestion Pipeline
To clean, normalise, validate, and load all datasets into the SQLite database:
```bash
python src/etl/loader.py
# Or using the Makefile:
make load
```
This generates:
- `data/nifty100.db` (populated database)
- `data/load_audit.csv` (load timings and row metrics)
- `data/validation_failures.csv` (data quality logs)

### Run Unit Tests
To execute all 61 tests and check coverage:
```bash
pytest tests/
# Or using the Makefile:
make test
```

---

## 🎯 Day-by-Day Sprint Log
Refer to the **[Daily Sprint Log](file:///x:/CODING/PROJECTS/InternshipWork/Bluestock/ProjectNifty/planning/spring_log.md)** for detailed standup descriptions and task completions.
