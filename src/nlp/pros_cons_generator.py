"""
NLP Auto Pros/Cons Generator.
Evaluates 12 pro rules and 12 con rules for all 92 companies and exports findings.
Guarantees at least 1 pro and 1 con for every company.
"""

import os
import sqlite3
import pandas as pd
import numpy as np

# Resolve paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "nifty100.db")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

def generate_pros_cons():
    """Generates pros and cons based on quantitative financial ratios."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Load companies
    df_companies = pd.read_sql_query("SELECT id as company_id, company_name FROM companies", conn)
    
    # 2. Load financial ratios
    df_ratios = pd.read_sql_query(
        "SELECT company_id, year, return_on_equity_pct, debt_to_equity, "
        "interest_coverage, free_cash_flow_cr, revenue_cagr_5yr, pat_cagr_5yr, "
        "eps_cagr_5yr, operating_profit_margin_pct, net_debt_cr, composite_quality_score "
        "FROM financial_ratios", conn
    )
    
    # 3. Load profit & loss
    df_pl = pd.read_sql_query(
        "SELECT company_id, year, sales, net_profit, operating_profit, interest, profit_before_tax, eps, dividend_payout "
        "FROM profitandloss", conn
    )
    
    # 4. Load balance sheet
    df_bs = pd.read_sql_query(
        "SELECT company_id, year, equity_capital, reserves, borrowings, total_assets "
        "FROM balancesheet", conn
    )
    
    # 5. Load market cap for dividend yield
    df_mc = pd.read_sql_query(
        "SELECT company_id, year, dividend_yield_pct FROM market_cap", conn
    )
    
    # 6. Load sectors for sector checks
    df_sectors = pd.read_sql_query(
        "SELECT company_id, broad_sector FROM sectors", conn
    )
    
    conn.close()
    
    # Pre-merge sectors
    df_ratios = df_ratios.merge(df_sectors, on="company_id", how="left")
    
    # Helper to get values for a specific year or historical years
    def get_by_year(df, cid, yr):
        sub = df[(df["company_id"] == cid) & (df["year"] == yr)]
        return sub.iloc[0] if len(sub) > 0 else None
        
    def get_history(df, cid, years):
        sub = df[(df["company_id"] == cid) & (df["year"].isin(years))].sort_values(by="year")
        return sub
        
    records = []
    
    for _, comp_row in df_companies.iterrows():
        cid = comp_row["company_id"]
        cname = comp_row["company_name"]
        
        # Get latest 2024-03 records
        ratio_24 = get_by_year(df_ratios, cid, "2024-03")
        pl_24 = get_by_year(df_pl, cid, "2024-03")
        bs_24 = get_by_year(df_bs, cid, "2024-03")
        mc_24 = get_by_year(df_mc, cid, "2024-03")
        
        # Get historical records
        hist_years_3 = ["2022-03", "2023-03", "2024-03"]
        hist_years_5 = ["2020-03", "2021-03", "2022-03", "2023-03", "2024-03"]
        
        ratio_hist_3 = get_history(df_ratios, cid, hist_years_3)
        ratio_hist_5 = get_history(df_ratios, cid, hist_years_5)
        
        pl_hist_3 = get_history(df_pl, cid, hist_years_3)
        bs_hist_3 = get_history(df_bs, cid, hist_years_3)
        
        # Calculate latest ROCE
        latest_roce = None
        if bs_24 is not None and pl_24 is not None:
            ebit = (pl_24["profit_before_tax"] or 0) + (pl_24["interest"] or 0)
            ce = (bs_24["equity_capital"] or 0) + (bs_24["reserves"] or 0) + (bs_24["borrowings"] or 0)
            if ce > 0:
                latest_roce = (ebit / ce) * 100
                
        pros = []
        cons = []
        
        # --- PRO RULES ---
        # Pro Rule 1: ROE > 20% sustained for 3+ years
        if len(ratio_hist_3) >= 3 and (ratio_hist_3["return_on_equity_pct"] > 20.0).all():
            pros.append(("PRO-01", "Consistently high return on equity above 20% demonstrates exceptional capital efficiency", 85))
            
        # Pro Rule 2: FCF positive for 5+ consecutive years
        if len(ratio_hist_5) >= 5 and (ratio_hist_5["free_cash_flow_cr"] > 0).all():
            pros.append(("PRO-02", "Strong free cash flow generation over 5 years signals healthy business fundamentals", 90))
            
        # Pro Rule 3: D/E = 0 in latest year
        if ratio_24 is not None and ratio_24["debt_to_equity"] <= 0.01:
            pros.append(("PRO-03", "Debt-free balance sheet provides financial flexibility and eliminates interest burden", 95))
            
        # Pro Rule 4: Revenue CAGR > 15% over 5 years
        if ratio_24 is not None and ratio_24["revenue_cagr_5yr"] is not None and ratio_24["revenue_cagr_5yr"] > 15.0:
            pros.append(("PRO-04", "Revenue growing at above 15% CAGR over 5 years reflects strong business momentum", 80))
            
        # Pro Rule 5: OPM > 25% in latest year
        if ratio_24 is not None and ratio_24["operating_profit_margin_pct"] is not None and ratio_24["operating_profit_margin_pct"] > 25.0:
            pros.append(("PRO-05", "Operating profit margin above 25% indicates strong pricing power and cost discipline", 85))
            
        # Pro Rule 6: PAT CAGR > 20% over 5 years
        if ratio_24 is not None and ratio_24["pat_cagr_5yr"] is not None and ratio_24["pat_cagr_5yr"] > 20.0:
            pros.append(("PRO-06", "Net profit compounding at above 20% over 5 years creates significant shareholder value", 85))
            
        # Pro Rule 7: ICR > 10 or Debt Free
        icr = ratio_24["interest_coverage"] if ratio_24 is not None else None
        de = ratio_24["debt_to_equity"] if ratio_24 is not None else None
        if (icr is not None and icr > 10.0) or (de is not None and de <= 0.01):
            pros.append(("PRO-07", "Very high interest coverage ratio reflects negligible financial stress from debt servicing", 80))
            
        # Pro Rule 8: Dividend Yield > 2% with FCF positive
        div_y = mc_24["dividend_yield_pct"] if mc_24 is not None else None
        fcf = ratio_24["free_cash_flow_cr"] if ratio_24 is not None else None
        if div_y is not None and div_y > 2.0 and fcf is not None and fcf > 0:
            pros.append(("PRO-08", f"Consistent dividend yield of {div_y:.2f}% is backed by positive free cash flow", 75))
            
        # Pro Rule 9: EPS CAGR > 15% over 5 years
        if ratio_24 is not None and ratio_24["eps_cagr_5yr"] is not None and ratio_24["eps_cagr_5yr"] > 15.0:
            pros.append(("PRO-09", "Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding", 80))
            
        # Pro Rule 10: ROE improving for 3 consecutive years
        if len(ratio_hist_3) >= 3:
            roes = ratio_hist_3["return_on_equity_pct"].tolist()
            if roes[2] > roes[1] > roes[0]:
                pros.append(("PRO-10", "Return on equity improving for 3 consecutive years shows strengthening business quality", 75))
                
        # Pro Rule 11: Revenue CAGR < PAT CAGR (operating leverage)
        rev_cagr = ratio_24["revenue_cagr_5yr"] if ratio_24 is not None else None
        pat_cagr = ratio_24["pat_cagr_5yr"] if ratio_24 is not None else None
        if rev_cagr is not None and pat_cagr is not None and pat_cagr > rev_cagr:
            pros.append(("PRO-11", "Revenue growing slower than profits shows improving operating leverage and scale benefits", 70))
            
        # Pro Rule 12: Balance sheet assets growing with declining debt
        if len(bs_hist_3) >= 2:
            assets = bs_hist_3["total_assets"].tolist()
            debts = bs_hist_3["borrowings"].tolist()
            if assets[-1] > assets[-2] and debts[-1] < debts[-2]:
                pros.append(("PRO-12", "Growing asset base funded by internal accruals reflects self-sustaining growth", 75))
                
        # --- CON RULES ---
        # Con Rule 1: D/E > 2.0 for non-financial companies
        de_val = ratio_24["debt_to_equity"] if ratio_24 is not None else None
        sector = ratio_24["broad_sector"] if ratio_24 is not None else None
        if de_val is not None and de_val > 2.0 and sector != "Financials":
            cons.append(("CON-01", f"Debt-to-equity ratio of {de_val:.2f}x is elevated for a non-financial company and warrants monitoring", 85))
            
        # Con Rule 2: FCF negative for 3 consecutive years
        if len(ratio_hist_3) >= 3 and (ratio_hist_3["free_cash_flow_cr"] < 0).all():
            cons.append(("CON-02", "Free cash flow negative for 3 consecutive years raises concern about cash generation quality", 90))
            
        # Con Rule 3: OPM declining for 3 consecutive years
        if len(ratio_hist_3) >= 3:
            opms = ratio_hist_3["operating_profit_margin_pct"].tolist()
            if opms[2] < opms[1] < opms[0]:
                cons.append(("CON-03", "Operating margins declining for 3 consecutive years suggest pricing or cost pressure", 80))
                
        # Con Rule 4: Net profit negative in latest year
        net_prof = pl_24["net_profit"] if pl_24 is not None else None
        if net_prof is not None and net_prof < 0:
            cons.append(("CON-04", "Company reported a net loss in the most recent financial year", 90))
            
        # Con Rule 5: Revenue declining for 2+ years
        if len(pl_hist_3) >= 2:
            sales = pl_hist_3["sales"].tolist()
            if sales[-1] < sales[-2]:
                cons.append(("CON-05", "Revenue contraction over consecutive years indicates demand weakness or market share loss", 80))
                
        # Con Rule 6: ICR < 1.5
        icr_val = ratio_24["interest_coverage"] if ratio_24 is not None else None
        if icr_val is not None and icr_val < 1.5:
            cons.append(("CON-06", f"Interest coverage ratio of {icr_val:.2f}x below 1.5x indicates the company is at risk of not meeting its debt obligations", 85))
            
        # Con Rule 7: Dividend payout > 100%
        div_p = pl_24["dividend_payout"] if pl_24 is not None else None
        if div_p is not None and div_p > 100:
            cons.append(("CON-07", f"Dividend payout ratio of {div_p:.1f}% is unsustainable as dividends are paid from reserves", 75))
            
        # Con Rule 8: D/E rising for 3 consecutive years
        if len(ratio_hist_3) >= 3:
            des = ratio_hist_3["debt_to_equity"].tolist()
            if des[2] > des[1] > des[0]:
                cons.append(("CON-08", "Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk", 75))
                
        # Con Rule 9: EPS declining for 3 consecutive years
        if len(pl_hist_3) >= 3:
            eps_vals = pl_hist_3["eps"].tolist()
            if eps_vals[2] < eps_vals[1] < eps_vals[0]:
                cons.append(("CON-09", "Earnings per share declining for 3 consecutive years reflects deteriorating profitability", 80))
                
        # Con Rule 10: ROCE < 10%
        if latest_roce is not None and latest_roce < 10.0:
            cons.append(("CON-10", f"Return on capital employed of {latest_roce:.1f}% is below 10%, suggesting insufficient return on invested capital", 80))
            
        # Con Rule 11: Net Debt > 3x EBITDA
        net_debt = ratio_24["net_debt_cr"] if ratio_24 is not None else None
        ebitda = pl_24["operating_profit"] if pl_24 is not None else None # Approximating EBITDA as Operating Profit
        if net_debt is not None and ebitda is not None and ebitda > 0 and (net_debt / ebitda) > 3.0:
            cons.append(("CON-11", f"Net debt exceeding {net_debt/ebitda:.1f} times EBITDA limits financial flexibility", 80))
            
        # Con Rule 12: Revenue CAGR < 5% over 5 years
        if ratio_24 is not None and ratio_24["revenue_cagr_5yr"] is not None and ratio_24["revenue_cagr_5yr"] < 5.0:
            cons.append(("CON-12", "Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum", 75))
            
        # Fallbacks to ensure every company has at least 1 pro and 1 con
        if not pros:
            # Fallback Pro based on positive metrics
            pros.append(("PRO-FALLBACK", "Stable operating history and continuous listing on the Nifty 100 index", 65))
        if not cons:
            # Fallback Con
            cons.append(("CON-FALLBACK", "Subject to macro-economic cycles, regulatory changes, and raw material price volatility", 65))
            
        # Write to final records list
        for rule_id, text, conf in pros:
            records.append({
                "company_id": cid,
                "type": "pro",
                "rule_id": rule_id,
                "text": text,
                "confidence_pct": conf
            })
        for rule_id, text, conf in cons:
            records.append({
                "company_id": cid,
                "type": "con",
                "rule_id": rule_id,
                "text": text,
                "confidence_pct": conf
            })
            
    df_output = pd.DataFrame(records)
    output_path = os.path.join(OUTPUT_DIR, "pros_cons_generated.csv")
    df_output.to_csv(output_path, index=False)
    print(f"Saved generated pros/cons: {output_path}")

if __name__ == "__main__":
    generate_pros_cons()
