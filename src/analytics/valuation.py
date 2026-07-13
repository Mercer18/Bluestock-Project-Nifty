"""
Valuation Module for Nifty 100 Financial Intelligence Platform.
Computes FCF Yield, sector median P/E, 5-year median P/E, and flags overvalued/undervalued companies.
"""

import os
import sqlite3
import pandas as pd
import numpy as np

# Resolve paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "nifty100.db")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

def compute_valuation():
    """Queries SQLite and computes valuation summary and flags."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Load companies and their sectors
    df_companies = pd.read_sql_query(
        "SELECT c.id as company_id, c.company_name, s.broad_sector as sector "
        "FROM companies c "
        "LEFT JOIN sectors s ON c.id = s.company_id", conn
    )
    
    # 2. Load latest year (2024-03) market cap and ratios
    df_mc_latest = pd.read_sql_query(
        "SELECT company_id, pe_ratio, pb_ratio, ev_ebitda, market_cap_crore "
        "FROM market_cap WHERE year = '2024-03'", conn
    )
    
    df_ratios_latest = pd.read_sql_query(
        "SELECT company_id, free_cash_flow_cr FROM financial_ratios WHERE year = '2024-03'", conn
    )
    
    # 3. Load historical PE for 5-year median calculation
    # Years: 2020-03, 2021-03, 2022-03, 2023-03, 2024-03
    df_pe_hist = pd.read_sql_query(
        "SELECT company_id, pe_ratio FROM market_cap "
        "WHERE year IN ('2020-03', '2021-03', '2022-03', '2023-03', '2024-03')", conn
    )
    
    conn.close()
    
    # Compute 5-year median PE per company
    df_pe_5yr = df_pe_hist.groupby("company_id")["pe_ratio"].median().reset_index()
    df_pe_5yr.rename(columns={"pe_ratio": "5yr_median_PE"}, inplace=True)
    
    # Merge datasets
    df_val = df_companies.merge(df_mc_latest, on="company_id", how="left")
    df_val = df_val.merge(df_ratios_latest, on="company_id", how="left")
    df_val = df_val.merge(df_pe_5yr, on="company_id", how="left")
    
    # Compute FCF yield: FCF / market_cap_crore * 100
    df_val["FCF_yield_pct"] = np.where(
        (df_val["market_cap_crore"] > 0) & (df_val["free_cash_flow_cr"].notna()),
        (df_val["free_cash_flow_cr"] / df_val["market_cap_crore"]) * 100,
        np.nan
    )
    
    # Compute sector median P/E
    # Dropna or negative P/E for median calculation
    sector_medians = df_val[df_val["pe_ratio"] > 0].groupby("sector")["pe_ratio"].median().to_dict()
    
    # Map sector medians back
    df_val["sector_median_PE"] = df_val["sector"].map(sector_medians)
    
    # PE vs Sector Median %: (pe_ratio - sector_median) / sector_median * 100
    df_val["PE_vs_sector_median_pct"] = np.where(
        (df_val["sector_median_PE"] > 0) & (df_val["pe_ratio"].notna()),
        ((df_val["pe_ratio"] - df_val["sector_median_PE"]) / df_val["sector_median_PE"]) * 100,
        np.nan
    )
    
    # Apply valuation flags:
    # Caution if P/E > sector_median * 1.5
    # Discount if P/E < sector_median * 0.7
    # Fair otherwise
    def get_valuation_flag(row):
        pe = row["pe_ratio"]
        med = row["sector_median_PE"]
        if pd.isna(pe) or pd.isna(med) or pe is None or med is None or med <= 0:
            return "Fair"
        if pe > med * 1.5:
            return "Caution"
        if pe < med * 0.7:
            return "Discount"
        return "Fair"
        
    df_val["flag"] = df_val.apply(get_valuation_flag, axis=1)
    
    # Select columns for summary
    df_summary = df_val[[
        "company_id", "company_name", "sector", "pe_ratio", "pb_ratio", "ev_ebitda",
        "FCF_yield_pct", "5yr_median_PE", "PE_vs_sector_median_pct", "flag"
    ]].rename(columns={
        "pe_ratio": "P/E",
        "pb_ratio": "P/B",
        "ev_ebitda": "EV/EBITDA"
    })
    
    # Write output/valuation_summary.xlsx
    summary_path = os.path.join(OUTPUT_DIR, "valuation_summary.xlsx")
    df_summary.to_excel(summary_path, index=False, sheet_name="Valuation Summary")
    print(f"Saved: {summary_path}")
    
    # Generate output/valuation_flags.csv: only Caution or Discount
    df_flags = df_summary[df_summary["flag"].isin(["Caution", "Discount"])]
    flags_path = os.path.join(OUTPUT_DIR, "valuation_flags.csv")
    df_flags.to_csv(flags_path, index=False)
    print(f"Saved: {flags_path}")

if __name__ == "__main__":
    compute_valuation()
