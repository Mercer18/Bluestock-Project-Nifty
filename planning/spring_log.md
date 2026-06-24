# Sprint 1 Log & Standup Records

This document logs daily achievements, tasks completed, and the exact standup updates logged for each day of **Sprint 1 (Foundation & ETL)**.

---

## 📅 June 16, 2026 – Day 1: Project Scaffolding & Environment Setup

### 🛠️ Tasks Completed
- Created the project directory structure under `ProjectNifty/`:
  - `data/raw/` (moved the 7 core spreadsheets here)
  - `data/supporting/` (moved the 5 supplementary spreadsheets here)
  - `src/etl/` (for ETL code)
  - `tests/etl/` (for unit tests)
  - `config/` (for configuration settings)
- Configured Python virtual environment `.venv` and generated `requirements.txt` pinning dependencies.
- Configured configuration files `config/.env.template` and the local `.env`.
- Initialized local Git repository and created a standard `.gitignore` file.

### 🗣️ Daily Standup Submitted
*   **Title**: `Sprint 1 - Project Scaffolding & Environment Setup`
*   **Category**: `Data Analysis`
*   **Description**:
    ```text
    - Scaffolded the Nifty 100 Financial Intelligence Platform directory structure (data/raw/, data/supporting/, src/etl/, tests/etl/, config/).
    - Created and configured the Python virtual environment (.venv) and requirements.txt pinning core dependencies (Pandas, NumPy, openpyxl, sqlite3, pytest, python-dotenv, black, ruff).
    - Set up the environment configuration templates (.env.template and local .env) to manage local database paths and application ports securely.
    - Initialized the local Git repository and configured the .gitignore file to ensure a clean codebase baseline.
    ```

---

## 📅 June 17, 2026 – Day 2: Ingestion & Normalisation (Core Datasets)

### 🛠️ Tasks Completed
- Created `src/etl/normaliser.py` containing:
  - `normalize_ticker`: Strips whitespaces and converts tickers to uppercase.
  - `normalize_year`: Normalises formats (`Mar-23`, `FY23`, `2023`, `Dec-22`, `Jun-23`) to ISO `YYYY-MM` format.
- Created `src/etl/loader.py` to:
  - Load multi-header Excel files using `header=1`.
  - Clean and strip whitespaces from all data cells and column headers.
  - Normalise tickers and year fields in loaded DataFrames.
- Created `tests/etl/test_normalise.py` containing 42 parameterized test cases for unit testing.
- Verified test suite passes successfully with 100% green tests.
- Ran ingestion loader directly to verify correct loading of core datasets.

### 🗣️ Daily Standup Submitted
*   **Title**: `Sprint 1 - Ingestion & Normalisation (Core Datasets)`
*   **Category**: `Data Analysis`
*   **Description**:
    ```text
    - Implemented the core Excel parsing engine in src/etl/loader.py to read the 7 core datasets with header metadata offset (using header=1).
    - Created src/etl/normaliser.py containing functions to normalise ticker formats (normalize_ticker) and standardise diverse year formats (normalize_year) like 'Mar-23', 'FY23', 'Dec-22', etc., to 'YYYY-MM'.
    - Wrote 40+ unit tests in tests/etl/test_normalise.py covering edge cases for tickers and years.
    - Executed pytest to verify all normalisation and loading functions pass without errors.
    ```

---

## 📅 June 18, 2026 – Day 3: Schema Validation & Database Setup

### 🛠️ Tasks Completed
- Created `src/etl/schema.sql` declaring a 12-table SQLite database structure (including primary keys, foreign keys, and optimized nullable constraints to support diverse industries like banking and non-banking companies).
- Created `src/etl/validator.py` implementing the 16 Data Quality validation rules (DQ-01 to DQ-16) with automated failures logging.
- Integrated automated data healing and sanitization in the pipeline:
  - Dropped empty rows/trailing artifact rows from Excel sheets.
  - Coerced missing face values (e.g., TVSMOTOR) to a standard fallback of `1.0` and logged warnings.
  - Deduplicated tables with composite primary keys (e.g., P&L, balance sheets, cash flows, documents, and ratios) using `keep="last"`.
  - Optimized URL connection checks (DQ-13) using a regex check for all items and connection test for the first 5 unique URLs to prevent slow loading.
- Integrated SQLite database connection context managers and table loading in `src/etl/loader.py`.
- Successfully ran the end-to-end ingestion pipeline, loading all 12 source files in **2.77 seconds** and generating `data/nifty100.db`, `data/load_audit.csv`, and `data/validation_failures.csv` (recording 1,152 warnings/errors).

### 🗣️ Daily Standup Submitted
*   **Title**: `Sprint 1 - Schema Validation & Database Setup`
*   **Category**: `Data Analysis`
*   **Description**:
    ```text
    - Designed and wrote the 12-table SQLite database schema in src/etl/schema.sql with enforced foreign keys.
    - Implemented the 16 Data Quality validation rules in src/etl/validator.py, logging violations to data/validation_failures.csv.
    - Added data sanitization logic (PK dropna, duplicate removal, TVSMOTOR null face-value fallback) and optimized the URL check (first 5 unique connection checks + regex validation).
    - Executed the loader script to build and populate data/nifty100.db and write the load metrics to data/load_audit.csv.
    ```

