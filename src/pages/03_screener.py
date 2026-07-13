"""
Financial Screener Screen.
Implements 10 metrics sliders, 6 preset filter buttons, and a CSV exporter.
"""

import os
import sys
import yaml
import streamlit as st
import pandas as pd

# Add src/ to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.dashboard.utils.db import get_companies, get_ratios, get_valuation

st.set_page_config(page_title="Nifty 100 Analytics - Screener", layout="wide")

# Helper for safe formatting
def sf(val, fmt="{:.2f}", suffix=""):
    if val is None or pd.isna(val):
        return "N/A"
    try:
        return fmt.format(float(val)) + suffix
    except Exception:
        return "N/A"

st.markdown('<h1 style="color:#1F4E79; font-weight:bold;">🔍 Interactive Financial Screener</h1>', unsafe_allow_html=True)

# Load configurations
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "screener_config.yaml")

presets = {}
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r") as f:
            presets = yaml.safe_load(f).get("presets", {})
    except Exception:
        pass

# Fallback presets if yaml is not loaded
if not presets:
    presets = {
        "Quality Compounder": {"roe_min": 15.0, "de_max": 1.0, "fcf_min": 100.0, "revenue_cagr_5yr_min": 10.0},
        "Value Pick": {"pe_max": 25.0, "pb_max": 3.0, "roe_min": 12.0},
        "Growth Accelerator": {"revenue_cagr_5yr_min": 15.0, "pat_cagr_5yr_min": 15.0, "roe_min": 12.0},
        "Dividend Yield": {"dividend_yield_min": 2.0, "fcf_min": 0.0},
        "Debt-Free": {"de_max": 0.01},
        "Turnaround": {"interest_coverage_min": 1.5, "revenue_cagr_5yr_min": -5.0}
    }

# 10 Sliders configuration
slider_configs = {
    "roe_min": ("ROE Min (%)", -50.0, 100.0, 0.0, 1.0),
    "de_max": ("D/E Max (x)", 0.0, 10.0, 5.0, 0.1),
    "fcf_min": ("FCF Min (Cr)", -1000.0, 5000.0, -100.0, 50.0),
    "revenue_cagr_min": ("Revenue CAGR 5Yr Min (%)", -50.0, 100.0, 0.0, 1.0),
    "pat_cagr_min": ("PAT CAGR 5Yr Min (%)", -50.0, 100.0, 0.0, 1.0),
    "opm_min": ("OPM Min (%)", -20.0, 100.0, 0.0, 1.0),
    "pe_max": ("P/E Max (x)", 0.0, 200.0, 150.0, 5.0),
    "pb_max": ("P/B Max (x)", 0.0, 50.0, 40.0, 1.0),
    "div_yield_min": ("Dividend Yield Min (%)", 0.0, 10.0, 0.0, 0.1),
    "icr_min": ("ICR Min (x)", -10.0, 100.0, 1.0, 0.5)
}

# Initialize session state for sliders
for k, cfg in slider_configs.items():
    state_key = f"scr_{k}"
    if state_key not in st.session_state:
        st.session_state[state_key] = cfg[3]

# Apply preset helper
def apply_preset(name):
    vals = presets.get(name, {})
    # Reset all to default first
    for k, cfg in slider_configs.items():
        st.session_state[f"scr_{k}"] = cfg[3]
    # Set preset values
    if "roe_min" in vals: st.session_state["scr_roe_min"] = float(vals["roe_min"])
    if "de_max" in vals: st.session_state["scr_de_max"] = float(vals["de_max"])
    if "fcf_min" in vals: st.session_state["scr_fcf_min"] = float(vals["fcf_min"])
    if "revenue_cagr_5yr_min" in vals: st.session_state["scr_revenue_cagr_min"] = float(vals["revenue_cagr_5yr_min"])
    if "pat_cagr_5yr_min" in vals: st.session_state["scr_pat_cagr_min"] = float(vals["pat_cagr_5yr_min"])
    if "opm_min" in vals: st.session_state["scr_opm_min"] = float(vals["opm_min"])
    if "pe_max" in vals: st.session_state["scr_pe_max"] = float(vals["pe_max"])
    if "pb_max" in vals: st.session_state["scr_pb_max"] = float(vals["pb_max"])
    if "dividend_yield_min" in vals: st.session_state["scr_div_yield_min"] = float(vals["dividend_yield_min"])
    if "interest_coverage_min" in vals: st.session_state["scr_icr_min"] = float(vals["interest_coverage_min"])

