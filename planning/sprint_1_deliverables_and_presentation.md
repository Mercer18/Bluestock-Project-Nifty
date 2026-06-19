# Deliverables & Presentation Guide: Sprint 1

This document outlines the exact deliverables you must build, what files must be uploaded to the portal, what needs to be shown for verification, and how to present your progress.

---

## 🛠️ 1. What We Need to Build & Show
For Sprint 1 (Foundation & ETL), you are building the core data ingestion engine. Here is the list of files to write:

### A. Python Source Code (in `src/etl/`)
1.  **`normaliser.py`**: Houses clean functions for uniform company tickers and standardised `YYYY-MM` year fields.
2.  **`validator.py`**: Executes the data validation engine checking all 16 Data Quality rules.
3.  **`loader.py`**: Handles Excel reads, calls normalisation/validation routines, initiates the SQLite database connection, creates tables, and executes bulk data insertion.
4.  **`schema.sql`**: Relational database DDL schema setting up the 10 tables, data types, primary keys, and foreign keys.

### B. Unit Testing (in `tests/etl/`)
1.  **`test_normalise.py`**: Contains 40+ unit test cases testing various year formats and ticker inputs to ensure parser correctness.

### C. Analytical Verification
1.  **`exploratory_queries.sql`**: A file with 10+ standard SQL queries (e.g., top ROE companies, debt-free list, row count comparisons) to verify database data integrity.

---

## 📦 2. What Needs to Be Uploaded
When submitting Sprint 1 on the portal, upload the following:

### A. Core Output Files
*   **`data/nifty100.db`**: The final Relational SQLite database loaded with all 92 companies and their historical financial datasets (12 source sheets combined).
*   **`data/load_audit.csv`**: A CSV detailing rows read, loaded, rejected, and timing statistics per table.
*   **`data/validation_failures.csv`**: A CSV capturing all data quality warnings logged during execution.

### B. Source Repository
*   A zipped file of the project directory (excluding `.venv/` and local `.env`) or a link to your private Git repository tagged at release version `v1.0-sprint1`.

### C. Documentation
*   `README.md` at the project root explaining how to set up the environment, run the ETL loader, and execute the test suite.
*   `docs/dq_review_notes.md` summarising the manual data quality checks.
*   `planning/` folder containing the sprint planning documents.
*   `sprint1_retro.md` documenting the sprint outcomes.

---

## 🖥️ 3. How We Are Going to Show Everything (Presentation & Demo)
To successfully demonstrate completion of Sprint 1 to your manager/team lead, follow this checklist:

### A. Demonstrate Code Correctness (Run Pytest)
*   **Action**: Execute the command `pytest tests/etl/` from your terminal.
*   **What to Show**: Screenshot the terminal window showing the test results:
    ```text
    ============================= test session starts =============================
    platform win32 -- Python 3.13.12, pytest-7.4.4, pluggy-1.3.0
    collected 60 items

    tests/etl/test_normalise.py ........................................ [ 66%]
    tests/dq/test_rules.py ....................                          [100%]

    ============================== 60 passed in 1.12s =============================
    ```

### B. Demonstrate DB Population (Run Ingestion)
*   **Action**: Run `python src/etl/loader.py` (or execute `make load` if a Makefile is configured).
*   **What to Show**: The execution terminal logs showing:
    1. Successful reading of Excel files.
    2. Number of warnings found and written to `validation_failures.csv`.
    3. Creation of `nifty100.db`.
    4. Generation of `load_audit.csv`.

### C. Demonstrate Database Structure & Queries (Run SQL Queries)
*   **Action**: Open the SQLite terminal or an IDE tool (like VS Code SQLite viewer) and execute the queries in `exploratory_queries.sql`.
*   **What to Show**: The result of the query counting rows in each of the 10 tables to prove no data loss. For example:
    | Table Name | Row Count | Source Excel Sheet Reference |
    | :--- | :--- | :--- |
    | `companies` | 92 | `companies.xlsx` |
    | `profitandloss` | 1,276 | `profitandloss.xlsx` |
    | `balancesheet` | 1,312 | `balancesheet.xlsx` |
    | `cashflow` | 1,187 | `cashflow.xlsx` |
    | `analysis` | 20 | `analysis.xlsx` |
    | `documents` | 1,585 | `documents.xlsx` |
    | `prosandcons` | 16 | `prosandcons.xlsx` |
    | `sectors` | 92 | `sectors.xlsx` |
    | `stock_prices` | 5,520 | `stock_prices.xlsx` |
    | `market_cap` | 552 | `market_cap.xlsx` |
    | `peer_groups` | 56 | `peer_groups.xlsx` |

---

## 🎯 4. Sprint 1 Acceptance Criteria (Quality Gates)
To pass Sprint 1 review, your output must satisfy the following gates (from Section 18, Page 32):

1.  **AC-01 (Data Coverage)**: Exactly 92 companies present in `companies` table. No extra/missing tickers.
2.  **AC-02 (Time Coverage)**: >=90% of companies must have >=10 years of time-series records.
3.  **AC-03 (Schema Integrity)**: All foreign key relationships intact. `PRAGMA foreign_key_check` returns 0 rows.
4.  **AC-19 (DQ Documentation)**: `validation_failures.csv` exists and logs all occurrences with proper columns.
5.  **AC-20 (Code Formatting)**: Zero linting errors via `ruff check src/` and fully formatted by `black`.
