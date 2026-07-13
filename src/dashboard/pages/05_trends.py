"""
Trend Analysis Screen.
Implements multi-metric overlay charts showing 10-year trends and YoY % change annotations.
"""

import os
import sys
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Add src/ to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.dashboard.utils.db import get_companies, get_ratios, get_pl, get_bs, get_cf

st.set_page_config(page_title="Nifty 100 Analytics - Trends", layout="wide")

st.markdown('<h1 style="color:#1F4E79; font-weight:bold;">📉 10-Year Metric Trend Overlay</h1>', unsafe_allow_html=True)

df_all_cos = get_companies()
options_list = sorted([f"{row['company_id']} - {row['company_name']}" for _, row in df_all_cos.iterrows()])

search_choice = st.selectbox("Select Company Ticker or Name", options_list, key="trend_comp")

if search_choice:
    ticker = search_choice.split(" - ")[0]
    
    # Load all historical data
    df_pl = get_pl(ticker).sort_values(by="year")
    df_bs = get_bs(ticker).sort_values(by="year")
    df_cf = get_cf(ticker).sort_values(by="year")
    df_r = get_ratios(ticker).sort_values(by="year")
    
    # Align common years
    pl_years = set(df_pl["year"])
    bs_years = set(df_bs["year"])
    cf_years = set(df_cf["year"])
    r_years = set(df_r["year"])
    
    common_years = sorted(list(pl_years.intersection(bs_years).intersection(cf_years).intersection(r_years)))
    
    df_pl = df_pl[df_pl["year"].isin(common_years)]
    df_bs = df_bs[df_bs["year"].isin(common_years)]
    df_cf = df_cf[df_cf["year"].isin(common_years)]
    df_r = df_r[df_r["year"].isin(common_years)]
    
    years_x = [y.split("-")[0] for y in common_years]
    
    # Dynamic metric dictionaries
    metric_options = {
        "Revenue (INR Cr)": df_pl["sales"] / 10.0,
        "Net Profit (INR Cr)": df_pl["net_profit"] / 10.0,
        "Operating Profit (INR Cr)": df_pl["operating_profit"] / 10.0,
        "ROE %": df_r["return_on_equity_pct"],
        "OPM %": df_r["operating_profit_margin_pct"],
        "D/E Ratio": df_r["debt_to_equity"],
        "Interest Coverage Ratio": df_r["interest_coverage"],
        "Free Cash Flow (Cr)": df_r["free_cash_flow_cr"]
    }
    
    selected_metrics = st.multiselect(
        "Select Metrics to Overlay (Max 3)",
        options=list(metric_options.keys()),
        default=["Revenue (INR Cr)", "Net Profit (INR Cr)"]
    )
    
    if len(selected_metrics) > 3:
        st.warning("Please select at most 3 metrics to display.")
        selected_metrics = selected_metrics[:3]
        
    if selected_metrics:
        fig = go.Figure()
        
        # Color palettes
        colors_list = ["#1F4E79", "#E26B0A", "#27AE60"]
        
        for idx, m_name in enumerate(selected_metrics):
            vals = metric_options[m_name].tolist()
            # Handle list length mismatches
            if len(vals) < len(years_x):
                vals += [np.nan] * (len(years_x) - len(vals))
            else:
                vals = vals[:len(years_x)]
                
            # Compute YoY % change
            yoy_text = []
            for i in range(len(vals)):
                if i == 0 or pd.isna(vals[i-1]) or pd.isna(vals[i]) or vals[i-1] == 0:
                    yoy_text.append("")
                else:
                    change = ((vals[i] - vals[i-1]) / abs(vals[i-1])) * 100
                    yoy_text.append(f"{change:+.1f}%")
            
            fig.add_trace(go.Scatter(
                x=years_x,
                y=vals,
                name=m_name,
                line=dict(color=colors_list[idx % len(colors_list)], width=3),
                mode="lines+markers+text",
                text=yoy_text,
                textposition="top center",
                textfont=dict(size=8, color="#7F8C8D"),
                hoverinfo="x+y+name"
            ))
            
        fig.update_layout(
            height=450,
            margin=dict(l=40, r=40, t=30, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
            xaxis=dict(title="Fiscal Year"),
            yaxis=dict(title="Value")
        )
        st.plotly_chart(fig, use_container_width=True)
        st.info("YoY % change labels are plotted above each marker point.")
    else:
        st.info("Select one or more metrics from the dropdown to visualize the historical trend.")
