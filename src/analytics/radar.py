import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def generate_radar_charts(db_path: str, output_dir: str):
    """Generates polar radar charts comparing companies to their peer group average or Nifty 100 average."""
    # Load base data using ScreenerEngine
    from src.screener.engine import ScreenerEngine
    screener = ScreenerEngine(db_path)
    df = screener.load_base_data()
    
    # Filter for the latest year (2024-03)
    df_latest = df[df["year"] == "2024-03"].copy()
    
    # Load peer group mapping
    conn = sqlite3.connect(db_path)
    df_peers = pd.read_sql_query("SELECT * FROM peer_groups", conn)
    conn.close()
    
    # Merge peer group info
    df_latest = pd.merge(df_latest, df_peers, on="company_id", how="left")
    
    # 8 Axes to plot
    axes = [
        "ROE", "ROCE", "NPM", "D/E", "FCF Score", "PAT CAGR 5Yr", "Revenue CAGR 5Yr", "Composite Score"
    ]
    
    metrics_cols = {
        "ROE": "return_on_equity_pct",
        "ROCE": "computed_roce",
        "NPM": "net_profit_margin_pct",
        "D/E": "debt_to_equity",
        "FCF Score": "free_cash_flow_cr",
        "PAT CAGR 5Yr": "pat_cagr_5yr",
        "Revenue CAGR 5Yr": "revenue_cagr_5yr",
        "Composite Score": "composite_quality_score"
    }
    
    # Scale all metrics from 0 to 100 across the universe for visual balance
    df_scaled = df_latest.copy()
    for label, col in metrics_cols.items():
        vals = df_latest[col].dropna()
        if len(vals) == 0:
            df_scaled[label] = 0.0
            continue
        p10 = np.percentile(vals, 10)
        p90 = np.percentile(vals, 90)
        
        # Invert D/E so that lower leverage yields a higher rating
        if label == "D/E":
            capped = df_latest[col].clip(lower=p10, upper=p90)
            denom = p90 - p10
            if denom == 0:
                df_scaled[label] = 100.0
            else:
                df_scaled[label] = 100.0 - ((capped - p10) / denom * 100.0)
        else:
            capped = df_latest[col].clip(lower=p10, upper=p90)
            denom = p90 - p10
            if denom == 0:
                df_scaled[label] = 50.0
            else:
                df_scaled[label] = (capped - p10) / denom * 100.0
                
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Calculate group averages
    group_averages = {}
    for group_name, df_group in df_scaled.groupby("peer_group_name"):
        group_averages[group_name] = df_group[axes].mean().values
        
    # Calculate global Nifty 100 average
    global_average = df_scaled[axes].mean().values
    
    # Setup plotting styles
    plt.rcParams['font.sans-serif'] = 'Calibri'
    plt.rcParams['font.family'] = 'sans-serif'
    
    # Number of variables
    N = len(axes)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1] # Close polar loop
    
    for _, row in df_scaled.iterrows():
        co = row["company_id"]
        group_name = row["peer_group_name"]
        
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        fig.patch.set_facecolor('#FAFAFA')
        ax.set_facecolor('#FFFFFF')
        
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        
        # Draw labels
        plt.xticks(angles[:-1], axes, color='#333333', size=9, fontweight='bold')
        
        # Radial grid ticks
        ax.set_rlabel_position(0)
        plt.yticks([25, 50, 75, 100], ["25", "50", "75", "100"], color="#999999", size=8)
        plt.ylim(0, 100)
        
        # Get values
        values = row[axes].values.tolist()
        values += values[:1]
        
        # Get reference overlays
        if group_name and not pd.isna(group_name) and group_name in group_averages:
            ref_values = group_averages[group_name].tolist()
            ref_label = f"{group_name} Avg"
        else:
            ref_values = global_average.tolist()
            ref_label = "Nifty 100 Avg"
        ref_values += ref_values[:1]
        
        # Plot company filled polygon
        ax.plot(angles, values, linewidth=2, linestyle='solid', color='#4F81BD', label=co)
        ax.fill(angles, values, color='#4F81BD', alpha=0.3)
        
        # Plot reference dashed line
        ax.plot(angles, ref_values, linewidth=1.5, linestyle='dashed', color='#C00000', label=ref_label)
        
        plt.title(f"{row['company_name']} ({co})", size=14, color='#111111', weight='bold', pad=25)
        plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1), frameon=True, facecolor='#FFFFFF', edgecolor='#D9D9D9')
        
        fig_path = os.path.join(output_dir, f"{co}_radar.png")
        plt.savefig(fig_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close()
        
    print(f"Generated radar charts for {len(df_scaled)} companies.")

if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(project_root, "data", "nifty100.db")
    out = os.path.join(project_root, "reports", "radar_charts")
    
    generate_radar_charts(db_path=db, output_dir=out)
