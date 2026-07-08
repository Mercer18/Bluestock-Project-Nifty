import os
import yaml
import sqlite3
import pandas as pd

def load_screener_config(config_path: str) -> dict:
    """Loads analyst-editable filter thresholds from config/screener_config.yaml."""
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config.get("thresholds", {}) if config else {}

def load_screener_presets(config_path: str) -> dict:
    """Loads preset screener configurations from config/screener_config.yaml."""
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config.get("presets", {}) if config else {}

class ScreenerEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def load_base_data(self) -> pd.DataFrame:
        """Loads and merges financial_ratios, market_cap, profitandloss, and sectors into a single DataFrame."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at: {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        
        # Load ratios
        df_ratios = pd.read_sql_query("SELECT * FROM financial_ratios", conn)
        
        # Load market cap
        df_mc = pd.read_sql_query(
            "SELECT company_id, year, market_cap_crore, enterprise_value_crore, "
            "pe_ratio, pb_ratio, ev_ebitda, dividend_yield_pct FROM market_cap", 
            conn
        )
        
        # Load profit and loss (for sales and net profit)
        df_pl = pd.read_sql_query(
            "SELECT company_id, year, sales, net_profit FROM profitandloss", 
            conn
        )
        
        # Load sectors and company names
        df_sec = pd.read_sql_query(
            "SELECT c.id as company_id, c.company_name, s.broad_sector, s.sub_sector "
            "FROM companies c "
            "LEFT JOIN sectors s ON c.id = s.company_id", 
            conn
        )
        
        conn.close()
        
        # Merge datasets
        df = pd.merge(df_ratios, df_sec, on="company_id", how="left")
        df = pd.merge(df, df_mc, on=["company_id", "year"], how="left")
        df = pd.merge(df, df_pl, on=["company_id", "year"], how="left")
        
        # Load CAGR data to get sales_cagr_3yr (3-year Revenue CAGR)
        from src.analytics.cagr import CAGRCalculationEngine
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        cagr_log = os.path.join(project_root, "output", "ratio_edge_cases.log")
        
        cagr_engine = CAGRCalculationEngine(db_path=self.db_path, log_path=cagr_log)
        df_cagr = cagr_engine.run_cagr_pipeline()
        
        # Select CAGR columns to merge
        df_cagr_sel = df_cagr[["company_id", "year", "sales_cagr_3yr"]].copy()
        df = pd.merge(df, df_cagr_sel, on=["company_id", "year"], how="left")
        
        # Compute de_declining_yoy
        df = df.sort_values(by=["company_id", "year"])
        df["prev_de"] = df.groupby("company_id")["debt_to_equity"].shift(1)
        df["de_declining_yoy"] = df.apply(
            lambda r: r["debt_to_equity"] < r["prev_de"] if r["debt_to_equity"] is not None and not pd.isna(r["debt_to_equity"]) and r["prev_de"] is not None and not pd.isna(r["prev_de"]) else False,
            axis=1
        )
        
        return df

    def apply_filters(self, df: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
        """Applies filters to the DataFrame based on specified thresholds (Day 15 & 16 logic)."""
        filtered_df = df.copy()
        
        filter_rules = [
            ("roe_min", ">=", "return_on_equity_pct"),
            ("de_max", "<=", "debt_to_equity"),
            ("fcf_min", ">=", "free_cash_flow_cr"),
            ("revenue_cagr_5yr_min", ">=", "revenue_cagr_5yr"),
            ("pat_cagr_5yr_min", ">=", "pat_cagr_5yr"),
            ("opm_min", ">=", "operating_profit_margin_pct"),
            ("pe_max", "<=", "pe_ratio"),
            ("pb_max", "<=", "pb_ratio"),
            ("dividend_yield_min", ">=", "dividend_yield_pct"),
            ("icr_min", ">=", "interest_coverage"),
            ("market_cap_min", ">=", "market_cap_crore"),
            ("net_profit_min", ">=", "net_profit"),
            ("eps_cagr_min", ">=", "eps_cagr_5yr"),
            ("asset_turnover_min", ">=", "asset_turnover"),
            ("sales_min", ">=", "sales"),
            # Day 16 additions
            ("dividend_payout_max", "<=", "dividend_payout_ratio_pct"),
            ("revenue_cagr_3yr_min", ">=", "sales_cagr_3yr"),
            ("de_declining_yoy", "==", "de_declining_yoy")
        ]
        
        for key, op, col in filter_rules:
            val = thresholds.get(key)
            if val is None or pd.isna(val):
                continue
            
            if key == "de_declining_yoy":
                if val is True:
                    filtered_df = filtered_df[filtered_df["de_declining_yoy"] == True]
                continue
                
            val = float(val)
            
            if key == "de_max":
                # D/E filter: automatically skip companies in Financials broad sector
                mask = (filtered_df["broad_sector"] == "Financials") | \
                       (filtered_df[col].isna()) | \
                       (filtered_df[col] <= val)
                filtered_df = filtered_df[mask]
            elif key == "icr_min":
                # ICR filter: treat 'Debt Free' label as ICR = infinity
                mask = (filtered_df["icr_label"] == "Debt Free") | \
                       (filtered_df[col].isna()) | \
                       (filtered_df[col] >= val)
                filtered_df = filtered_df[mask]
            else:
                if op == ">=":
                    filtered_df = filtered_df[filtered_df[col] >= val]
                elif op == "<=":
                    filtered_df = filtered_df[filtered_df[col] <= val]
                    
        # Sort by composite_quality_score descending
        if "composite_quality_score" in filtered_df.columns:
            filtered_df = filtered_df.sort_values(by="composite_quality_score", ascending=False)
            
        return filtered_df

    def run_preset(self, df_base: pd.DataFrame, preset_name: str, config_path: str, year: str = "2024-03") -> pd.DataFrame:
        """Loads thresholds for a preset and runs the filters on the base dataset for a specific year."""
        presets = load_screener_presets(config_path)
        thresholds = presets.get(preset_name, {})
        
        # Filter base data for target year
        df_yr = df_base[df_base["year"] == year].copy()
        
        return self.apply_filters(df_yr, thresholds)

if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(project_root, "data", "nifty100.db")
    cfg = os.path.join(project_root, "config", "screener_config.yaml")
    
    engine = ScreenerEngine(db_path=db)
    df_base = engine.load_base_data()
    print(f"Loaded base screener data: {len(df_base)} rows.")
    
    presets = load_screener_presets(cfg)
    print("\nPreset Screener Test Results (Latest Year 2024-03):")
    for name in presets.keys():
        df_res = engine.run_preset(df_base, name, cfg, year="2024-03")
        print(f"  Preset: {name:<25} -> {len(df_res)} matching companies.")
