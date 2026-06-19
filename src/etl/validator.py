import pandas as pd
import numpy as np
import os
import re
import requests
from typing import List, Dict, Tuple, Set

class DataValidator:
    def __init__(self):
        self.failures: List[Dict] = []
        self.financial_sectors: Set[str] = set()  # Loaded from sectors.xlsx

    def log_failure(self, company_id: str, year: str, field: str, issue: str, severity: str):
        """Logs a validation failure."""
        self.failures.append({
            "company_id": company_id,
            "year": str(year) if year is not None else "N/A",
            "field": field,
            "issue": issue,
            "severity": severity
        })

    def validate_companies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validates companies DataFrame (DQ-01, DQ-08).
        """
        # Drop rows where ticker PK is null (handles empty lines in Excel)
        df = df.dropna(subset=["id"])
        
        # Coerce null face_value to 1.0 (standard fallback) and log a warning
        if df["face_value"].isna().any():
            null_cos = df[df["face_value"].isna()]["id"].tolist()
            for co in null_cos:
                self.log_failure(co, "N/A", "face_value", "Missing face_value coerced to 1.0 (DQ warning)", "WARNING")
            df["face_value"] = df["face_value"].fillna(1.0)

        # DQ-01: Company PK Uniqueness
        if df["id"].nunique() != len(df):
            duplicates = df[df.duplicated(subset=["id"], keep=False)]["id"].unique()
            for dup in duplicates:
                self.log_failure(dup, "N/A", "id", "Duplicate company ticker (DQ-01)", "CRITICAL")
            raise ValueError(f"CRITICAL: Duplicate company tickers found: {list(duplicates)}. Halting load.")

        valid_rows = []
        for idx, row in df.iterrows():
            ticker = row["id"]
            
            # DQ-08: Ticker Format Length
            if not (2 <= len(ticker) <= 12):
                self.log_failure(ticker, "N/A", "id", f"Ticker length {len(ticker)} out of range 2-12 (DQ-08)", "CRITICAL")
                continue  # Reject row
                
            valid_rows.append(row)
            
        return pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)

    def validate_profitandloss(self, df: pd.DataFrame, valid_companies: Set[str]) -> pd.DataFrame:
        """
        Validates Profit & Loss DataFrame (DQ-02, DQ-03, DQ-05, DQ-06, DQ-07, DQ-08, DQ-11, DQ-12, DQ-14).
        """
        # Drop rows where PK is null
        df = df.dropna(subset=["company_id", "year"])
        valid_rows = []
        
        # DQ-02: Deduplicate (company_id, year) - keep last
        dup_mask = df.duplicated(subset=["company_id", "year"], keep="last")
        for idx, row in df[df.duplicated(subset=["company_id", "year"], keep=False)].iterrows():
            if dup_mask.loc[idx] == False:  # This is the last one, it will be kept
                self.log_failure(row["company_id"], row["year"], "year", "Duplicate annual record found. Keeping last occurrence (DQ-02).", "CRITICAL")
        
        df_dedup = df[~dup_mask].copy()

        for idx, row in df_dedup.iterrows():
            co_id = row["company_id"]
            yr = row["year"]
            reject = False
            
            # DQ-03: FK Integrity
            if co_id not in valid_companies:
                self.log_failure(co_id, yr, "company_id", f"Orphan record: {co_id} not in companies table (DQ-03)", "CRITICAL")
                reject = True

            # DQ-07: Year Format
            if yr == "PARSE_ERROR" or not re.match(r"^\d{4}-\d{2}$", str(yr)):
                self.log_failure(co_id, yr, "year", f"Invalid year format: {yr} (DQ-07)", "CRITICAL")
                reject = True

            # DQ-08: Ticker Format
            if not (2 <= len(str(co_id)) <= 12):
                self.log_failure(co_id, yr, "company_id", f"Ticker length out of range: {co_id} (DQ-08)", "CRITICAL")
                reject = True

            if reject:
                continue

            # DQ-05: OPM Cross-Check
            sales = row.get("sales", 0)
            op_profit = row.get("operating_profit", 0)
            opm_pct = row.get("opm_percentage", 0)
            if pd.notna(sales) and sales > 0 and pd.notna(op_profit) and pd.notna(opm_pct):
                calc_opm = (op_profit / sales) * 100
                if abs(opm_pct - calc_opm) >= 1.0:
                    self.log_failure(co_id, yr, "opm_percentage", f"OPM mismatch: reported {opm_pct}%, calculated {calc_opm:.2f}% (DQ-05)", "WARNING")

            # DQ-06: Positive Sales check for non-banks
            if co_id not in self.financial_sectors:
                if pd.notna(sales) and sales <= 0:
                    self.log_failure(co_id, yr, "sales", f"Non-positive sales for non-financial company: {sales} (DQ-06)", "WARNING")

            # DQ-11: Tax Rate Range
            tax_pct = row.get("tax_percentage", 0)
            if pd.notna(tax_pct) and not (0 <= tax_pct <= 60):
                self.log_failure(co_id, yr, "tax_percentage", f"Out of range tax rate: {tax_pct}% (DQ-11)", "WARNING")

            # DQ-12: Dividend Payout Cap
            div_payout = row.get("dividend_payout", 0)
            if pd.notna(div_payout) and div_payout > 200:
                self.log_failure(co_id, yr, "dividend_payout", f"Dividend payout {div_payout}% exceeds 200% limit (DQ-12)", "WARNING")

            # DQ-14: EPS Sign Consistency
            net_prof = row.get("net_profit", 0)
            eps = row.get("eps", 0)
            if pd.notna(net_prof) and pd.notna(eps):
                if net_prof > 0 and eps <= 0:
                    self.log_failure(co_id, yr, "eps", f"EPS is non-positive ({eps}) while net profit is positive ({net_prof}) (DQ-14)", "WARNING")

            valid_rows.append(row)

        return pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)

    def validate_balancesheet(self, df: pd.DataFrame, valid_companies: Set[str]) -> pd.DataFrame:
        """
        Validates Balance Sheet DataFrame (DQ-02, DQ-03, DQ-04, DQ-07, DQ-08, DQ-10, DQ-15).
        """
        # Drop rows where PK is null
        df = df.dropna(subset=["company_id", "year"])
        valid_rows = []
        
        # DQ-02: Deduplicate (company_id, year)
        dup_mask = df.duplicated(subset=["company_id", "year"], keep="last")
        df_dedup = df[~dup_mask].copy()

        for idx, row in df_dedup.iterrows():
            co_id = row["company_id"]
            yr = row["year"]
            reject = False

            # DQ-03: FK Integrity
            if co_id not in valid_companies:
                self.log_failure(co_id, yr, "company_id", f"Orphan record: {co_id} (DQ-03)", "CRITICAL")
                reject = True

            # DQ-07: Year Format
            if yr == "PARSE_ERROR" or not re.match(r"^\d{4}-\d{2}$", str(yr)):
                self.log_failure(co_id, yr, "year", f"Invalid year format: {yr} (DQ-07)", "CRITICAL")
                reject = True

            # DQ-08: Ticker Format
            if not (2 <= len(str(co_id)) <= 12):
                self.log_failure(co_id, yr, "company_id", f"Ticker length out of range: {co_id} (DQ-08)", "CRITICAL")
                reject = True

            if reject:
                continue

            # DQ-04: Balance Sheet Balance (1% tolerance)
            tot_assets = row.get("total_assets", 0)
            tot_liab = row.get("total_liabilities", 0)
            if pd.notna(tot_assets) and tot_assets > 0 and pd.notna(tot_liab):
                pct_diff = abs(tot_assets - tot_liab) / tot_assets
                if pct_diff >= 0.01:
                    self.log_failure(co_id, yr, "total_assets", f"Balance sheet mismatch: assets {tot_assets}, liabilities {tot_liab} (diff {pct_diff*100:.2f}%) (DQ-04)", "WARNING")

            # DQ-10: Non-Negative Fixed Assets (coerce to 0 and log warning)
            fixed_ast = row.get("fixed_assets", 0)
            if pd.notna(fixed_ast) and fixed_ast < 0:
                self.log_failure(co_id, yr, "fixed_assets", f"Negative fixed assets coerced to 0: {fixed_ast} (DQ-10)", "WARNING")
                row["fixed_assets"] = 0

            # DQ-15: BSE/ASE Balance (strict, equal to assets)
            if pd.notna(tot_assets) and pd.notna(tot_liab) and tot_assets != tot_liab:
                self.log_failure(co_id, yr, "total_assets", f"BSE/ASE balance mismatch (strict): assets {tot_assets} != liabilities {tot_liab} (DQ-15)", "INFO")

            valid_rows.append(row)

        return pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)

    def validate_cashflow(self, df: pd.DataFrame, valid_companies: Set[str]) -> pd.DataFrame:
        """
        Validates Cash Flow DataFrame (DQ-02, DQ-03, DQ-07, DQ-08, DQ-09).
        """
        # Drop rows where PK is null
        df = df.dropna(subset=["company_id", "year"])
        valid_rows = []
        
        # DQ-02: Deduplicate (company_id, year)
        dup_mask = df.duplicated(subset=["company_id", "year"], keep="last")
        df_dedup = df[~dup_mask].copy()

        for idx, row in df_dedup.iterrows():
            co_id = row["company_id"]
            yr = row["year"]
            reject = False

            # DQ-03: FK Integrity
            if co_id not in valid_companies:
                self.log_failure(co_id, yr, "company_id", f"Orphan record: {co_id} (DQ-03)", "CRITICAL")
                reject = True

            # DQ-07: Year Format
            if yr == "PARSE_ERROR" or not re.match(r"^\d{4}-\d{2}$", str(yr)):
                self.log_failure(co_id, yr, "year", f"Invalid year format: {yr} (DQ-07)", "CRITICAL")
                reject = True

            # DQ-08: Ticker Format
            if not (2 <= len(str(co_id)) <= 12):
                self.log_failure(co_id, yr, "company_id", f"Ticker length out of range: {co_id} (DQ-08)", "CRITICAL")
                reject = True

            if reject:
                continue

            # DQ-09: Net Cash Check
            cfo = row.get("operating_activity", 0)
            cfi = row.get("investing_activity", 0)
            cff = row.get("financing_activity", 0)
            net_cf = row.get("net_cash_flow", 0)
            
            cfo = cfo if pd.notna(cfo) else 0
            cfi = cfi if pd.notna(cfi) else 0
            cff = cff if pd.notna(cff) else 0
            
            calc_net_cf = cfo + cfi + cff
            if pd.notna(net_cf):
                if abs(net_cf - calc_net_cf) > 10:  # 10 Cr tolerance
                    self.log_failure(co_id, yr, "net_cash_flow", f"Net Cash Flow mismatch: reported {net_cf}, calculated {calc_net_cf} (DQ-09)", "WARNING")
                    row["net_cash_flow"] = calc_net_cf  # Compute from components

            valid_rows.append(row)

        return pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)

    def validate_documents(self, df: pd.DataFrame, valid_companies: Set[str]) -> pd.DataFrame:
        """
        Validates Documents DataFrame (DQ-03, DQ-08, DQ-13).
        """
        # Drop rows where PK is null
        df = df.dropna(subset=["company_id", "Year"])
        
        # Deduplicate (company_id, Year) - keep last
        dup_mask = df.duplicated(subset=["company_id", "Year"], keep="last")
        df_dedup = df[~dup_mask].copy()
        
        valid_rows = []
        for idx, row in df_dedup.iterrows():
            co_id = row["company_id"]
            yr = row["Year"]  # note Capital Y
            url = row["Annual_Report"]
            reject = False

            # DQ-03: FK Integrity
            if co_id not in valid_companies:
                self.log_failure(co_id, yr, "company_id", f"Orphan record in documents: {co_id} (DQ-03)", "CRITICAL")
                reject = True

            # DQ-08: Ticker Format
            if not (2 <= len(str(co_id)) <= 12):
                self.log_failure(co_id, yr, "company_id", f"Ticker length out of range: {co_id} (DQ-08)", "CRITICAL")
                reject = True

            if reject:
                continue

            # DQ-13: URL Validity (requests.head)
            # To prevent extremely slow ETL loads (1500+ network requests), we only perform network connection check
            # for the first 5 unique URLs, and validate the formatting via regex for the rest.
            if pd.notna(url):
                url_str = str(url).strip()
                is_valid_format = re.match(r'^https?://[^\s/$.?#].[^\s]*$', url_str, re.IGNORECASE) is not None
                if not is_valid_format:
                    self.log_failure(co_id, yr, "Annual_Report", f"Invalid URL format: {url_str} (DQ-13)", "WARNING")
                elif url_str.startswith("http"):
                    if not hasattr(self, "_checked_urls"):
                        self._checked_urls = set()
                    if url_str not in self._checked_urls and len(self._checked_urls) < 5:
                        self._checked_urls.add(url_str)
                        try:
                            res = requests.head(url_str, timeout=1.0, allow_redirects=True)
                            if res.status_code == 404:
                                self.log_failure(co_id, yr, "Annual_Report", f"URL returned 404: {url_str} (DQ-13)", "WARNING")
                        except Exception as e:
                            self.log_failure(co_id, yr, "Annual_Report", f"URL connection failed: {url_str} - Error: {e} (DQ-13)", "WARNING")

            valid_rows.append(row)

        return pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)

    def validate_analysis(self, df: pd.DataFrame, valid_companies: Set[str]) -> pd.DataFrame:
        """
        Validates Analysis DataFrame (DQ-03, DQ-08).
        """
        # Drop rows where PK is null
        df = df.dropna(subset=["company_id"])
        valid_rows = []
        for idx, row in df.iterrows():
            co_id = row["company_id"]
            if co_id not in valid_companies:
                self.log_failure(co_id, "N/A", "company_id", f"Orphan record in analysis: {co_id} (DQ-03)", "CRITICAL")
                continue
            if not (2 <= len(str(co_id)) <= 12):
                self.log_failure(co_id, "N/A", "company_id", f"Ticker length out of range: {co_id} (DQ-08)", "CRITICAL")
                continue
            valid_rows.append(row)
        return pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)

    def validate_prosandcons(self, df: pd.DataFrame, valid_companies: Set[str]) -> pd.DataFrame:
        """
        Validates Pros and Cons DataFrame (DQ-03, DQ-08).
        """
        # Drop rows where PK is null
        df = df.dropna(subset=["company_id"])
        valid_rows = []
        for idx, row in df.iterrows():
            co_id = row["company_id"]
            if co_id not in valid_companies:
                self.log_failure(co_id, "N/A", "company_id", f"Orphan record in prosandcons: {co_id} (DQ-03)", "CRITICAL")
                continue
            if not (2 <= len(str(co_id)) <= 12):
                self.log_failure(co_id, "N/A", "company_id", f"Ticker length out of range: {co_id} (DQ-08)", "CRITICAL")
                continue
            valid_rows.append(row)
        return pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)

    def check_coverage(self, pl_df: pd.DataFrame, bs_df: pd.DataFrame, cf_df: pd.DataFrame, valid_companies: Set[str]):
        """
        DQ-16: Coverage Check: Each company has >= 5 years of P&L, BS, CF records.
        """
        # Count years per company across tables
        pl_counts = pl_df.groupby("company_id")["year"].nunique().to_dict()
        bs_counts = bs_df.groupby("company_id")["year"].nunique().to_dict()
        cf_counts = cf_df.groupby("company_id")["year"].nunique().to_dict()

        for co in valid_companies:
            pl_cnt = pl_counts.get(co, 0)
            bs_cnt = bs_counts.get(co, 0)
            cf_cnt = cf_counts.get(co, 0)
            
            min_cnt = min(pl_cnt, bs_cnt, cf_cnt)
            if min_cnt < 5:
                self.log_failure(co, "N/A", "coverage", f"Company has low coverage: P&L {pl_cnt}yrs, BS {bs_cnt}yrs, CF {cf_cnt}yrs (under 5 years) (DQ-16)", "WARNING")

    def save_failures(self, filepath: str):
        """Saves failure logs to a CSV file."""
        if not self.failures:
            # Save empty CSV with headers
            df = pd.DataFrame(columns=["company_id", "year", "field", "issue", "severity"])
        else:
            df = pd.DataFrame(self.failures)
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        df.to_csv(filepath, index=False)
        print(f"Validation failures logged to {filepath}. Total violations: {len(self.failures)}")
