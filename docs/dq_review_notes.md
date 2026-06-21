# Data Quality Review & Manual Spot Checks (Sprint 1)

This document contains the verification notes and manual spot checks executed on the relational database `nifty100.db` to satisfy **Day 6 (Data Quality Review)**.

---

## 🔍 1. Verification Strategy & Objectives
To ensure the ETL pipeline ingested, cleaned, and normalized the financial data correctly, we conducted a manual QA audit on **5 target companies** representing different sectors and reporting variations:
1.  **TCS** (Information Technology - IT Services)
2.  **HDFCBANK** (Financials - Private Banks)
3.  **SBILIFE** (Financials - Life Insurance)
4.  **INFY** (Information Technology - IT Services)
5.  **TVSMOTOR** (Consumer Discretionary - Two Wheelers)

We verified:
- String stripping and case normalisation (Tickers and headers).
- Time-series year format standardisation (YYYY-MM).
- Mathematical integrity (Assets = Liabilities).
- Correct execution of the data quality rules.
- Orphan record detection.

---

## 📈 2. Verification Summary per Company

### A. TCS (Tata Consultancy Services Ltd)
- **Master Data**: Correctly mapped name, face value (1.0), and website (https://www.tcs.com/).
- **Sector Mapping**: Mapped to `Information Technology` (IT Services) with index weight of `1.1%`.
- **Row Counts**: 12 P&L rows (2013-03 to 2024-03), 13 Balance Sheet rows (2013-03 to 2024-09), 12 Cash Flow rows.
- **Sample Cross-Check (2024-03)**:
  - *Profit & Loss*: Sales = `240,893 Cr`, Net Profit = `46,099 Cr` (Matches source profitandloss.xlsx exactly).
  - *Balance Sheet (2024-09)*: Total Assets (`161,124 Cr`) = Total Liabilities (`161,124 Cr`) (Enforces mathematical balance).

### B. HDFCBANK (HDFC Bank Ltd)
- **Master Data**: Correctly mapped name, face value (1.0), and website (http://www.hdfcbank.com/).
- **Sector Mapping**: Mapped to `Financials` (Private Banks) with index weight of `1.06%`.
- **Row Counts**: 12 P&L rows, 12 Balance Sheet rows, 12 Cash Flow rows.
- **Sample Cross-Check (2024-03)**:
  - *Profit & Loss*: Sales = `283,649 Cr`, Net Profit = `65,446 Cr`.
  - *Balance Sheet*: Total Assets (`4,030,194 Cr`) = Total Liabilities (`4,030,194 Cr`).

### C. SBILIFE (SBI Life Insurance Company Ltd)
- **Master Data**: Correctly mapped name, face value (10.0), and website.
- **Sector Mapping**: Mapped to `Financials` (Life Insurance) with index weight of `3.16%`.
- **Sample Cross-Check (2024-03)**:
  - *Profit & Loss*: Sales = `131,988 Cr`, Net Profit = `1,894 Cr`.
  - *Balance Sheet (2024-09)*: Total Assets (`448,497 Cr`) = Total Liabilities (`448,497 Cr`).

### D. INFY (Infosys Ltd)
- **Master Data**: Correctly mapped name, face value (5.0), and website.
- **Sector Mapping**: Mapped to `Information Technology` with index weight of `3.37%`.
- **Sample Cross-Check (2024-03)**:
  - *Profit & Loss*: Sales = `153,670 Cr`, Net Profit = `26,248 Cr`.
  - *Balance Sheet (2024-09)*: Total Assets (`141,870 Cr`) = Total Liabilities (`141,870 Cr`).

### E. TVSMOTOR (TVS Motor Company Ltd)
- **Master Data**: Correctly mapped name, website is missing (`None`).
- **Coercion Check**: TVSMOTOR had a missing (null) `face_value` in the raw `companies.xlsx`. The validator successfully flagged it and coerced it to the standard default value of `1.0` (TVS Motor's actual share face value in India) to satisfy database NOT NULL constraints.
- **Sector Mapping**: Mapped to `Consumer Discretionary` (Two Wheelers) with index weight of `2.16%`.
- **Sample Cross-Check (2024-03)**:
  - *Profit & Loss*: Sales = `39,145 Cr`, Net Profit = `1,779 Cr`.
  - *Balance Sheet (2024-09)*: Total Assets (`44,946 Cr`) = Total Liabilities (`44,946 Cr`).

---

## 🚨 3. Key Data Quality Findings & Anomalies Logged

During our manual spot checks and automated validations, we discovered several anomalies in the raw spreadsheets. The ETL engine handled them automatically:

1.  **Orphan Records (DQ-03 Violation)**:
    *   `WIPRO` was found in `analysis.xlsx` (growth metrics spreadsheet), but **Wipro is missing** from the master `companies.xlsx` sheet.
    *   *ETL Action*: The validator flagged this as a critical foreign key violation and excluded the orphan records to maintain relational integrity, preventing insertion crashes in SQLite.
2.  **Low Coverage (DQ-16 Warnings)**:
    *   Several companies (e.g. `JIOFIN` and `LICI`) had less than 5 years of historical financial data.
    *   *ETL Action*: Logged as warnings in `validation_failures.csv` so analysts are aware of coverage gaps.
3.  **Deduplicated Records (DQ-02 Violation)**:
    *   Raw sheets like `documents.xlsx` contained duplicate records (e.g., `HAL` had duplicate 2011 rows, one with a null URL and one with a valid PDF URL).
    *   *ETL Action*: Automatically deduplicated, preserving the last non-null URL.
4.  **Exemptions (DQ-06 Check)**:
    *   Banking stocks (e.g., `PNB`) have null values for operating profits. The validator correctly identified PNB as a financial stock and bypassed standard operating profit checks.
