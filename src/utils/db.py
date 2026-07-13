"""
Cached Database Loader for Nifty 100 Dashboard.
Utilizes @st.cache_data to optimize SQLite query performance.
"""

import os
import sqlite3
import pandas as pd
import streamlit as st

# Resolve paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "nifty100.db")

def get_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)

@st.cache_data(ttl=600)
def get_companies():
    """Fetches all companies with metadata and sector classifications."""
    conn = get_connection()
    query = (
        "SELECT c.id as company_id, c.company_name, c.about_company, c.website, "
        "c.nse_profile, c.bse_profile, c.roce_percentage, c.roe_percentage, "
        "s.broad_sector, s.sub_sector, s.market_cap_category "
        "FROM companies c "
        "LEFT JOIN sectors s ON c.id = s.company_id"
    )
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_ratios(ticker, year=None):
    """Fetches financial ratios/KPIs for a specific ticker (and optional year)."""
    conn = get_connection()
    query = "SELECT * FROM financial_ratios WHERE company_id = ?"
    params = [ticker.upper()]
    if year:
        query += " AND year = ?"
        params.append(year)
    query += " ORDER BY year"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_pl(ticker):
    """Fetches Profit and Loss history for a company."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year", conn, params=(ticker.upper(),))
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_bs(ticker):
    """Fetches Balance Sheet history for a company."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year", conn, params=(ticker.upper(),))
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_cf(ticker):
    """Fetches Cash Flow history for a company."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM cashflow WHERE company_id = ? ORDER BY year", conn, params=(ticker.upper(),))
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_sectors():
    """Fetches sectors and sub-sectors weight summary."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM sectors", conn)
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_peers(group_name):
    """Fetches all peer groups matching a group name."""
    conn = get_connection()
    query = (
        "SELECT pg.company_id, pg.is_benchmark, c.company_name, "
        "r.return_on_equity_pct, r.debt_to_equity, r.interest_coverage, "
        "r.free_cash_flow_cr, r.revenue_cagr_5yr, r.composite_quality_score "
        "FROM peer_groups pg "
        "JOIN financial_ratios r ON pg.company_id = r.company_id "
        "JOIN companies c ON pg.company_id = c.id "
        "WHERE pg.peer_group_name = ? AND r.year = '2024-03'"
    )
    df = pd.read_sql_query(query, conn, params=(group_name,))
    conn.close()
    return df

@st.cache_data(ttl=600)
def get_valuation(ticker=None):
    """Fetches valuation multiples and market cap parameters."""
    conn = get_connection()
    if ticker:
        df = pd.read_sql_query("SELECT * FROM market_cap WHERE company_id = ? ORDER BY year", conn, params=(ticker.upper(),))
    else:
        df = pd.read_sql_query("SELECT * FROM market_cap ORDER BY company_id, year", conn)
    conn.close()
    return df
