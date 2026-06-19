# Day-Wise Execution Plan: Sprint 1 (June 17 – June 22)

This document details the day-by-day tasks, deliverables, and daily stand-up scripts squeezed into a **6-day sprint** to meet the **June 22, 2026** deadline for Sprint 1 (Foundation & ETL).

---

## 📅 June 17, 2026 (Wednesday) – Day 1: Project Scaffolding & Environment Setup
Establish the development workspace, configure dependencies, set environment variables, and create the directory skeleton.

### 🛠️ Tasks
- Scaffold the project directory structure as specified in Section 19 of the master document (Page 33):
  - `data/raw/` (place the 7 core files here)
  - `data/supporting/` (place the 5 supplementary files here)
  - `src/etl/` (for loader, validator, normaliser, schema DDL)
  - `src/analytics/`, `src/dashboard/`, `src/api/`, `src/reports/` (placeholders/folders)
  - `tests/etl/` (for unit tests)
  - `config/` (for config files)
- Create and activate python virtual environment (`.venv`).
- Create `requirements.txt` pinning dependencies (`pandas>=2.0`, `numpy>=1.24`, `openpyxl>=3.1`, `scipy>=1.11`, `pytest>=7.4`, `black>=24.0`, `ruff>=0.4`, `python-dotenv>=1.0`).
- Configure environment variables: Copy `config/.env.template` to `.env` (define `DB_PATH=data/nifty100.db`, `PORT=8000`, `LOG_LEVEL=INFO`, `SIMULATED_DATA_FLAG=TRUE`).
- Initialize local git repository, set up `.gitignore` (excluding `.venv/`, `.env`, `data/*.db`), and make the initial commit.

### 📦 Deliverables
- `requirements.txt`
- `config/.env.template`
- `.env` (configured locally)
- `.gitignore`
- Clean repository folder structure.

### 🗣️ Daily Stand-Up (End of Day 1)
- **What did I complete yesterday?**
  > "Yesterday, I analyzed the Nifty 100 Project Master Document and mapped out the 6-day execution schedule to hit our June 22nd deadline."
- **What will I complete today?**
  > "Today, I will scaffold the directory structure (`data/`, `src/`, `tests/`, `config/`), build the Python virtual environment, create `requirements.txt` and `.env.template`, configure local `.env` variables, and initialize our Git repository."
- **What is blocking me?**
  > "None. The environment setup completed successfully without packages version conflicts."
- **Anything to share?**
  > "I confirmed that we are using Python 3.13 and Pandas 3.0.3. I have successfully installed `openpyxl` to support reading the Excel files."

---

## 📅 June 18, 2026 (Thursday) – Day 2: Core Ingestion & Normalisation
Build the custom loader to read multi-header Excel sheets and normalise company identifiers and year fields.

### 🛠️ Tasks
- Write `src/etl/normaliser.py` containing:
  - `normalize_ticker(ticker: str) -> str`: strips whitespace and converts ticker to uppercase.
  - `normalize_year(year: str) -> str`: parses diverse year formats (e.g. `Mar-23`, `Mar 23`, `FY23`, `Dec-22`, `Jun-23`) and outputs standardised `YYYY-MM` format (e.g., `2023-03`).
- Write `src/etl/loader.py` with header=1 support to parse the 7 core Excel files from `data/raw/`. Strip leading/trailing whitespaces and normalise all string data.
- Write unit tests in `tests/etl/test_normalise.py` covering at least 20 edge cases for year formats and 15 edge cases for ticker formatting.
- Execute unit tests using `pytest tests/etl/test_normalise.py` and ensure they pass.

### 📦 Deliverables
- `src/etl/normaliser.py`
- `tests/etl/test_normalise.py` (20+ test cases)
- Python execution log showing passing tests.

### 🗣️ Daily Stand-Up (End of Day 2)
- **What did I complete yesterday?**
  > "Yesterday, I completed the project scaffolding, environment variables configuration, and initialized the Git repository."
- **What will I complete today?**
  > "Today, I will write the custom parser in `src/etl/loader.py` to handle the Excel files with metadata header rows (using `header=1`). I'll also implement ticker and year normalisation in `src/etl/normaliser.py` and write the test cases in `tests/etl/test_normalise.py`."
