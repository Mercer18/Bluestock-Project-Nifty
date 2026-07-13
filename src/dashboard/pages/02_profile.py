"""
Company Profile Deep-Dive Screen.
Features autocomplete search, KPI cards, Plotly financial charts, and dynamic pros/cons lists.
"""

import os
import sys
import sqlite3
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Add src/ to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.dashboard.utils.db import get_companies, get_ratios, get_pl, get_bs, get_cf

st.set_page_config(page_title="Nifty 100 Analytics - Company Profile", layout="wide")

# Helper for safe formatting
def sf(val, fmt="{:.2f}", suffix=""):
    if val is None or pd.isna(val):
        return "N/A"
    try:
        return fmt.format(float(val)) + suffix
    except Exception:
        return "N/A"

st.markdown('<h1 style="color:#1F4E79; font-weight:bold;">📊 Company Deep-Dive Profile</h1>', unsafe_allow_html=True)

# Load all companies for search list
df_all_cos = get_companies()
options_list = sorted([f"{row['company_id']} - {row['company_name']}" for _, row in df_all_cos.iterrows()])

search_choice = st.selectbox("Search / Select Company Ticker or Name", options_list)

if search_choice:
    ticker = search_choice.split(" - ")[0]
    
    # Load company specific records
    df_co_pl = get_pl(ticker).sort_values(by="year")
    df_co_bs = get_bs(ticker).sort_values(by="year")
    df_co_cf = get_cf(ticker).sort_values(by="year")
    df_co_r = get_ratios(ticker).sort_values(by="year")
    
    comp_meta = df_all_cos[df_all_cos["company_id"] == ticker].iloc[0]
    
    # Check if there is data
    if len(df_co_pl) == 0:
        st.error(f"Ticker not found — please try another.")
    else:
        # Align common years
        pl_years = set(df_co_pl["year"])
        bs_years = set(df_co_bs["year"])
        cf_years = set(df_co_cf["year"])
        r_years = set(df_co_r["year"])
        
        common_years = sorted(list(pl_years.intersection(bs_years).intersection(cf_years).intersection(r_years)))
        
        df_co_pl = df_co_pl[df_co_pl["year"].isin(common_years)]
        df_co_bs = df_co_bs[df_co_bs["year"].isin(common_years)]
        df_co_cf = df_co_cf[df_co_cf["year"].isin(common_years)]
        df_co_r = df_co_r[df_co_r["year"].isin(common_years)]
        
        latest_ratio = df_co_r.iloc[-1] if len(df_co_r) > 0 else {}
        latest_pl = df_co_pl.iloc[-1] if len(df_co_pl) > 0 else {}
        latest_bs = df_co_bs.iloc[-1] if len(df_co_bs) > 0 else {}
        
        # Calculate latest ROCE
        latest_roce = None
        if len(latest_bs) > 0 and len(latest_pl) > 0:
            ebit = (latest_pl["profit_before_tax"] or 0) + (latest_pl["interest"] or 0)
            ce = (latest_bs["equity_capital"] or 0) + (latest_bs["reserves"] or 0) + (latest_bs["borrowings"] or 0)
            if ce > 0:
                latest_roce = (ebit / ce) * 100
                
        # Main company details card
        st.markdown(
            f"""
            <div style="background-color:#F8F9FA; padding: 20px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 20px;">
                <h3 style="margin-top:0; color:#1F4E79;"><b>{comp_meta['company_name']} ({ticker})</b></h3>
                <p><b>Sector</b>: {comp_meta['broad_sector']} | <b>Sub-sector</b>: {comp_meta['sub_sector']} | <b>Market Cap</b>: {comp_meta['market_cap_category']}</p>
                <p style="color:#4A5568;">{comp_meta['about_company'] or 'No description available for this constituent.'}</p>
                <p style="margin-bottom:0;"><a href="{comp_meta['website']}" target="_blank">Visit Website</a> | <a href="{comp_meta['nse_profile']}" target="_blank">NSE Profile</a> | <a href="{comp_meta['bse_profile']}" target="_blank">BSE Profile</a></p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # 6 KPI Tiles
        kcol1, kcol2, kcol3, kcol4, kcol5, kcol6 = st.columns(6)
        with kcol1:
            st.metric("Latest ROE %", sf(latest_ratio.get("return_on_equity_pct"), "{:.2f}", "%"))
        with kcol2:
            st.metric("Latest ROCE %", sf(latest_roce, "{:.2f}", "%"))
        with kcol3:
            st.metric("Net Profit Margin", sf(latest_ratio.get("net_profit_margin_pct"), "{:.2f}", "%"))
        with kcol4:
            st.metric("Debt-to-Equity", sf(latest_ratio.get("debt_to_equity"), "{:.2f}", "x"))
        with kcol5:
            st.metric("Sales CAGR 5Yr", sf(latest_ratio.get("revenue_cagr_5yr"), "{:.2f}", "%"))
        with kcol6:
            st.metric("Latest FCF Cr", sf(latest_ratio.get("free_cash_flow_cr"), "{:,.1f}"))
            
        st.write("")
        
        # 10-Year Revenue and Net Profit side-by-side
        cc1, cc2 = st.columns([1, 1])
        
        with cc1:
            st.write("#### 10-Year Revenue & Net Profit Trend")
            fig1 = go.Figure()
            fig1.add_trace(go.Bar(
                x=[y.split("-")[0] for y in common_years],
                y=df_co_pl["sales"] / 10.0,
                name="Revenue (INR Cr)",
                marker_color="#1F4E79"
            ))
            fig1.add_trace(go.Bar(
                x=[y.split("-")[0] for y in common_years],
                y=df_co_pl["net_profit"] / 10.0,
                name="Net Profit (INR Cr)",
                marker_color="#4F81BD"
            ))
            fig1.update_layout(barmode="group", height=320, margin=dict(l=0, r=0, t=20, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig1, use_container_width=True)
            
        with cc2:
            st.write("#### ROE & ROCE Dual-Axis Trend")
            # Calculate ROCE history
            roce_history = []
            for _, row_bs in df_co_bs.iterrows():
                y = row_bs["year"]
                row_pl = df_co_pl[df_co_pl["year"] == y]
                if len(row_pl) > 0:
                    ebit = (row_pl.iloc[0]["profit_before_tax"] or 0) + (row_pl.iloc[0]["interest"] or 0)
                    ce = (row_bs["equity_capital"] or 0) + (row_bs["reserves"] or 0) + (row_bs["borrowings"] or 0)
                    roce_history.append((ebit / ce * 100) if ce > 0 else np.nan)
                else:
                    roce_history.append(np.nan)
                    
            fig2 = make_subplots(specs=[[{"secondary_y": True}]])
            x_yrs = [y.split("-")[0] for y in common_years]
            
            fig2.add_trace(go.Scatter(
                x=x_yrs,
                y=df_co_r["return_on_equity_pct"],
                name="ROE %",
                line=dict(color="#E26B0A", width=2.5),
                mode="lines+markers"
            ), secondary_y=False)
            
            fig2.add_trace(go.Scatter(
                x=x_yrs,
                y=roce_history,
                name="ROCE %",
                line=dict(color="#5B9BD5", width=2.5),
                mode="lines+markers"
            ), secondary_y=True)
            
            fig2.update_layout(height=320, margin=dict(l=0, r=0, t=20, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig2.update_yaxes(title_text="ROE (%)", secondary_y=False)
            fig2.update_yaxes(title_text="ROCE (%)", secondary_y=True)
            st.plotly_chart(fig2, use_container_width=True)
            
        # Pros & Cons
        st.write("")
        st.subheader("Qualitative Pros & Cons (NLP Engine)")
        
        # Load generated pros/cons from output csv
        pc_path = os.path.join(PROJECT_ROOT, "output", "pros_cons_generated.csv")
        if os.path.exists(pc_path):
            df_pc = pd.read_csv(pc_path)
            co_pc = df_pc[df_pc["company_id"] == ticker]
            pros = co_pc[co_pc["type"] == "pro"]["text"].tolist()
            cons = co_pc[co_pc["type"] == "con"]["text"].tolist()
        else:
            pros = []
            cons = []
            
        if not pros:
            pros = ["Stable operating history and continuous listing on the Nifty 100 index."]
        if not cons:
            cons = ["Subject to macro-economic cycles, raw material pricing volatility, and regulatory updates."]
            
        pcol, ccol = st.columns(2)
        
        with pcol:
            st.markdown("<h5 style='color:#27AE60;'><b>Key Strengths (Pros)</b></h5>", unsafe_allow_html=True)
            for p in pros:
                st.markdown(f"✅ {p}")
                
        with ccol:
            st.markdown("<h5 style='color:#C0392B;'><b>Key Concerns (Cons)</b></h5>", unsafe_allow_html=True)
            for c in cons:
                st.markdown(f"❌ {c}")
