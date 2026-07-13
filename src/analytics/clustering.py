"""
KMeans Clustering and Portfolio Statistics Module.
Performs clustering, profiles clusters, checks for outliers, and generates correlation heatmaps.
"""

import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Resolve paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "nifty100.db")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")

def run_clustering_and_stats():
    """Implements KMeans clustering, profiles archetypes, and reports statistics."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Load latest ratios (2024-03) and join sector
    df_ratios = pd.read_sql_query(
        "SELECT r.company_id, r.return_on_equity_pct, r.debt_to_equity, "
        "r.interest_coverage, r.free_cash_flow_cr, r.revenue_cagr_5yr, "
        "r.pat_cagr_5yr, r.eps_cagr_5yr, r.operating_profit_margin_pct, "
        "r.net_profit_margin_pct, r.composite_quality_score, s.broad_sector as sector "
        "FROM financial_ratios r "
        "LEFT JOIN sectors s ON r.company_id = s.company_id "
        "WHERE r.year = '2024-03'", conn
    )
    
    # Load FCF values to compute FCF CAGR dynamically
    df_fcf_all = pd.read_sql_query(
        "SELECT company_id, year, free_cash_flow_cr FROM financial_ratios "
        "WHERE year IN ('2019-03', '2024-03')", conn
    )
    conn.close()
    
    # Compute 5-year FCF CAGR
    fcf_cagrs = {}
    for cid in df_ratios["company_id"].unique():
        sub = df_fcf_all[df_fcf_all["company_id"] == cid]
        f19 = sub[sub["year"] == "2019-03"]["free_cash_flow_cr"].values
        f24 = sub[sub["year"] == "2024-03"]["free_cash_flow_cr"].values
        if len(f19) > 0 and len(f24) > 0 and not pd.isna(f19[0]) and not pd.isna(f24[0]):
            s_val = f19[0]
            e_val = f24[0]
            if s_val > 0 and e_val > 0:
                fcf_cagrs[cid] = float((e_val / s_val) ** 0.2 - 1.0) * 100.0
            else:
                fcf_cagrs[cid] = np.nan
        else:
            fcf_cagrs[cid] = np.nan
            
    df_ratios["fcf_cagr_5yr"] = df_ratios["company_id"].map(fcf_cagrs)
    
    # Features for clustering
    features = [
        "return_on_equity_pct", "debt_to_equity", "revenue_cagr_5yr", 
        "fcf_cagr_5yr", "operating_profit_margin_pct"
    ]
    
    df_feat = df_ratios[["company_id", "sector"] + features].copy()
    
    # Impute missing values with sector median
    for col in features:
        # Group by sector and compute median
        sector_medians = df_feat.groupby("sector")[col].transform("median")
        df_feat[col] = df_feat[col].fillna(sector_medians)
        # Global fallback if sector median is also NaN
        df_feat[col] = df_feat[col].fillna(df_feat[col].median())
        
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_feat[features])
    
    # 2. Generate Elbow Plot (k from 2 to 10)
    inertias = []
    k_range = range(2, 11)
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)
        
    plt.figure(figsize=(8, 5))
    plt.plot(k_range, inertias, marker="o", linestyle="--", color="#1F4E79")
    plt.xlabel("Number of Clusters (k)")
    plt.ylabel("Inertia / Within-Cluster Sum of Squares")
    plt.title("K-Means Elbow Curve")
    plt.grid(True)
    elbow_path = os.path.join(REPORTS_DIR, "elbow_plot.png")
    plt.savefig(elbow_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved Elbow Plot: {elbow_path}")
    
    # 3. Fit K-Means with k=5
    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    df_feat["cluster_id"] = kmeans.fit_predict(X_scaled)
    
    # Calculate distance from centroid
    centroids = kmeans.cluster_centers_
    distances = []
    for idx, row_scaled in enumerate(X_scaled):
        cluster_id = df_feat.iloc[idx]["cluster_id"]
        centroid = centroids[cluster_id]
        dist = np.linalg.norm(row_scaled - centroid)
        distances.append(dist)
    df_feat["distance_from_centroid"] = distances
    
    # Profile clusters to assign descriptive names
    cluster_means = df_feat.groupby("cluster_id")[features].mean()
    
    # Map descriptive names based on centroids
    # Let's map dynamically:
    # Cluster with highest ROE and OPM -> High-Quality Compounders
    # Cluster with highest D/E -> Value Cyclicals
    # Cluster with lowest ROE / lowest interest coverage -> Distressed or Turnaround
    # Cluster with high growth cagr but moderate ROE -> Emerging Growth
    # Cluster with moderate indicators across -> Defensive Dividend Payers
    cluster_names = {}
    sorted_roe = cluster_means["return_on_equity_pct"].sort_values()
    sorted_de = cluster_means["debt_to_equity"].sort_values()
    
    # Identify clusters
    hq_id = sorted_roe.index[-1] # Highest ROE
    distressed_id = sorted_roe.index[0] # Lowest ROE
    high_debt_id = sorted_de.index[-1] # Highest Debt
    
    remaining = [i for i in range(5) if i not in [hq_id, distressed_id, high_debt_id]]
    
    # Between remaining two, one with higher CAGR is Emerging Growth, other is Defensive Dividend Payers
    if len(remaining) >= 2:
        c1, c2 = remaining[0], remaining[1]
        c1_growth = cluster_means.loc[c1, "revenue_cagr_5yr"]
        c2_growth = cluster_means.loc[c2, "revenue_cagr_5yr"]
        if c1_growth > c2_growth:
            eg_id, def_id = c1, c2
        else:
            eg_id, def_id = c2, c1
    else:
        eg_id = remaining[0] if len(remaining) > 0 else 3
        def_id = 4
        
    cluster_names[hq_id] = "High-Quality Compounders"
    cluster_names[distressed_id] = "Distressed or Turnaround"
    cluster_names[high_debt_id] = "Value Cyclicals"
    cluster_names[eg_id] = "Emerging Growth"
    cluster_names[def_id] = "Defensive Dividend Payers"
    
    df_feat["cluster_name"] = df_feat["cluster_id"].map(cluster_names)
    
    # Save output/cluster_labels.csv
    labels_path = os.path.join(OUTPUT_DIR, "cluster_labels.csv")
    df_feat[["company_id", "cluster_id", "cluster_name", "distance_from_centroid"]].to_csv(labels_path, index=False)
    print(f"Saved Cluster Labels: {labels_path}")
    
    # 4. Generate Correlation Heatmap
    # 10 KPIs: ROE, DE, Interest Coverage, FCF, Revenue CAGR 5yr, PAT CAGR 5yr, EPS CAGR 5yr, OPM, NPM, Quality Score
    kpi_cols = [
        "return_on_equity_pct", "debt_to_equity", "interest_coverage", 
        "free_cash_flow_cr", "revenue_cagr_5yr", "pat_cagr_5yr", 
        "eps_cagr_5yr", "operating_profit_margin_pct", "net_profit_margin_pct", 
        "composite_quality_score"
    ]
    df_corr_data = df_ratios[kpi_cols].copy()
    
    # Fill missing values with column median
    df_corr_data = df_corr_data.fillna(df_corr_data.median())
    
    # Compute correlation
    corr_matrix = df_corr_data.corr(method="pearson")
    
    # Rename for heatmap aesthetics
    nice_labels = [
        "ROE %", "D/E Ratio", "Interest Coverage", "FCF (Cr)", 
        "Sales CAGR 5Y", "PAT CAGR 5Y", "EPS CAGR 5Y", "OPM %", "NPM %", "Quality Score"
    ]
    corr_matrix.columns = nice_labels
    corr_matrix.index = nice_labels
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_matrix, annot=True, cmap="coolwarm", fmt=".2f", vmin=-1.0, vmax=1.0, square=True)
    plt.title("Pearson Correlation Heatmap of 10 Financial KPIs")
    heatmap_path = os.path.join(REPORTS_DIR, "correlation_heatmap.png")
    plt.savefig(heatmap_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved Correlation Heatmap: {heatmap_path}")
    
    # 5. Outlier Detection: Z-Score per sector
    outliers = []
    for col in kpi_cols:
        for sector_name in df_ratios["sector"].dropna().unique():
            sub = df_ratios[df_ratios["sector"] == sector_name]
            mean_val = sub[col].mean()
            std_val = sub[col].std()
            if pd.notna(std_val) and std_val > 0:
                for idx, row in sub.iterrows():
                    z = (row[col] - mean_val) / std_val
                    if abs(z) > 3.0:
                        outliers.append({
                            "company_id": row["company_id"],
                            "sector": sector_name,
                            "metric": col,
                            "value": row[col],
                            "sector_mean": mean_val,
                            "sector_std": std_val,
                            "z_score": z
                        })
    df_outliers = pd.DataFrame(outliers)
    outliers_path = os.path.join(OUTPUT_DIR, "outlier_report.csv")
    df_outliers.to_csv(outliers_path, index=False)
    print(f"Saved Outlier Report: {outliers_path}")
    
    # 6. Generate output/portfolio_stats.csv
    # Percentiles: P10, P25, P50, P75, P90, Mean, Std for each KPI
    stats_records = []
    for col in kpi_cols:
        col_data = df_ratios[col].dropna()
        if len(col_data) > 0:
            stats_records.append({
                "kpi": col,
                "P10": np.percentile(col_data, 10),
                "P25": np.percentile(col_data, 25),
                "P50": np.percentile(col_data, 50),
                "P75": np.percentile(col_data, 75),
                "P90": np.percentile(col_data, 90),
                "Mean": col_data.mean(),
                "Std": col_data.std()
            })
    df_stats = pd.DataFrame(stats_records)
    stats_path = os.path.join(OUTPUT_DIR, "portfolio_stats.csv")
    df_stats.to_csv(stats_path, index=False)
    print(f"Saved Portfolio Stats: {stats_path}")

if __name__ == "__main__":
    run_clustering_and_stats()
