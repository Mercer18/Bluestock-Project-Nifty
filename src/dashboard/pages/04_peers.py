"""
Peer Group Comparison Screen.
Implements dynamic Scatterpolar radar charts comparing constituent metrics against peer group averages.
"""

import os
import sys
import sqlite3
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Add src/ to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.dashboard.utils.db import get_companies, get_ratios, get_peers

st.set_page_config(page_title="Nifty 100 Analytics - Peer Comparison", layout="wide")

# Helper for safe formatting
def sf(val, fmt="{:.2f}", suffix=""):
    if val is None or pd.isna(val):
        return "N/A"
    try:
        return fmt.format(float(val)) + suffix
    except Exception:
        return "N/A"

st.markdown('<h1 style="color:#1F4E79; font-weight:bold;">👥 Peer Group Comparison Portal</h1>', unsafe_allow_html=True)

# Connect and load peer group names
conn_str = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "nifty100.db")
import sqlite3
conn = sqlite3.connect(os.path.abspath(conn_str))
df_peers_names = pd.read_sql_query("SELECT DISTINCT peer_group_name FROM peer_groups WHERE peer_group_name IS NOT NULL", conn)
conn.close()

peer_choice = st.selectbox("Select Industry Peer Group", sorted(df_peers_names["peer_group_name"].unique()))

if peer_choice:
    # Query peer list
    df_peer_list = get_peers(peer_choice)
    
    if len(df_peer_list) > 0:
        st.write(f"### **{peer_choice}** Industry Peer Matrix (FY 2024)")
        
        # Display side-by-side table
        df_disp = df_peer_list.copy()
        df_disp["Benchmark"] = df_disp["is_benchmark"].apply(lambda b: "⭐ Yes" if b == 1 or b is True else "No")
        df_disp["ROE %"] = df_disp["return_on_equity_pct"].apply(lambda v: sf(v, "{:.2f}", "%"))
        df_disp["D/E"] = df_disp["debt_to_equity"].apply(lambda v: sf(v, "{:.2f}", "x"))
        df_disp["ICR"] = df_disp["interest_coverage"].apply(lambda v: sf(v, "{:.2f}", "x"))
        df_disp["FCF (Cr)"] = df_disp["free_cash_flow_cr"].apply(lambda v: sf(v, "{:,.1f}"))
        df_disp["Sales CAGR 5Yr %"] = df_disp["revenue_cagr_5yr"].apply(lambda v: sf(v, "{:.2f}", "%"))
        df_disp["Composite Score"] = df_disp["composite_quality_score"].apply(lambda v: sf(v, "{:.1f}"))
        
        # Select columns to display
        df_disp_table = df_disp[[
            "company_id", "company_name", "ROE %", "D/E", "ICR", "FCF (Cr)", "Sales CAGR 5Yr %", "Composite Score", "Benchmark"
        ]].rename(columns={
            "company_id": "Ticker",
            "company_name": "Company Name"
        })
        
        st.dataframe(df_disp_table, use_container_width=True, hide_index=True)
        
        # Radar Chart Visualization
        st.write("")
        st.subheader("⚔️ Peer-Relative Radar Chart Overlay")
        
        # Select company from peer list to plot
        selected_co = st.selectbox("Select Company to Plot", sorted(df_peer_list["company_id"].unique()))
        
        # Get selected company row and group average
        co_row = df_peer_list[df_peer_list["company_id"] == selected_co].iloc[0]
        
        # We need ROCE for radar chart. Let's load ROCE for latest year dynamically
        conn = sqlite3.connect(os.path.abspath(conn_str))
        df_bs_latest = pd.read_sql_query("SELECT company_id, equity_capital, reserves, borrowings FROM balancesheet WHERE year = '2024-03'", conn)
        df_pl_latest = pd.read_sql_query("SELECT company_id, profit_before_tax, interest, net_profit_margin_pct FROM profitandloss WHERE year = '2024-03'", conn)
        conn.close()
        
        # Calculate ROCE for all companies in peer list
        df_roce = df_bs_latest.merge(df_pl_latest, on="company_id", how="inner")
        df_roce["roce"] = (df_roce["profit_before_tax"].fillna(0) + df_roce["interest"].fillna(0)) / (
            df_roce["equity_capital"].fillna(0) + df_roce["reserves"].fillna(0) + df_roce["borrowings"].fillna(0)
        ) * 100
        # Replace inf/nan
        df_roce["roce"] = df_roce["roce"].replace([np.inf, -np.inf], np.nan).fillna(0)
        
        # Merge ROCE into peer list
        df_peer_full = df_peer_list.merge(df_roce[["company_id", "roce", "net_profit_margin_pct"]], on="company_id", how="left")
        
        # Standardize features to percentile ranks (0-100) for a meaningful radar comparison
        radar_metrics = [
            "return_on_equity_pct", "roce", "net_profit_margin_pct", "debt_to_equity",
            "interest_coverage", "free_cash_flow_cr", "revenue_cagr_5yr", "composite_quality_score"
        ]
        
        # Fill missing values for calculation
        df_calc = df_peer_full.copy()
        for m in radar_metrics:
            df_calc[m] = df_calc[m].fillna(df_calc[m].median()).fillna(0)
            
        # Standardize using percentile rank
        df_ranks = df_calc.copy()
        for m in radar_metrics:
            if df_calc[m].std() > 0:
                # Rank relative to all 92 companies (global percentile) or peer group percentile?
                # Global percentile is more standard to show true scale
                df_ranks[m] = df_calc[m].rank(pct=True) * 100
            else:
                df_ranks[m] = 50.0
                
        co_ranks = df_ranks[df_ranks["company_id"] == selected_co].iloc[0]
        avg_ranks = df_ranks[radar_metrics].mean()
        
        # Radar axes
        axes = [
            "ROE", "ROCE", "Net Profit Margin", "D/E (Inverted)",
            "Interest Coverage", "FCF", "Revenue CAGR 5Y", "Composite Score"
        ]
        
        # Invert D/E percentile because lower D/E is better
        co_vals = [
            co_ranks["return_on_equity_pct"],
            co_ranks["roce"],
            co_ranks["net_profit_margin_pct"],
            100 - co_ranks["debt_to_equity"], # Invert D/E
            co_ranks["interest_coverage"],
            co_ranks["free_cash_flow_cr"],
            co_ranks["revenue_cagr_5yr"],
            co_ranks["composite_quality_score"]
        ]
        
        avg_vals = [
            avg_ranks["return_on_equity_pct"],
            avg_ranks["roce"],
            avg_ranks["net_profit_margin_pct"],
            100 - avg_ranks["debt_to_equity"], # Invert D/E
            avg_ranks["interest_coverage"],
            avg_ranks["free_cash_flow_cr"],
            avg_ranks["revenue_cagr_5yr"],
            avg_ranks["composite_quality_score"]
        ]
        
        # Plot Scatterpolar
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=co_vals + [co_vals[0]],
            theta=axes + [axes[0]],
            fill="toself",
            name=f"{selected_co} (Percentile)",
            line=dict(color="#1F4E79")
        ))
        
        fig.add_trace(go.Scatterpolar(
            r=avg_vals + [avg_vals[0]],
            theta=axes + [axes[0]],
            fill="toself",
            name="Peer Group Average",
            line=dict(color="#5B9BD5", dash="dash")
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100])
            ),
            showlegend=True,
            height=450,
            margin=dict(l=50, r=50, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