# Preset Buttons Row
st.write("### Preset Screener Templates")
cols = st.columns(6)
preset_names = list(presets.keys())
for i, name in enumerate(preset_names[:6]):
    with cols[i]:
        if st.button(name, use_container_width=True):
            apply_preset(name)
            st.rerun()

st.sidebar.subheader("Filter Customization")
# Sliders
filters = {}
for k, cfg in slider_configs.items():
    filters[k] = st.sidebar.slider(
        cfg[0],
        min_value=cfg[1],
        max_value=cfg[2],
        step=cfg[4],
        key=f"scr_{k}"
    )

# Load data and filter
df_comp = get_companies()
conn = get_connection()
df_ratios = pd.read_sql_query("SELECT * FROM financial_ratios WHERE year = '2024-03'", conn)
df_mc = pd.read_sql_query("SELECT * FROM market_cap WHERE year = '2024-03'", conn)
conn.close()

# Merge
df_all = df_comp.merge(df_ratios, left_on="company_id", right_on="company_id", how="inner")
df_all = df_all.merge(df_mc, left_on="company_id", right_on="company_id", how="inner")

# Apply filters
df_fil = df_all.copy()

df_fil = df_fil[df_fil["return_on_equity_pct"] >= filters["roe_min"]]
# Ignore financials for DE
df_fil = df_fil[(df_fil["debt_to_equity"] <= filters["de_max"]) | (df_fil["broad_sector"] == "Financials")]
df_fil = df_fil[df_fil["free_cash_flow_cr"] >= filters["fcf_min"]]
df_fil = df_fil[df_fil["revenue_cagr_5yr"] >= filters["revenue_cagr_min"]]
df_fil = df_fil[df_fil["pat_cagr_5yr"] >= filters["pat_cagr_min"]]
df_fil = df_fil[df_fil["operating_profit_margin_pct"] >= filters["opm_min"]]
df_fil = df_fil[df_fil["pe_ratio"] <= filters["pe_max"]]
df_fil = df_fil[df_fil["pb_ratio"] <= filters["pb_max"]]
df_fil = df_fil[df_fil["dividend_yield_pct"] >= filters["div_yield_min"]]
df_fil = df_fil[df_fil["interest_coverage"] >= filters["icr_min"]]

# Sorting by composite score
df_fil = df_fil.sort_values(by="composite_quality_score", ascending=False)

st.write("")
st.subheader("Screener Results (FY 2024)")
st.write(f"📊 **{len(df_fil)}** companies matched your filter criteria.")

if len(df_fil) > 0:
    df_disp = df_fil[[
        "company_id", "company_name", "broad_sector", "return_on_equity_pct",
        "debt_to_equity", "pe_ratio", "pb_ratio", "free_cash_flow_cr", "composite_quality_score"
    ]].rename(columns={
        "company_id": "Ticker",
        "company_name": "Company Name",
        "broad_sector": "Sector",
        "return_on_equity_pct": "ROE %",
        "debt_to_equity": "D/E",
        "pe_ratio": "P/E",
        "pb_ratio": "P/B",
        "free_cash_flow_cr": "FCF (Cr)",
        "composite_quality_score": "Quality Score"
    })
    
    # Formatting
    df_formatted = df_disp.copy()
    df_formatted["ROE %"] = df_formatted["ROE %"].apply(lambda v: sf(v, "{:.2f}", "%"))
    df_formatted["D/E"] = df_formatted["D/E"].apply(lambda v: sf(v, "{:.2f}", "x"))
    df_formatted["P/E"] = df_formatted["P/E"].apply(lambda v: sf(v, "{:.2f}", "x"))
    df_formatted["P/B"] = df_formatted["P/B"].apply(lambda v: sf(v, "{:.2f}", "x"))
    df_formatted["FCF (Cr)"] = df_formatted["FCF (Cr)"].apply(lambda v: sf(v, "{:,.1f}"))
    df_formatted["Quality Score"] = df_formatted["Quality Score"].apply(lambda v: sf(v, "{:.1f}"))
    
    st.dataframe(df_formatted, use_container_width=True, hide_index=True)
    
    # Download Button
    csv = df_disp.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download Screener Results (CSV)",
        csv,
        "screener_results.csv",
        "text/csv",
        key="download-screener-csv"
    )
else:
    st.info("No companies match the current filter thresholds. Move the sliders to expand your search.")
