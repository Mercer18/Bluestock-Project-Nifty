"""
FastAPI REST API Server for Nifty 100 Financial Intelligence Platform.
Exposes 16 REST endpoints on port 8000 with JSON compliance for NaN values.
"""

import os
import time
import sqlite3
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import numpy as np

# Resolve paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "nifty100.db")
TEARSHEETS_DIR = os.path.join(PROJECT_ROOT, "reports", "tearsheets")

# Uptime tracking
START_TIME = time.time()

app = FastAPI(
    title="Nifty 100 API Server",
    description="API Server for Nifty 100 Financial Intelligence Platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    print(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.4f}s")
    return response

# Database connection helper
def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Helper to safely serialize DataFrames to dict (replaces NaN with None)
def to_dict_safe(df: pd.DataFrame) -> list:
    return df.fillna(np.nan).replace({np.nan: None}).to_dict(orient="records")

# Helper to safely serialize single sqlite3.Row or dict (replaces NaN with None)
def dict_safe(row):
    if not row:
        return {}
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, float) and (np.isnan(v) or pd.isna(v)):
            d[k] = None
    return d

# 1. GET /api/v1/health
@app.get("/api/v1/health")
def get_health():
    conn = get_db_conn()
    tables = [
        "companies", "profitandloss", "balancesheet", "cashflow", "analysis",
        "documents", "prosandcons", "sectors", "stock_prices", "financial_ratios"
    ]
    row_counts = {}
    for table in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            row_counts[table] = count
        except Exception:
            row_counts[table] = -1
    conn.close()
    
    return {
        "status": "ok",
        "db_row_counts": row_counts,
        "uptime_seconds": int(time.time() - START_TIME),
        "version": "1.0.0"
    }

# 2. GET /api/v1/companies
@app.get("/api/v1/companies")
def get_companies(
    sector: str = None,
    market_cap_category: str = None,
    search: str = None
):
    conn = get_db_conn()
    query = (
        "SELECT c.id, c.company_name, s.broad_sector, s.sub_sector, "
        "c.roe_percentage as roe_pct, c.roce_percentage as roce_pct "
        "FROM companies c "
        "LEFT JOIN sectors s ON c.id = s.company_id WHERE 1=1"
    )
    params = []
    
    if sector:
        query += " AND s.broad_sector = ?"
        params.append(sector)
    if market_cap_category:
        query += " AND s.market_cap_category = ?"
        params.append(market_cap_category)
    if search:
        query += " AND (c.id LIKE ? OR c.company_name LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
        
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return to_dict_safe(df)

# 3. GET /api/v1/companies/{ticker}
@app.get("/api/v1/companies/{ticker}")
def get_company_profile(ticker: str):
    conn = get_db_conn()
    comp = conn.execute("SELECT * FROM companies WHERE id = ?", (ticker.upper(),)).fetchone()
    if not comp:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")
        
    sector = conn.execute("SELECT * FROM sectors WHERE company_id = ?", (ticker.upper(),)).fetchone()
    ratios_latest = conn.execute("SELECT * FROM financial_ratios WHERE company_id = ? AND year = '2024-03'", (ticker.upper(),)).fetchone()
    conn.close()
    
    profile = dict_safe(comp)
    profile["sector"] = dict_safe(sector)
    profile["latest_ratios"] = dict_safe(ratios_latest)
    return profile

# 4. GET /api/v1/companies/{ticker}/pl
@app.get("/api/v1/companies/{ticker}/pl")
def get_pl_history(ticker: str):
    conn = get_db_conn()
    df = pd.read_sql_query("SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year", conn, params=(ticker.upper(),))
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No P&L history found for {ticker}")
    return to_dict_safe(df)

# 5. GET /api/v1/companies/{ticker}/bs
@app.get("/api/v1/companies/{ticker}/bs")
def get_bs_history(ticker: str):
    conn = get_db_conn()
    df = pd.read_sql_query("SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year", conn, params=(ticker.upper(),))
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No Balance Sheet history found for {ticker}")
    return to_dict_safe(df)

# 6. GET /api/v1/companies/{ticker}/cashflow
@app.get("/api/v1/companies/{ticker}/cashflow")
def get_cf_history(ticker: str):
    conn = get_db_conn()
    df = pd.read_sql_query("SELECT * FROM cashflow WHERE company_id = ? ORDER BY year", conn, params=(ticker.upper(),))
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No Cash Flow history found for {ticker}")
    return to_dict_safe(df)

# 7. GET /api/v1/companies/{ticker}/ratios
@app.get("/api/v1/companies/{ticker}/ratios")
def get_ratios_history(ticker: str, year: str = None):
    conn = get_db_conn()
    query = "SELECT * FROM financial_ratios WHERE company_id = ?"
    params = [ticker.upper()]
    if year:
        query += " AND year = ?"
        params.append(year)
    query += " ORDER BY year"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No ratio records found for {ticker}")
    return to_dict_safe(df)

