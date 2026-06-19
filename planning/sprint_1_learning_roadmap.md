# Learning Roadmap: Sprint 1 (June 17 – June 22)

This roadmap outlines the core technical concepts, libraries, and frameworks to learn day-by-day to successfully complete the Sprint 1 deliverables.

---

## 📚 June 17, 2026 – Day 1: Project Setup & Package Management
Understand python virtual environments, project structures, and package dependencies.

### 🧠 Core Concepts to Learn
1.  **Virtual Environments (`venv`)**:
    *   Why isolate environments?
    *   How to create (`python -m venv .venv`) and activate (`.venv\Scripts\Activate.ps1` in PowerShell) virtual environments on Windows.
2.  **Package Managers (`pip`)**:
    *   How to write a standard `requirements.txt` with version pinning (e.g., `pandas>=2.0.0`).
    *   How to install all pinned packages: `pip install -r requirements.txt`.
3.  **Environment Variables (`dotenv`)**:
    *   How to hide sensitive configurations (database paths, API ports) in a local `.env` file that is excluded from Git.
    *   How to read them in Python: `from dotenv import load_dotenv; import os; load_dotenv()`.
4.  **Formatting & Linting Tools**:
    *   *Black*: Python's uncompromising code formatter (PEP 8 compliance).
    *   *Ruff*: High-performance Python linter for checking style violations and syntax errors.

---

## 📚 June 18, 2026 – Day 2: Advanced Pandas Data Parsing & String Normalisation
Learn how to read Excel files with metadata header offsets, clean messy strings, normalise columns, and write unit tests.

### 🧠 Core Concepts to Learn
1.  **Pandas Multi-Header Parsing**:
    *   How to skip metadata rows when reading Excel: `pd.read_excel(filepath, header=1)`.
    *   Handling merged cells and missing headers in Pandas.
2.  **String Vectorised Operations**:
    *   Performing bulk string cleaning: `df['company_id'].str.strip().str.upper()`.
3.  **Regular Expressions (`re` module) for Date Parsing**:
    *   Understanding patterns for year-month inputs.
    *   Converting abbreviations like `Mar-23`, `FY23`, `Jun-23` or `Dec 2012` to a standardized ISO `YYYY-MM` format.
4.  **Unit Testing with Pytest**:
    *   Understanding test assertions: `assert normalize_ticker(" tcs ") == "TCS"`.
    *   How to run tests: `pytest tests/`.
    *   Using pytest parametrization to run a function against multiple test cases.

---

## 📚 June 19, 2026 – Day 3: Relational DB Design & Schema Constraints
Learn to design relational tables, enforce foreign keys, write SQLite DDL scripts, and validate loaded data.

### 🧠 Core Concepts to Learn
1.  **Relational Database Design**:
    *   Primary Keys (PK) vs Foreign Keys (FK).
    *   One-to-many (`1:N`) and Many-to-many (`M:N`) relationships.
    *   Ensuring database integrity and preventing duplicate entries.
2.  **SQLite Data Types & DDL Schema**:
    *   Declaring schema using `CREATE TABLE` with `INTEGER`, `VARCHAR`, `NUMERIC`, and `TEXT`.
    *   Enforcing constraints: `PRIMARY KEY`, `NOT NULL`, `FOREIGN KEY ... REFERENCES`.
3.  **Enforcing Constraints in SQLite**:
    *   Enforcing referential integrity dynamically at connection time: `PRAGMA foreign_keys = ON;`.
4.  **Data Quality Validation Paradigms**:
    *   How to structure a validation rule engine (rules DQ-01 to DQ-16).
    *   Logging data warnings to CSV: `validation_failures.csv`.

---

## 📚 June 20, 2026 – Day 4: SQLite Database Ingestion & Transaction Management
Learn standard Python SQLite integration, bulk inserts, and auditing execution metrics.

### 🧠 Core Concepts to Learn
1.  **Python `sqlite3` API**:
    *   Establishing connection objects and cursors: `conn = sqlite3.connect(db_path)`.
    *   Using context managers (`with conn:`) to auto-commit transactions and auto-close connections.
2.  **Parameterised Queries (SQL Injection Prevention)**:
    *   Why you must *never* use f-strings for SQL variables.
    *   Correct syntax: `cursor.execute("INSERT INTO table VALUES (?, ?)", (val1, val2))`.
3.  **Bulk Inserts**:
    *   Using `executemany` or Pandas `to_sql(name, con, if_exists='append', index=False)` for high-performance loading.
4.  **ETL Audit Log Tracking**:
    *   How to track pipeline performance (timing execution with `time.time()`).
    *   Writing table statistics (row counts in/out, rejections, runtime) to `load_audit.csv`.

---

## 📚 June 21, 2026 – Day 5: Database Verification & Quality Assurance
Learn manual database validation workflows, write SQL scripts to spot-check records, and debug ETL scripts.

### 🧠 Core Concepts to Learn
1.  **Data Auditing Workflows**:
    *   Why automated validation is not enough: the necessity of manual verification.
    *   How to select random cohorts for verification (e.g., picking 5 diverse companies representing different sectors).
2.  **Verification Queries**:
    *   Writing SQL checks to compare database aggregates against Excel sum calculations.
    *   Finding nulls, duplicates, and orphaned records using SQL joins: `LEFT JOIN ... WHERE child.id IS NULL`.
3.  **Debugging ETL Bugs**:
    *   Troubleshooting character encoding issues, trailing hidden whitespaces, and unexpected decimal formatting in numeric fields.

---

## 📚 June 22, 2026 – Day 6: Analytical SQL Queries & Agile Sprint Reviews
Learn to write complex SQL queries, analyze financial metrics, perform retrospectives, and prepare production deliverables.

### 🧠 Core Concepts to Learn
1.  **Exploratory & Analytical SQL**:
    *   *Aggregations*: `SUM()`, `AVG()`, `COUNT()`, `GROUP BY`.
    *   *Joins*: Combining tables to pull composite profiles (e.g., joining `profitandloss` and `balancesheet` on `company_id` and `year`).
    *   *Window Functions*: Using `RANK() OVER (PARTITION BY ... ORDER BY ...)` for ranking companies.
    *   *Common Table Expressions (CTEs)*: Structuring complex queries for readability.
2.  **Sprint Retrospectives (Agile Framework)**:
    *   Reflecting on what went well, what failed, and identifying action items.
    *   Writing clean retrospective markdown logs (`sprint1_retro.md`).
3.  **Handoff Procedures**:
    *   Cleaning code scripts (docstrings, type hints, PEP 8 checking).
    *   Creating git tags (`git tag v1.0-sprint1`) to release a stable snapshot of the codebase.