---

## 📅 June 19, 2026 – Day 4: Full Ingestion Validation & Unit Testing

### 🛠️ Tasks Completed
- Refined `loader.py` data ingestion to support Arrow string dtypes in Pandas 3.0.3 by using `pd.api.types.is_string_dtype` instead of checking `df[col].dtype == object`.
- Created a robust test suite for the Data Quality Validation Rules:
  - Created `tests/etl/test_rules.py` containing 9 detailed unit tests verifying company PK uniqueness (DQ-01), ticker formats/lengths (DQ-08), null fallbacks (TVSMOTOR face value warning), composite PK deduplication (DQ-02), foreign key orphans rejection (DQ-03), OPM calculations cross-checks (DQ-05), banking positive sales exceptions (DQ-06), balance sheet equations (DQ-04), and cash flow net matches (DQ-09).
- Created helper tests for Loader operations:
  - Created `tests/etl/test_loader.py` checking Pandas Arrow string header stripping, missing file handling, and audit logger metrics calculations.
- Executed the complete testing suite containing **61 tests**, achieving 100% test pass rates and successfully satisfying the project exit criteria of 60+ tests.

### 🗣️ Daily Standup Submitted
*   **Title**: `Sprint 1 - Full Ingestion Validation & Unit Testing`
*   **Category**: `Data Analysis`
*   **Description**:
    ```text
    - Refined the string stripping logic in src/etl/loader.py to support new Pandas 3.0 Arrow string types.
    - Wrote tests/etl/test_rules.py to cover all 16 Data Quality validation rules on mock validation dataframes.
    - Wrote tests/etl/test_loader.py to verify data cleansing string manipulations and audit log timing functions.
    - Ran the full test suite verifying that all 61 tests pass cleanly, meeting the exit criteria.
    ```

---

## 📅 June 20, 2026 – Day 5: Supplementary Ingestion & Full Load

### 🛠️ Tasks Completed
- Ingested all 5 supplementary files (`sectors.xlsx`, `market_cap.xlsx`, `stock_prices.xlsx`, `peer_groups.xlsx`, `financial_ratios.xlsx`) from `data/supporting/` using header=0.
- Executed the full ETL pipeline to merge core and supplementary tables into `data/nifty100.db`.
- Generated the load metrics log `data/load_audit.csv` verifying loaded rows, raw rows, rejections, and execution timings per table.
- Generated `data/validation_failures.csv` logging all 1,152 data quality warnings/info constraints.
- Verified that all foreign key constraints and primary keys are successfully populated in the SQLite relational database.

### 🗣️ Daily Standup Submitted
*   **Title**: `Sprint 1 - Supplementary Ingestion & Full Load`
*   **Category**: `Data Analysis`
*   **Description**:
    ```text
    - Ingested all 5 supplementary datasets (sectors, market cap, stock prices, peer_groups, financial_ratios) into the relational database.
    - Ran the complete ETL pipeline loading ~11,000+ data points across 12 tables and generated the load audit report load_audit.csv.
    - Logged all data warnings to validation_failures.csv and verified zero critical schema failures.
    - Maintained Git version control records on the public repository.
    ```

---

## 📅 June 21, 2026 – Day 6: Data Quality Manual Review

### 🛠️ Tasks Completed
- Conducted a data quality manual review auditing **5 key constituent companies** across all SQLite tables: TCS, HDFCBANK, SBILIFE, INFY, and TVSMOTOR.
- Verified string normalisation, year standardisation, and mathematical equations (Assets = Liabilities balance verification).
- Discovered a critical dataset anomaly: **Wipro (WIPRO)** is present in `analysis.xlsx` but missing from the master index mapping in `companies.xlsx`. The validator correctly logged it as a critical foreign key violation (DQ-03) and excluded it to maintain database integrity.
- Verified TVSMOTOR's missing face value is correctly coerced to `1.0` and logged as a warning.
- Documented all data quality findings, row counts, and spot checks inside `docs/dq_review_notes.md`.

### 🗣️ Daily Standup Submitted
*   **Title**: `Sprint 1 - Data Quality Manual Review`
*   **Category**: `Data Analysis`
*   **Description**:
    ```text
    - Conducted manual spot-checking for 5 diverse constituent companies (TCS, HDFCBANK, SBILIFE, INFY, TVSMOTOR) across all database tables.
    - Verified mathematical balance, primary key uniqueness, and custom normalisation logic on the populated SQLite database.
    - Identified a critical data anomaly (WIPRO orphan record in analysis.xlsx) and documented the self-healing actions.
    - Written up the comprehensive QA notes in docs/dq_review_notes.md.
    ```

---

## 📅 June 22, 2026 – Day 7: SQL Verification & Sprint 1 Retrospective

