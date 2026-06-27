-- SQLite Schema Definition for Nifty 100 Financial Intelligence Platform
-- Enforces referential integrity via FOREIGN KEY constraints.

PRAGMA foreign_keys = ON;

-- 1. Master Company Reference
CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR PRIMARY KEY,
    company_logo TEXT,
    company_name VARCHAR NOT NULL,
    chart_link TEXT,
    about_company TEXT,
    website TEXT,
    nse_profile TEXT,
    bse_profile TEXT,
    face_value NUMERIC,  -- Coerced to 1.0 in ETL but made nullable in schema for flexibility
    book_value NUMERIC,
    roce_percentage NUMERIC,
    roe_percentage NUMERIC
);

-- 2. Annual Profit & Loss Statements
CREATE TABLE IF NOT EXISTS profitandloss (
    company_id VARCHAR,
    year VARCHAR,
    sales NUMERIC,
    expenses NUMERIC,
    operating_profit NUMERIC,
    opm_percentage NUMERIC,
    other_income NUMERIC,
    interest NUMERIC,
    depreciation NUMERIC,
    profit_before_tax NUMERIC,
    tax_percentage NUMERIC,
    net_profit NUMERIC,
    eps NUMERIC,
    dividend_payout NUMERIC,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 3. Annual Balance Sheets
CREATE TABLE IF NOT EXISTS balancesheet (
    company_id VARCHAR,
    year VARCHAR,
    equity_capital NUMERIC,
    reserves NUMERIC,
    borrowings NUMERIC,
    other_liabilities NUMERIC,
    total_liabilities NUMERIC,
    fixed_assets NUMERIC,
    cwip NUMERIC,
    investments NUMERIC,
    other_asset NUMERIC,
    total_assets NUMERIC,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 4. Annual Cash Flow Statements
CREATE TABLE IF NOT EXISTS cashflow (
    company_id VARCHAR,
    year VARCHAR,
    operating_activity NUMERIC,
    investing_activity NUMERIC,
    financing_activity NUMERIC,
    net_cash_flow NUMERIC,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 5. Pre-Computed Growth Metrics (Partial Coverage)
CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR,
    compounded_sales_growth TEXT,
    compounded_profit_growth TEXT,
    stock_price_cagr TEXT,
    roe TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 6. Annual Report Repository
CREATE TABLE IF NOT EXISTS documents (
    company_id VARCHAR,
    year INTEGER,
    annual_report TEXT,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 7. Qualitative Investment Insights (Pros & Cons)
CREATE TABLE IF NOT EXISTS prosandcons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR,
    pros TEXT,
    cons TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 8. Company Sector Mapping (Supplementary)
CREATE TABLE IF NOT EXISTS sectors (
    company_id VARCHAR PRIMARY KEY,
    broad_sector VARCHAR NOT NULL,
    sub_sector VARCHAR NOT NULL,
    index_weight_pct NUMERIC,
    market_cap_category VARCHAR,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 9. Annual Valuation Multiples (Supplementary)
CREATE TABLE IF NOT EXISTS market_cap (
    company_id VARCHAR,
    year INTEGER,
    market_cap_crore NUMERIC,
    enterprise_value_crore NUMERIC,
    pe_ratio NUMERIC,
    pb_ratio NUMERIC,
    ev_ebitda NUMERIC,
    dividend_yield_pct NUMERIC,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 10. Monthly OHLCV Price History (Supplementary)
CREATE TABLE IF NOT EXISTS stock_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR,
    date VARCHAR,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    volume INTEGER,
    adjusted_close NUMERIC,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 11. Peer Comparison Groups (Supplementary)
CREATE TABLE IF NOT EXISTS peer_groups (
    company_id VARCHAR,
    peer_group_name VARCHAR,
    is_benchmark BOOLEAN,
    PRIMARY KEY (company_id, peer_group_name),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 12. Pre-Computed KPI Table (Supplementary)
CREATE TABLE IF NOT EXISTS financial_ratios (
    company_id VARCHAR,
    year VARCHAR,
    net_profit_margin_pct NUMERIC,
    operating_profit_margin_pct NUMERIC,
    return_on_equity_pct NUMERIC,
    debt_to_equity NUMERIC,
    interest_coverage NUMERIC,
    asset_turnover NUMERIC,
    free_cash_flow_cr NUMERIC,
    capex_cr NUMERIC,
    earnings_per_share NUMERIC,
    book_value_per_share NUMERIC,
    dividend_payout_ratio_pct NUMERIC,
    total_debt_cr NUMERIC,
    cash_from_operations_cr NUMERIC,
    
    -- Sprint 2 Added Columns
    return_on_assets_pct NUMERIC,
    net_debt_cr NUMERIC,
    icr_label VARCHAR,
    high_leverage_flag INTEGER,
    icr_warning_flag INTEGER,
    
    revenue_cagr_5yr NUMERIC,
    revenue_cagr_5yr_flag VARCHAR,
    pat_cagr_5yr NUMERIC,
    pat_cagr_5yr_flag VARCHAR,
    eps_cagr_5yr NUMERIC,
    eps_cagr_5yr_flag VARCHAR,
    
    composite_quality_score NUMERIC,
    
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);