- **What is blocking me?**
  > "None. However, parsing various date formats like `FY23` and `Dec-22` requires careful regex pattern matching. I am mapping out the edge cases using the decision table on Page 37."
- **Anything to share?**
  > "I found that `balancesheet.xlsx` and `profitandloss.xlsx` contain different row counts. This is normal, but we must ensure `company_id` is normalized to uppercase stripped ticker strings across all sheets to guarantee join compatibility."

---

## 📅 June 19, 2026 (Friday) – Day 3: Data Quality Rules & Database Setup
Enforce the 16 data quality rules and design the SQLite schema.

### 🛠️ Tasks
- Write `src/etl/validator.py` implementing the 16 Data Quality rules from Section 14 (Page 28):
  - **Critical rules**: Company PK uniqueness (DQ-01), Annual PK uniqueness (DQ-02), FK integrity (DQ-03), Year format check (DQ-07), Ticker format length/validity (DQ-08).
  - **Warning rules**: Balance sheet equation balance (DQ-04), OPM margin check (DQ-05), Positive sales check (DQ-06), Net cash flow matches CFO+CFI+CFF (DQ-09), Non-negative fixed assets (DQ-10), Tax rate range (DQ-11), Dividend payout cap (DQ-12), URL validity (DQ-13), EPS sign consistency (DQ-14), Coverage check (DQ-16).
  - Output failures to `data/validation_failures.csv`.
- Create `src/etl/schema.sql` declaring SQLite schema tables (10 tables: `companies`, `profitandloss`, `balancesheet`, `cashflow`, `analysis`, `documents`, `prosandcons`, `sectors`, `market_cap`, `stock_prices`) with strict data types, primary keys, and foreign keys.
- Write SQLite database loader inside `src/etl/loader.py` to:
  - Connect to SQLite using a context manager.
  - Execute DDL from `schema.sql`.
  - Enforce foreign keys via `PRAGMA foreign_keys = ON;`.
  - Load normalized DataFrames into SQLite tables.

### 📦 Deliverables
- `src/etl/validator.py`
- `src/etl/schema.sql`
- Core table loading code in `src/etl/loader.py`.
- Initial `data/validation_failures.csv`.

### 🗣️ Daily Stand-Up (End of Day 3)
- **What did I complete yesterday?**
  > "Yesterday, I wrote the normalisation functions, loaded core Excel files using header=1, and verified everything with a suite of 40+ pytest cases."
- **What will I complete today?**
  > "Today, I will write `src/etl/validator.py` to enforce the 16 DQ rules and generate the validation failures log. I will also write `src/etl/schema.sql` to build the 10-table SQLite schema and code the database insertion routines."
- **What is blocking me?**
  > "Enforcing the SQLite foreign key checks is producing errors when loading tables out of order. I am solving this by ordering the inserts: `companies` first, then its dependent child tables."
- **Anything to share?**
  > "I noticed that 84 companies have missing rows in `prosandcons.xlsx` and `analysis.xlsx`. These are warnings (not critical), so the validator logs them and proceeds with loading. This is normal according to the coverage matrix on Page 17."

---

## 📅 June 20, 2026 (Saturday) – Day 4: Supplementary Data Ingestion & Full Ingestion Run
Load the 5 supplementary datasets and execute the end-to-end ingestion pipeline.

### 🛠️ Tasks
- Update `src/etl/loader.py` to parse the 5 supplementary files from `data/supporting/` (using `header=0`). Normalise their headers and data content.
- Integrate validation rules for supplementary data (e.g., verifying tickers exist in `companies` master table).
- Implement the load audit logging: write a function that records table-level loading statistics to `data/load_audit.csv` (storing: table name, rows in, rows out, rows rejected, execution timestamp, and runtime in seconds).
- Run the full ETL pipeline to ingest all 12 source files into `data/nifty100.db`. Verify that the database is fully populated and no critical DQ violations are present.

### 📦 Deliverables
- Fully completed `src/etl/loader.py`.
- Relational SQLite database: `data/nifty100.db` with all 10 tables loaded.
- Ingestion statistics audit log: `data/load_audit.csv`.

### 🗣️ Daily Stand-Up (End of Day 4)
- **What did I complete yesterday?**
  > "Yesterday, I implemented the 16 DQ validation rules, designed the SQLite star schema, and wrote the database loader with foreign key constraints."
