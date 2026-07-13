"""
NLP Analysis Text Parser.
Parses CAGR strings from analysis table using regex and cross-validates against calculated ratios.
"""

import os
import re
import sqlite3
import pandas as pd

# Resolve paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "nifty100.db")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

def parse_analysis_text():
    """Parses text fields using regex and saves results."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Load raw analysis table
    df_analysis = pd.read_sql_query("SELECT company_id, compounded_sales_growth, compounded_profit_growth, stock_price_cagr, roe FROM analysis", conn)
    
    # 2. Load computed ratios for latest year (2024-03) for cross-validation
    df_ratios = pd.read_sql_query(
        "SELECT company_id, revenue_cagr_5yr, pat_cagr_5yr, return_on_equity_pct "
        "FROM financial_ratios WHERE year = '2024-03'", conn
    )
    
    conn.close()
    
    pattern = re.compile(r"(\d+)\s*Years?:?\s*([\d.]+)%")
    
    parsed_records = []
    parse_failures = []
    
    fields = {
        "compounded_sales_growth": "sales_growth",
        "compounded_profit_growth": "profit_growth",
        "stock_price_cagr": "stock_cagr",
        "roe": "roe"
    }
    
    for idx, row in df_analysis.iterrows():
        company_id = row["company_id"]
        for field, metric_type in fields.items():
            val = row[field]
            if pd.isna(val) or val is None or str(val).strip() == "":
                continue
            
            # Find all matches in case there are multiple lines
            matches = pattern.findall(str(val))
            if not matches:
                # Log as failure
                parse_failures.append({
                    "company_id": company_id,
                    "field": field,
                    "raw_text": val
                })
            else:
                for period, pct_str in matches:
                    parsed_records.append({
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "period_years": int(period),
                        "value_pct": float(pct_str)
                    })
                    
    # Create parsed dataframe
    df_parsed = pd.DataFrame(parsed_records)
    parsed_path = os.path.join(OUTPUT_DIR, "analysis_parsed.csv")
    df_parsed.to_csv(parsed_path, index=False)
    print(f"Saved parsed records: {parsed_path}")
    
    # Create parse failures dataframe
    df_failures = pd.DataFrame(parse_failures)
    failures_path = os.path.join(OUTPUT_DIR, "parse_failures.csv")
    df_failures.to_csv(failures_path, index=False)
    print(f"Saved parse failures: {failures_path}")
    
    # 3. Cross-validate against computed ratios
    # We will match:
    # sales_growth at period 5 -> revenue_cagr_5yr
    # profit_growth at period 5 -> pat_cagr_5yr
    # roe at period 10 or latest -> return_on_equity_pct
    validation_rows = []
    
    for idx, row in df_parsed.iterrows():
        cid = row["company_id"]
        mtype = row["metric_type"]
        period = row["period_years"]
        val = row["value_pct"]
        
        # Get latest computed ratio
        comp_row = df_ratios[df_ratios["company_id"] == cid]
        if comp_row.empty:
            continue
            
        comp_row = comp_row.iloc[0]
        
        if mtype == "sales_growth" and period == 5:
            comp_val = comp_row["revenue_cagr_5yr"]
            if comp_val is not None and not pd.isna(comp_val):
                divergence = abs(val - comp_val)
                if divergence > 5.0:
                    print(f"[DIVERGENT] {cid} sales_growth 5yr: parsed={val}%, computed={comp_val:.2f}%, diff={divergence:.2f}%")
                    
        elif mtype == "profit_growth" and period == 5:
            comp_val = comp_row["pat_cagr_5yr"]
            if comp_val is not None and not pd.isna(comp_val):
                divergence = abs(val - comp_val)
                if divergence > 5.0:
                    print(f"[DIVERGENT] {cid} profit_growth 5yr: parsed={val}%, computed={comp_val:.2f}%, diff={divergence:.2f}%")

if __name__ == "__main__":
    parse_analysis_text()