# 8. GET /api/v1/companies/{ticker}/tearsheet
@app.get("/api/v1/companies/{ticker}/tearsheet")
def download_tearsheet(ticker: str):
    pdf_path = os.path.join(TEARSHEETS_DIR, f"{ticker.upper()}_tearsheet.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail=f"Tearsheet PDF for {ticker} not found")
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{ticker.upper()}_tearsheet.pdf")

# 9. GET /api/v1/screener
@app.get("/api/v1/screener")
def get_screener_results(
    min_roe: float = None,
    max_de: float = None,
    min_fcf: float = None,
    sector: str = None,
    min_rev_cagr_5yr: float = None,
    min_pat_cagr_5yr: float = None,
    max_pe: float = None
):
    conn = get_db_conn()
    query = (
        "SELECT r.company_id, c.company_name, s.broad_sector as sector, "
        "r.return_on_equity_pct as roe, r.debt_to_equity as de, "
        "r.free_cash_flow_cr as fcf, r.revenue_cagr_5yr as rev_cagr, "
        "r.pat_cagr_5yr as pat_cagr, mc.pe_ratio as pe, r.composite_quality_score as score "
        "FROM financial_ratios r "
        "JOIN companies c ON r.company_id = c.id "
        "LEFT JOIN sectors s ON r.company_id = s.company_id "
        "LEFT JOIN market_cap mc ON r.company_id = mc.company_id AND r.year = mc.year "
        "WHERE r.year = '2024-03'"
    )
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Filter
    if min_roe is not None:
        df = df[df["roe"] >= min_roe]
    if max_de is not None:
        # Ignore financials sector for D/E check
        df = df[(df["de"] <= max_de) | (df["sector"] == "Financials")]
    if min_fcf is not None:
        df = df[df["fcf"] >= min_fcf]
    if sector:
        df = df[df["sector"] == sector]
    if min_rev_cagr_5yr is not None:
        df = df[df["rev_cagr"] >= min_rev_cagr_5yr]
    if min_pat_cagr_5yr is not None:
        df = df[df["pat_cagr"] >= min_pat_cagr_5yr]
    if max_pe is not None:
        df = df[df["pe"] <= max_pe]
        
    df = df.sort_values(by="score", ascending=False)
    return to_dict_safe(df)

# 10. GET /api/v1/sectors
@app.get("/api/v1/sectors")
def get_sectors_summary():
    conn = get_db_conn()
    query = (
        "SELECT s.broad_sector as sector, r.return_on_equity_pct as roe, "
        "mc.pe_ratio as pe, r.debt_to_equity as de "
        "FROM sectors s "
        "JOIN financial_ratios r ON s.company_id = r.company_id "
        "JOIN market_cap mc ON s.company_id = mc.company_id AND r.year = mc.year "
        "WHERE r.year = '2024-03'"
    )
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    summary = []
    for sector_name, sub in df.groupby("sector"):
        summary.append({
            "sector": sector_name,
            "company_count": len(sub),
            "median_roe": float(sub["roe"].median()) if len(sub["roe"].dropna()) > 0 else 0.0,
            "median_pe": float(sub["pe"].median()) if len(sub["pe"].dropna()) > 0 else 0.0,
            "median_de": float(sub["de"].median()) if len(sub["de"].dropna()) > 0 else 0.0,
        })
    return summary

# 11. GET /api/v1/sectors/{sector}/companies
@app.get("/api/v1/sectors/{sector}/companies")
def get_sector_companies(sector: str):
    conn = get_db_conn()
    query = (
        "SELECT r.company_id, c.company_name, r.return_on_equity_pct as roe, "
        "r.debt_to_equity as de, r.free_cash_flow_cr as fcf, r.composite_quality_score as score "
        "FROM financial_ratios r "
        "JOIN companies c ON r.company_id = c.id "
        "JOIN sectors s ON r.company_id = s.company_id "
        "WHERE s.broad_sector = ? AND r.year = '2024-03'"
    )
    df = pd.read_sql_query(query, conn, params=(sector,))
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail=f"Sector {sector} not found or has no companies")
    return to_dict_safe(df)

# 12. GET /api/v1/peers/{group_name}
@app.get("/api/v1/peers/{group_name}")
def get_peers_ranks(group_name: str):
    conn = get_db_conn()
    query = (
        "SELECT p.company_id, p.is_benchmark, r.* "
        "FROM peer_groups p "
        "JOIN financial_ratios r ON p.company_id = r.company_id "
        "WHERE p.peer_group_name = ? AND r.year = '2024-03'"
    )
    df = pd.read_sql_query(query, conn, params=(group_name,))
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail=f"Peer group {group_name} not found")
    return to_dict_safe(df)

