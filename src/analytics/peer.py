import os
import sqlite3
import pandas as pd
import numpy as np
from src.screener.engine import ScreenerEngine

def get_company_peer_group(company_id: str, db_path: str) -> str:
    """Returns the peer group name for a given company, or 'No peer group assigned' if not mapped."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT peer_group_name FROM peer_groups WHERE company_id = ?", (company_id,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return res[0]
    return "No peer group assigned"

def calculate_percent_rank(series: pd.Series, invert: bool = False) -> pd.Series:
    """Calculates percentile rank matching Excel's PERCENTRANK.INC behavior."""
    non_nulls = series.dropna()
    n = len(non_nulls)
    if n == 0:
        return pd.Series(np.nan, index=series.index)
    if n == 1:
        return pd.Series(1.0, index=series.index)
        
    if invert:
        # Lower value = higher percentile (e.g. D/E)
        ranks = non_nulls.rank(method="min", ascending=False)
    else:
        ranks = non_nulls.rank(method="min", ascending=True)
        
    min_r = ranks.min()
    max_r = ranks.max()
    
    if max_r == min_r:
        res = pd.Series(1.0, index=non_nulls.index)
    else:
        res = (ranks - min_r) / (max_r - min_r)
        
    return res.reindex(series.index)

class PeerPercentileEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def run_peer_pipeline(self) -> int:
        """Computes percentiles for all peer groups and inserts them into peer_percentiles table."""
        # Load unified ratios data
        screener = ScreenerEngine(self.db_path)
        df_base = screener.load_base_data()
        
        # Load peer groups from database
        conn = sqlite3.connect(self.db_path)
        df_peers = pd.read_sql_query("SELECT * FROM peer_groups", conn)
        conn.close()
        
        # Join peer group mapping
        df = pd.merge(df_base, df_peers, on="company_id", how="inner")
        
        # Metrics to rank (10 metrics)
        metrics_mapping = [
            ("ROE", "return_on_equity_pct", False),
            ("ROCE", "computed_roce", False),
            ("NPM", "net_profit_margin_pct", False),
            ("D/E", "debt_to_equity", True), # Inverted
            ("FCF", "free_cash_flow_cr", False),
            ("PAT CAGR 5Yr", "pat_cagr_5yr", False),
            ("Revenue CAGR 5Yr", "revenue_cagr_5yr", False),
            ("EPS CAGR 5Yr", "eps_cagr_5yr", False),
            ("Interest Coverage", "interest_coverage", False),
            ("Asset Turnover", "asset_turnover", False)
        ]
        
        insert_records = []
        
        # Group by peer group and year
        for (group_name, year), df_sub in df.groupby(["peer_group_name", "year"]):
            df_sub = df_sub.copy()
            
            # Compute percentiles for each metric
            for metric_label, col_name, invert in metrics_mapping:
                if col_name not in df_sub.columns:
                    continue
                    
                pct_ranks = calculate_percent_rank(df_sub[col_name], invert=invert)
                
                for idx, row in df_sub.iterrows():
                    co = row["company_id"]
                    val = row[col_name]
                    rank_val = pct_ranks.loc[idx]
                    
                    # Convert NaN to None for SQLite insertion
                    db_val = float(val) if val is not None and not pd.isna(val) else None
                    db_rank = float(rank_val) if rank_val is not None and not pd.isna(rank_val) else None
                    
                    insert_records.append((
                        co,
                        group_name,
                        metric_label,
                        db_val,
                        db_rank,
                        year
                    ))
                    
        # Write to SQLite
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM peer_percentiles")
        cursor.executemany(
            "INSERT INTO peer_percentiles (company_id, peer_group_name, metric, value, percentile_rank, year) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            insert_records
        )
        conn.commit()
        conn.close()
        
        print(f"Populated peer_percentiles table with {len(insert_records)} records.")
        return len(insert_records)

if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(project_root, "data", "nifty100.db")
    
    # Test fallback message
    print("Testing company mapping:")
    print("  INFY ->", get_company_peer_group("INFY", db))
    print("  XYZ (Invalid) ->", get_company_peer_group("XYZ", db))
    
    engine = PeerPercentileEngine(db_path=db)
    engine.run_peer_pipeline()
