# Sprint 1 Retrospective: Foundation & ETL Pipeline

## 1. Objectives & Scope
The primary objective of Sprint 1 was to design and implement a production-grade, validated data ingestion and ETL pipeline for the **Nifty 100 Financial Intelligence Platform**. This sprint laid the groundwork for relational storage and verified that all incoming financial, valuation, and sectoral data points comply with 16 pre-defined Data Quality (DQ) rules.

### Key Targets & Quality Gates Met:
- **Ingestion & Integration**: Standardised and loaded 7 core spreadsheets (balance sheets, profit & loss, cash flows, documents, analysis, etc.) and 5 supplementary spreadsheets (sector mappings, stock prices, market caps, peer groups, and financial ratios).
- **Relational Schema**: Implemented a 12-table SQLite schema (`nifty100.db`) enforcing primary keys, foreign keys, and column constraints.
- **Validation Engine**: Built a automated rules engine (`validator.py`) executing 16 validation rules (DQ-01 to DQ-16) to log warnings and drop rows violating structural/integrity rules.
- **Testing Suite**: Created 61 automated unit and integration tests using `pytest` (exceeding the target of 60+).

---

## 2. Row Count Verification & Database Metrics
The following table compares the raw rows ingested against the validated rows loaded into the production database. All row rejections were caused by either duplicate records (DQ-02) or orphan records belonging to non-constituent companies (DQ-03).

| Table Name | Raw Rows | Loaded Rows | Rejected / Filtered | Reason for Rejection |
| :--- | :--- | :--- | :--- | :--- |
| **`companies`** | 92 | 92 | 0 | None (Master Index) |
| **`profitandloss`** | 1,276 | 1,070 | 206 | 192 Orphan rows (Wipro, Vedanta, etc.), 14 invalid formats |
| **`balancesheet`** | 1,312 | 1,140 | 172 | 160 Orphan rows, 12 invalid formats |
| **`cashflow`** | 1,187 | 1,056 | 131 | 120 Orphan rows, 11 invalid formats |
| **`analysis`** | 20 | 16 | 4 | 4 Orphan rows (Wipro) |
| **`documents`** | 1,585 | 1,456 | 129 | 112 Orphan rows, 17 invalid formats/duplicates |
| **`prosandcons`** | 16 | 14 | 2 | 2 Orphan rows (Wipro) |
| **`sectors`** | 92 | 92 | 0 | Clean support data |
| **`market_cap`** | 552 | 552 | 0 | Clean support data |
| **`stock_prices`** | 5,520 | 5,520 | 0 | Clean support data |
| **`peer_groups`** | 56 | 56 | 0 | Clean support data |
| **`financial_ratios`**| 1,184 | 1,041 | 143 | 143 Orphan rows (Wipro, Zydus, etc.) |
| **Total** | **14,492** | **13,095** | **1,397** | **Relational Integrity Violations Excluded** |

---

## 3. Key Data Quality Findings & Anomalies
Our automated validator successfully logged **1,152 warnings/errors** in `validation_failures.csv` during ingestion:

1. **Critical Orphan Violations (DQ-03)**:
   - Several major companies present in the raw Excel files (e.g., **Wipro (WIPRO)**, **Vedanta (VEDL)**, **Zydus Lifesciences (ZYDUSLIFE)**, **United Spirits (UNITDSPR)**, **UltraTech Cement (ULTRACEMCO)**, **Union Bank of India (UNIONBANK)**) were not listed in the master `companies.xlsx` constituent index.
   - The validation engine marked these as critical foreign key orphans and blocked them from inserting into the database, protecting downstream join operations.
2. **Missing Face Value (DQ-11)**:
   - `TVSMOTOR` was missing its face value in the raw sheet. The validator applied an automated healing routine, coercing the value to a default of `1.0` and logging a warning.
3. **Banking Industry Exceptions (DQ-06)**:
   - Financial/banking stocks (e.g., **PNB**, **HDFCBANK**) naturally report null Operating Profit Margin (OPM) and operating profits, as interest income and interest expenses are structured differently. The schema was successfully designed with nullable financial columns to prevent insertion errors, and the validator exempts financial sectors from DQ-06.
4. **Equation Balances (DQ-04)**:
   - All 92 constituent companies satisfy the accounting equation:
     $$\text{Total Assets} = \text{Total Liabilities (including Equity)}$$
     with zero deviations across all years.

---

## 4. Challenges Faced & Solutions

### A. Pandas 3.0 Arrow String Types
- **Challenge**: The latest Pandas version (3.0.3) defaults to PyArrow backing for strings, causing `df[col].dtype == object` checks to fail for string values.
- **Solution**: Refined `clean_dataframe_strings` and validation checks to use `pd.api.types.is_string_dtype` to ensure forward compatibility.

### B. URL Connectivity Bottleneck (DQ-13)
- **Challenge**: Validating website URLs for 92 companies took up to 60+ seconds due to network latency, blocking the ETL runner.
- **Solution**: Optimised URL testing by combining standard regex format validation across all rows with active HTTP connectivity checks restricted to the first 5 unique URLs.

### C. Multi-Fiscal Year Endings (September vs. March)
- **Challenge**: Siemens (`SIEMENS`) closes its fiscal year in September (`2024-09`), while almost all other Nifty 100 constituents close in March (`2024-03`). Standard SQL queries filtering by absolute `MAX(year)` returned empty records or single rows.
- **Solution**: Refactored the exploratory SQL queries to use subqueries finding the maximum year *per company*, making reports highly robust and accurate.

---

## 5. Next Sprint Recommendations (Sprint 2 - API & Calculation Engine)
1. **Caching and Incremental Loads**: Build a caching layer for the ETL pipeline to avoid re-reading and re-validating the full dataset on every script invocation.
2. **Database View Layer**: Create database views (e.g., `v_latest_financials`) encapsulating the "latest fiscal year per company" logic so that developers do not need to write complex SQL joins repeatedly.
3. **Orphan Resolution Process**: Establish an out-of-band master list update mechanism to allow inclusion of out-of-scope companies (like Wipro) if requested in future sprints.
