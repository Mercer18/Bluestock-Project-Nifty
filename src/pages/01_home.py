"""
Home Screen for Nifty 100 Analytics Dashboard.
Displays high-level KPI tiles, sector weights donut chart, and top-ranking quality leaders.
"""

import os
import sys
import streamlit as st
import plotly.express as px
import pandas as pd

# Add src/ to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.db import get_connection, get_companies, get_ratios, get_valuation

st.set_page_config(page_title="Nifty 100 Analytics - Home", layout="wide")

st.markdown('<h1 style="color:#1F4E79; font-weight:bold;">🏛️ Nifty 100 Portfolio Overview</h1>', unsafe_allow_html=True)
st.write("Welcome to the Bluestock Nifty 100 Financial Intelligence Platform dashboard.")

# Load datasets
df_comp = get_companies()
df_val = get_valuation()

# Sidebar year selector
selected_year = st.sidebar.selectbox("Select Year", ["2024-03", "2023-03", "2022-03", "2021-03", "2020-03", "2019-03"])

# Filter ratios and valuation for chosen year
# We will query all ratios dynamically or filter from db
conn = get_connection()
df_ratios_yr = pd.read_sql_query("SELECT * FROM financial_ratios WHERE year = ?", conn, params=(selected_year,))
df_mc_yr = pd.read_sql_query("SELECT * FROM market_cap WHERE year = ?", conn, params=(selected_year,))
conn.close()

# Merge for KPIs
df_kpis = df_comp.merge(df_ratios_yr, left_on="company_id", right_on="company_id", how="inner")
df_kpis = df_kpis.merge(df_mc_yr, left_on="company_id", right_on="company_id", how="inner")

if len(df_kpis) > 0:
    # 6 KPI Tiles
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    avg_roe = df_kpis["return_on_equity_pct"].mean()
    med_pe = df_kpis["pe_ratio"].median()
    med_de = df_kpis["debt_to_equity"].median()
    total_cos = len(df_kpis)
    med_cagr = df_kpis["revenue_cagr_5yr"].median()
    # Debt free: DE <= 0.01 (excluding financials for standard metrics if wanted, but globally here)
    debt_free_count = len(df_kpis[df_kpis["debt_to_equity"] <= 0.01])
    
    def fmt(val, f="{:.2f}", suf=""):
        if pd.isna(val) or val is None:
            return "N/A"
        return f.format(val) + suf

    with col1:
        st.metric("Average ROE %", fmt(avg_roe, "{:.2f}", "%"))
    with col2:
        st.metric("Median P/E", fmt(med_pe))
    with col3:
        st.metric("Median D/E", fmt(med_de, "{:.2f}", "x"))
    with col4:
        st.metric("Total Companies", total_cos)
    with col5:
        st.metric("Median Sales CAGR 5Y", fmt(med_cagr, "{:.2f}", "%"))
    with col6:
        st.metric("Debt-Free Companies", debt_free_count)

    st.write("")
    
    # Sector breakdown donut and Top-5 table
    cc1, cc2 = st.columns([1, 1])
    
    with cc1:
        st.subheader("Sector Breakdown")
        df_sec_counts = df_kpis.groupby("broad_sector").size().reset_index(name="count")
        fig = px.pie(
            df_sec_counts, 
            values="count", 
            names="broad_sector", 
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig.update_layout(showlegend=True, margin=dict(l=0, r=0, t=30, b=0), height=350)
        st.plotly_chart(fig, use_container_width=True)
        
    with cc2:
        st.subheader("Top-5 Composite Quality Score Leaders")
        df_top5 = df_kpis.sort_values(by="composite_quality_score", ascending=False).head(5)
        df_top5_disp = df_top5[["company_id", "company_name", "broad_sector", "composite_quality_score"]].rename(columns={
            "company_id": "Ticker",
            "company_name": "Company Name",
            "broad_sector": "Sector",
            "composite_quality_score": "Quality Score"
        })
        # Format quality score
        df_top5_disp["Quality Score"] = df_top5_disp["Quality Score"].apply(lambda v: fmt(v, "{:.1f}"))
        st.dataframe(df_top5_disp, use_container_width=True, hide_index=True)
else:
    st.warning(f"No records found for the year {selected_year} in the database.")