# 13. GET /api/v1/companies/{ticker}/peers/compare
@app.get("/api/v1/companies/{ticker}/peers/compare")
def get_company_peer_comparison(ticker: str):
    conn = get_db_conn()
    
    # Get company's peer group
    pg_row = conn.execute("SELECT peer_group_name FROM peer_groups WHERE company_id = ?", (ticker.upper(),)).fetchone()
    if not pg_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No peer group mapping found for {ticker}")
    peer_group = pg_row[0]
    
    # Get all company scores in peer group
    query = (
        "SELECT pg.company_id, pg.is_benchmark, "
        "r.return_on_equity_pct as roe, r.debt_to_equity as de, "
        "r.interest_coverage as icr, r.free_cash_flow_cr as fcf, "
        "r.revenue_cagr_5yr as rev_cagr, r.composite_quality_score as score "
        "FROM peer_groups pg "
        "JOIN financial_ratios r ON pg.company_id = r.company_id "
        "WHERE pg.peer_group_name = ? AND r.year = '2024-03'"
    )
    df = pd.read_sql_query(query, conn, params=(peer_group,))
    conn.close()
    
    # Extract company, benchmark, and group average
    company_data = df[df["company_id"] == ticker.upper()]
    benchmark_data = df[df["is_benchmark"] == 1]
    
    c_dict = dict_safe(company_data.iloc[0]) if len(company_data) > 0 else {}
    b_dict = dict_safe(benchmark_data.iloc[0]) if len(benchmark_data) > 0 else {}
    
    # Calculate group average
    group_avg = {
        "roe": float(df["roe"].mean()) if len(df["roe"].dropna()) > 0 else 0.0,
        "de": float(df["de"].mean()) if len(df["de"].dropna()) > 0 else 0.0,
        "icr": float(df["icr"].mean()) if len(df["icr"].dropna()) > 0 else 0.0,
        "fcf": float(df["fcf"].mean()) if len(df["fcf"].dropna()) > 0 else 0.0,
        "rev_cagr": float(df["rev_cagr"].mean()) if len(df["rev_cagr"].dropna()) > 0 else 0.0,
        "score": float(df["score"].mean()) if len(df["score"].dropna()) > 0 else 0.0
    }
    
    # Replace NaN in group_avg
    for k, v in group_avg.items():
        if np.isnan(v):
            group_avg[k] = 0.0
            
    return {
        "peer_group_name": peer_group,
        "company": c_dict,
        "benchmark": b_dict,
        "peer_group_average": group_avg
    }

# 14. GET /api/v1/market-cap/{ticker}
@app.get("/api/v1/market-cap/{ticker}")
def get_historical_valuation_multiples(ticker: str):
    conn = get_db_conn()
    df = pd.read_sql_query(
        "SELECT year, market_cap_crore, enterprise_value_crore, "
        "pe_ratio as pe, pb_ratio as pb, ev_ebitda, dividend_yield_pct "
        "FROM market_cap WHERE company_id = ? ORDER BY year",
        conn, params=(ticker.upper(),)
    )
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No valuation history found for {ticker}")
    return to_dict_safe(df)

# 15. GET /api/v1/portfolio/stats
@app.get("/api/v1/portfolio/stats")
def get_portfolio_stats():
    conn = get_db_conn()
    df = pd.read_sql_query("SELECT * FROM financial_ratios WHERE year = '2024-03'", conn)
    conn.close()
    
    kpis = [
        "return_on_equity_pct", "debt_to_equity", "interest_coverage", 
        "free_cash_flow_cr", "revenue_cagr_5yr", "pat_cagr_5yr", 
        "eps_cagr_5yr", "operating_profit_margin_pct", "net_profit_margin_pct", 
        "composite_quality_score"
    ]
    
    stats = {}
    for col in kpis:
        col_data = df[col].dropna()
        if len(col_data) > 0:
            p10 = np.percentile(col_data, 10)
            p25 = np.percentile(col_data, 25)
            p50 = np.percentile(col_data, 50)
            p75 = np.percentile(col_data, 75)
            p90 = np.percentile(col_data, 90)
            mean_v = col_data.mean()
            std_v = col_data.std()
            
            stats[col] = {
                "P10": None if np.isnan(p10) else float(p10),
                "P25": None if np.isnan(p25) else float(p25),
                "P50": None if np.isnan(p50) else float(p50),
                "P75": None if np.isnan(p75) else float(p75),
                "P90": None if np.isnan(p90) else float(p90),
                "Mean": None if np.isnan(mean_v) else float(mean_v),
                "Std": None if np.isnan(std_v) else float(std_v)
            }
    return stats

# 16. GET /api/v1/companies/{ticker}/documents
@app.get("/api/v1/companies/{ticker}/documents")
def get_company_documents(ticker: str):
    conn = get_db_conn()
    df = pd.read_sql_query("SELECT * FROM documents WHERE company_id = ?", conn, params=(ticker.upper(),))
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No documents found for {ticker}")
        
    records = []
    for _, row in df.iterrows():
        url = row["annual_report"]
        records.append({
            "report_type": "Annual Report",
            "year": int(row["year"]) if not pd.isna(row["year"]) else None,
            "document_url": url if not pd.isna(url) else None,
            "is_url_valid": True if url and isinstance(url, str) and url.startswith("http") else False
        })
    return records