- **What will I complete today?**
  > "Today, I will extend `src/etl/loader.py` to load the 5 supplementary files (using header=0). I'll write the load audit function to generate `data/load_audit.csv`, and run a full ingestion script to build the entire `nifty100.db`."
- **What is blocking me?**
  > "None. The database load is executing correctly."
- **Anything to share?**
  > "I verified that the raw row counts in `stock_prices.xlsx` match the SQLite table row counts (5,520 rows) exactly. The database size is approximately ~1.1 MB, which is efficient and lightweight."

---

## 📅 June 21, 2026 (Sunday) – Day 5: Data Quality Review & Manual Spot Checking
Review the database contents, fix bugs, and document data quality findings.

### 🛠️ Tasks
- Conduct a data quality review: manually select 5 random companies (e.g., TCS, HDFCBANK, INFYS, Reliance, Tata Motors) and query their SQLite records.
- Cross-check their values (Sales, Profit, Reserves, borrowings) against the raw Excel spreadsheets.
- Verify that there are zero critical errors (orphaned records, duplicated company-years, invalid date formats).
- Write up findings, row count validations, and anomalies in `docs/dq_review_notes.md`.
- Debug any parsing anomalies discovered during validation and rebuild the database.

### 📦 Deliverables
- `docs/dq_review_notes.md`
- Audited and clean `data/nifty100.db`.

### 🗣️ Daily Stand-Up (End of Day 5)
- **What did I complete yesterday?**
  > "Yesterday, I completed the load of the supplementary datasets, ran the full ETL pipeline, and generated the database file and the `load_audit.csv` report."
- **What will I complete today?**
  > "Today, I will perform a comprehensive data quality review. I'll write a script to extract records for 5 random companies, manually verify them against the raw spreadsheets, write my findings in `docs/dq_review_notes.md`, and patch any parsing bugs found."
- **What is blocking me?**
  > "None. I am allocating plenty of time today to spot check values to ensure 100% mathematical accuracy before writing our SQL analysis queries."
- **Anything to share?**
  > "I found that some companies have annual reports starting from 2010 while others only cover 2018 onwards. This is normal, and our review notes will document this year-coverage distribution."

---

## 📅 June 22, 2026 (Monday) – Day 6: SQL Analysis, Retrospective & Hand-Off
Verify the database with analytical queries, run the full test suite, perform the sprint retrospective, and tag the release for submission.

### 🛠️ Tasks
- Write `exploratory_queries.sql` containing the 10+ exploratory SQL queries from Section 24 (Page 39):
  1. Top 10 ROE Companies (Latest Year)
  2. Debt-Free Companies
  3. Consecutive FCF Positive (5yr)
  4. Sector Median ROE
  5. Capital Allocation Pattern Count
  6. Revenue CAGR > 15% (5yr)
  7. Missing Annual Reports
  8. Peer Group Rankings (ROE)
  9. Table row count query
  10. Null/missing values analysis
- Execute the SQL queries on `nifty100.db` and save their results.
- Create a Sprint 1 retrospective report `sprint1_retro.md` documenting achievements, metrics, challenges, and next-sprint recommendations.
- Run the entire pytest suite to verify all test cases pass.
- Create a git tag `v1.0-sprint1` for the project and commit all changes.

### 📦 Deliverables
- `exploratory_queries.sql`
- `sprint1_retro.md`
- Passing test report (`pytest_report.html` or terminal log showing all green)
- Git tag `v1.0-sprint1` registered on the repository.

### 🗣️ Daily Stand-Up (End of Day 6 - Handoff)
- **What did I complete yesterday?**
  > "Yesterday, I conducted manual spot-checks for 5 companies, verified data integrity, and documented my findings in `docs/dq_review_notes.md`."
- **What will I complete today?**
  > "Today is the deadline. I will write and run the 10 exploratory SQL queries to analyze the populated database, complete the `sprint1_retro.md` report, verify the full pytest suite is green, and tag the repository release as `v1.0-sprint1`."
- **What is blocking me?**
  > "None. All deliverables are on track for submission before the end of the day."
- **Anything to share?**
  > "The SQL queries have run successfully and show that 92 companies are correctly populated, all foreign keys are intact, and the data distribution is clean. The foundation is complete and ready for Sprint 2."
