import os
import sqlite3
import pandas as pd
import numpy as np

def calculate_npm(net_profit: float, sales: float) -> float | None:
    """
    Calculates Net Profit Margin (NPM) %.
    NPM = (Net Profit / Sales) * 100
    Returns None if sales is 0, negative, or None.
    """
    if sales is None or pd.isna(sales) or sales <= 0:
        return None
    if net_profit is None or pd.isna(net_profit):
        return None
    return float((net_profit / sales) * 100)

def calculate_opm(operating_profit: float, sales: float) -> float | None:
    """
    Calculates Operating Profit Margin (OPM) %.
    OPM = (Operating Profit / Sales) * 100
    Returns None if sales is 0, negative, or None.
    """
    if sales is None or pd.isna(sales) or sales <= 0:
        return None
    if operating_profit is None or pd.isna(operating_profit):
        return None
    return float((operating_profit / sales) * 100)

def calculate_roe(net_profit: float, equity_capital: float, reserves: float) -> float | None:
    """
    Calculates Return on Equity (ROE) %.
    ROE = (Net Profit / (Equity Capital + Reserves)) * 100
    Returns None if shareholders' equity (Equity + Reserves) <= 0 or if inputs are None.
    """
    if net_profit is None or pd.isna(net_profit):
        return None
    
    eq = equity_capital if equity_capital is not None and not pd.isna(equity_capital) else 0.0
    res = reserves if reserves is not None and not pd.isna(reserves) else 0.0
    
    # If both are None/NaN or sum to 0/negative
    if (equity_capital is None or pd.isna(equity_capital)) and (reserves is None or pd.isna(reserves)):
        return None
        
    equity = eq + res
    if equity <= 0:
        return None
        
    return float((net_profit / equity) * 100)

def calculate_roce(pbt: float, interest: float, equity_capital: float, reserves: float, borrowings: float) -> float | None:
    """
    Calculates Return on Capital Employed (ROCE) %.
    ROCE = (EBIT / (Equity Capital + Reserves + Borrowings)) * 100
    EBIT = PBT + Interest
    Returns None if Capital Employed <= 0 or if key inputs are missing.
    """
    # EBIT = PBT + Interest (defaulting missing interest or pbt to 0 if at least one exists)
    if (pbt is None or pd.isna(pbt)) and (interest is None or pd.isna(interest)):
        return None
    
    pbt_val = pbt if pbt is not None and not pd.isna(pbt) else 0.0
    int_val = interest if interest is not None and not pd.isna(interest) else 0.0
    ebit = pbt_val + int_val
    
    # Capital Employed
    eq = equity_capital if equity_capital is not None and not pd.isna(equity_capital) else 0.0
    res = reserves if reserves is not None and not pd.isna(reserves) else 0.0
    borr = borrowings if borrowings is not None and not pd.isna(borrowings) else 0.0
    
    if (equity_capital is None or pd.isna(equity_capital)) and \
       (reserves is None or pd.isna(reserves)) and \
       (borrowings is None or pd.isna(borrowings)):
        return None
        
    capital_employed = eq + res + borr
    if capital_employed <= 0:
        return None
        
    return float((ebit / capital_employed) * 100)

class ProfitabilityRatioEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.deviations = []

    def load_financial_data(self) -> pd.DataFrame:
        """
        Loads profitandloss and balancesheet records and joins them on company_id and year.
        Applies auto-healing for column-shifted raw rows.
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at: {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        
        # Load P&L (include expenses, other_income, depreciation for shift check/healing)
        pl_query = """
            SELECT company_id, year, sales, expenses, operating_profit, opm_percentage, 
                   other_income, interest, depreciation, profit_before_tax, net_profit 
            FROM profitandloss
        """
        df_pl = pd.read_sql_query(pl_query, conn)
        
        # Load Balance Sheet
        bs_query = "SELECT company_id, year, equity_capital, reserves, borrowings FROM balancesheet"
        df_bs = pd.read_sql_query(bs_query, conn)
        
        conn.close()
        
        # Merge on company_id and year
        df_merged = pd.merge(df_pl, df_bs, on=["company_id", "year"], how="inner")
        
        # Auto-detect and heal column shift anomaly
        healed_count = 0
        for idx, row in df_merged.iterrows():
            sales = row["sales"]
            expenses = row["expenses"]
            op = row["operating_profit"]
            opm_pct = row["opm_percentage"]
            
            if (sales is not None and sales > 0 and 
                expenses is not None and expenses > 0 and 
                op is not None and op > 0 and 
                opm_pct is not None):
                
                # Check if shifted: (sales - expenses) != operating_profit AND (sales - operating_profit) == opm_percentage
                if abs((sales - expenses) - op) > 5.0 and abs((sales - op) - opm_pct) <= 5.0:
                    healed_count += 1
                    # Shift columns back:
                    df_merged.at[idx, "expenses"] = op
                    df_merged.at[idx, "operating_profit"] = opm_pct
                    df_merged.at[idx, "opm_percentage"] = row["other_income"]
                    df_merged.at[idx, "other_income"] = row["interest"]
                    df_merged.at[idx, "interest"] = row["depreciation"]
                    df_merged.at[idx, "depreciation"] = expenses
                    
        if healed_count > 0:
            print(f"Auto-detected and healed {healed_count} shifted profitandloss records.")
            
        return df_merged

    def run_calculations(self) -> pd.DataFrame:
        """
        Runs calculations for NPM, OPM, ROE, and ROCE across all merged records.
        """
        df = self.load_financial_data()
        
        npm_list = []
        opm_list = []
        roe_list = []
        roce_list = []
        
        for _, row in df.iterrows():
            # NPM
            npm = calculate_npm(row["net_profit"], row["sales"])
            npm_list.append(npm)
            
            # OPM
            opm = calculate_opm(row["operating_profit"], row["sales"])
            opm_list.append(opm)
            
            # ROE
            roe = calculate_roe(row["net_profit"], row["equity_capital"], row["reserves"])
            roe_list.append(roe)
            
            # ROCE
            roce = calculate_roce(
                row["profit_before_tax"],
                row["interest"],
                row["equity_capital"],
                row["reserves"],
                row["borrowings"]
            )
            roce_list.append(roce)
            
            # OPM Cross-Validation (DQ-05)
            if opm is not None and row["opm_percentage"] is not None:
                source_opm = float(row["opm_percentage"])
                diff = abs(opm - source_opm)
                if diff > 1.0:
                    self.deviations.append({
                        "company_id": row["company_id"],
                        "year": row["year"],
                        "calculated_opm": round(opm, 2),
                        "source_opm": source_opm,
                        "deviation_pct": round(diff, 2)
                    })
                    
        df["computed_npm"] = npm_list
        df["computed_opm"] = opm_list
        df["computed_roe"] = roe_list
        df["computed_roce"] = roce_list
        
        return df

    def print_validation_report(self):
        """
        Calculates ratios, checks deviations, and prints verification summary.
        """
        df_results = self.run_calculations()
        print("\n=== SPRINT 2: PROFITABILITY RATIO ENGINE VALIDATION ===")
        print(f"Total company-year combinations evaluated: {len(df_results)}")
        print(f"Calculated NPM count: {df_results['computed_npm'].notna().sum()}")
        print(f"Calculated OPM count: {df_results['computed_opm'].notna().sum()}")
        print(f"Calculated ROE count: {df_results['computed_roe'].notna().sum()}")
        print(f"Calculated ROCE count: {df_results['computed_roce'].notna().sum()}")
        
        print(f"\nTotal OPM deviations (> 1.0% vs source) found: {len(self.deviations)}")
        if len(self.deviations) > 0:
            print("\nOPM Deviations Details:")
            for dev in self.deviations[:10]:
                print(f"  {dev['company_id']} ({dev['year']}): Calc OPM = {dev['calculated_opm']}% | Source OPM = {dev['source_opm']}% (Diff: {dev['deviation_pct']}%)")
            if len(self.deviations) > 10:
                print(f"  ... and {len(self.deviations) - 10} more deviations.")
        else:
            print("  All calculated OPM margins align perfectly with source files within ±1%!")

if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(project_root, "data", "nifty100.db")
    engine = ProfitabilityRatioEngine(db_path=db)
    engine.print_validation_report()