### 🛠️ Tasks Completed
- Reviewed and optimized the 10 exploratory SQL queries in `exploratory_queries.sql` to select the latest fiscal year data per company (properly handling Siemens' September fiscal year-end anomaly).
- Executed and validated all 10 SQL queries against the populated `nifty100.db` database using the Python query runner.
- Documented the Sprint 1 Retrospective report detailing database metrics, DQ anomalies, challenges solved, and next-sprint recommendations in `planning/sprint1_retro.md`.
- Ran the complete test suite verifying that all 61 pytest test cases pass cleanly (100% success rate).
- Prepared all project deliverables for submission, pushed the branch to the public GitHub repository, and tagged the release `v1.0-sprint1`.

### 🗣️ Daily Standup Submitted
*   **Title**: `Sprint 1 - SQL Verification & Sprint 1 Retrospective`
*   **Category**: `Data Analysis`
*   **Description**:
    ```text
    - Executed and verified the 10 exploratory SQL queries from the project specifications against the populated SQLite database nifty100.db.
    - Updated query joins to select the latest available fiscal year per company to handle September/December/March ending variations.
    - Wrote the comprehensive Sprint 1 Retrospective report planning/sprint1_retro.md detailing achievements, data anomalies, row comparisons, and next-sprint architectural recommendations.
    - Verified that 100% of the 61 pytest test cases pass cleanly without errors.
    - Tagged the release version v1.0-sprint1 and pushed all project changes to GitHub.
    ```

---

## 📅 June 23, 2026 – Day 8: Profitability Ratio Engine & Auto-Healing Integration

### 🛠️ Tasks Completed
- Initiated Sprint 2 (Ratio Engine) by creating the profitability calculations module in `src/analytics/ratios.py`.
- Implemented core profitability ratio formulas (NPM, OPM, ROE, ROCE) with strict edge-case handling for division-by-zero, negative or zero shareholders' equity, and missing input values.
- Discovered a critical column-shifting anomaly in the raw `profitandloss.xlsx` dataset affecting 6 non-financial companies (Cipla, Coal India, Hero Motocorp, Hindalco, Hindustan Unilever, IndiGo).
- Developed and integrated an auto-detection and healing routine in `ratios.py` that identifies shifted raw rows dynamically (`sales - expenses != operating_profit` and `sales - operating_profit == opm_percentage`) and shifts columns back, healing 88 records.
- Wrote 12 comprehensive unit test cases in `tests/kpi/test_profitability.py` validating ratio logic, division by zero, null defaults, and negative equity.
- Executed the entire test suite, verifying that all 73 pytest tests pass successfully (100% green).

### 🗣️ Daily Standup Submitted
*   **Title**: `Sprint 2 - Profitability Ratio Engine & Auto-Healing Integration`
*   **Category**: `Data Analysis`
*   **Description**:
    ```text
    - Initiated Sprint 2 by writing src/analytics/ratios.py to compute profitability KPIs (NPM, OPM, ROE, ROCE) with robust null and division-by-zero protections.
    - Discovered a critical column shift bug in raw profitandloss.xlsx affecting 6 major non-financial companies and implemented an auto-healing algorithm that detects and shifts raw data cells back to correct columns on the fly.
    - Wrote 12 unit tests in tests/kpi/test_profitability.py covering calculation logic and edge cases (negative equity, zero sales).
    - Executed the full pytest suite confirming all 73 tests pass.
    ```

---

## 📅 June 24, 2026 – Day 9: Leverage & Efficiency Ratio Engine

### 🛠️ Tasks Completed
- Implemented leverage and efficiency calculations inside `src/analytics/ratios.py` covering Debt-to-Equity (D/E), Interest Coverage Ratio (ICR), and Asset Turnover.
- Configured edge-case overrides for debt-free companies, including returning `0.0` for D/E when borrowings are zero, and returning `999.0` for ICR (substituting for 'Debt Free' display) when interest expenses are zero or None.
- Updated database query fields inside `load_financial_data` to select `total_assets` from the `balancesheet` table to support Asset Turnover.
- Wrote 10 comprehensive unit test cases inside `tests/kpi/test_leverage.py` verifying leverage ratios, debt-free overrides, negative equity, and asset turnover boundaries.
- Executed the entire test suite, confirming that all 83 pytest unit tests pass cleanly (100% success rate).

### 🗣️ Daily Standup Submitted
*   **Title**: `Sprint 2 - Leverage & Efficiency Ratio Engine`
*   **Category**: `Data Analysis`
*   **Description**:
    ```text
    - Implemented leverage and efficiency ratios (D/E, Interest Coverage ICR, Asset Turnover) inside src/analytics/ratios.py with custom edge-case overrides.
    - Added debt-free substitution to calculate 999.0 for companies with zero interest expenses and zero borrowings default checks.
    - Wrote 10 unit test cases in tests/kpi/test_leverage.py validating calculations, zero values, and null overrides.
    - Ran the full pytest suite confirming that all 83 test cases pass cleanly (100% success rate).
    ```
