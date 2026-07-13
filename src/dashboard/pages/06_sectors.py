"""
Sector Analysis Screen.
Implements dynamic bubble charts (Revenue vs. ROE vs. Market Cap) and sub-sector median bar charts.
"""

import os
import sys
import sqlite3
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Add src/ to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.dashboard.utils.db import get_companies, get_ratios, get_valuation

st.set_page_config(page_title="Nifty 100 Analytics - Sectors", layout="wide")

# Helper for safe formatting
def sf(val, fmt="{:.2f}", suffix=""):
    if val is None or pd.isna(val):
        return "N/A"
    try:
        return fmt.format(float(val)) + suffix
    except Exception:
        return "N/A"

st.markdown('<h1 style="color:#1F4E79; font-weight:bold;">🏢 Sector & Sub-sector Intelligence</h1>', unsafe_allow_html=True)

# Connect and load sector list
conn_str = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "nifty100.db")
import sqlite3
conn = sqlite3.connect(os.path.abspath(conn_str))
df_sectors_list = pd.read_sql_query("SELECT DISTINCT broad_sector FROM sectors WHERE broad_sector IS NOT NULL", conn)
conn.close()

sector_choice = st.selectbox("Select Sector", sorted(df_sectors_list["broad_sector"].unique()), key="sector_ana")

if sector_choice:
    # Load companies in the selected sector for latest year
    conn = sqlite3.connect(os.path.abspath(conn_str))
    query = (
        "SELECT r.company_id, c.company_name, s.sub_sector, "
        "pl.sales, r.return_on_equity_pct as roe, mc.market_cap_crore, "
        "r.debt_to_equity as de, r.composite_quality_score as score "
        "FROM financial_ratios r "
        "JOIN companies c ON r.company_id = c.id "
        "JOIN sectors s ON r.company_id = s.company_id "
        "JOIN profitandloss pl ON r.company_id = pl.company_id AND r.year = pl.year "
        "JOIN market_cap mc ON r.company_id = mc.company_id AND r.year = mc.year "
        "WHERE s.broad_sector = ? AND r.year = '2024-03'"
    )
    df_sec = pd.read_sql_query(query, conn, params=(sector_choice,))
    conn.close()
    
    if len(df_sec) > 0:
        # Convert values to standard Cr representation
        df_sec["Revenue (INR Cr)"] = df_sec["sales"] / 10.0
        df_sec["ROE %"] = df_sec["roe"]
        df_sec["Market Cap (Cr)"] = df_sec["market_cap_crore"]
        df_sec["Sub-sector"] = df_sec["sub_sector"]
        
        # 1. Bubble Chart
        st.write("#### Revenue vs. Return on Equity vs. Market Capitalization")
        fig1 = px.scatter(
            df_sec,
            x="Revenue (INR Cr)",
            y="ROE %",
            size="Market Cap (Cr)",
            color="Sub-sector",
            hover_name="company_name",
            text="company_id",
            size_max=50,
            height=400,
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig1.update_traces(textposition="top center")
        fig1.update_layout(margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig1, use_container_width=True)
        
        st.write("")
        
        # 2. Sector Median KPI Bar Chart
        st.write(f"#### Sub-sector Median ROE % & Quality Score Summary")
        df_medians = df_sec.groupby("Sub-sector")[["ROE %", "score"]].median().reset_index()
        
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df_medians["Sub-sector"],
            y=df_medians["ROE %"],
            name="Median ROE %",
            marker_color="#1F4E79"
        ))
        fig2.add_trace(go.Bar(
            x=df_medians["Sub-sector"],
            y=df_medians["score"],
            name="Median Quality Score",
            marker_color="#E26B0A"
        ))
        fig2.update_layout(
            barmode="group",
            height=320,
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning(f"No records found for the sector {sector_choice} in the database for FY 2024.")
