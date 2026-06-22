-- Nifty 100 Financial Intelligence Platform - Sprint 1 Exploratory Queries
-- Run these queries on nifty100.db to verify data integrity and extract initial insights.

-- 1. Row Counts Verification (AC-01 & AC-04 Verification)
SELECT 'companies' as table_name, COUNT(*) as row_count FROM companies UNION ALL
SELECT 'profitandloss', COUNT(*) FROM profitandloss UNION ALL
SELECT 'balancesheet', COUNT(*) FROM balancesheet UNION ALL
SELECT 'cashflow', COUNT(*) FROM cashflow UNION ALL
SELECT 'analysis', COUNT(*) FROM analysis UNION ALL
SELECT 'documents', COUNT(*) FROM documents UNION ALL
SELECT 'prosandcons', COUNT(*) FROM prosandcons UNION ALL
SELECT 'sectors', COUNT(*) FROM sectors UNION ALL
SELECT 'market_cap', COUNT(*) FROM market_cap UNION ALL
SELECT 'stock_prices', COUNT(*) FROM stock_prices UNION ALL
SELECT 'peer_groups', COUNT(*) FROM peer_groups UNION ALL
SELECT 'financial_ratios', COUNT(*) FROM financial_ratios;

-- 2. Top 10 ROE Companies (Latest Year per company)
SELECT r.company_id, c.company_name, r.return_on_equity_pct
FROM financial_ratios r
JOIN companies c ON r.company_id = c.id
JOIN (
    SELECT company_id, MAX(year) as max_year
    FROM financial_ratios
    GROUP BY company_id
) latest ON r.company_id = latest.company_id AND r.year = latest.max_year
ORDER BY r.return_on_equity_pct DESC
LIMIT 10;

-- 3. Debt-Free Companies (Latest Year per company, D/E = 0)
SELECT r.company_id, c.company_name, r.year, r.debt_to_equity
FROM financial_ratios r
JOIN companies c ON r.company_id = c.id
JOIN (
    SELECT company_id, MAX(year) as max_year
    FROM financial_ratios
    GROUP BY company_id
) latest ON r.company_id = latest.company_id AND r.year = latest.max_year
WHERE r.debt_to_equity = 0
ORDER BY c.company_name ASC;

-- 4. Consecutive FCF Positive (5+ Years)
SELECT company_id, COUNT(*) AS positive_fcf_yrs
FROM financial_ratios
WHERE free_cash_flow_cr > 0
GROUP BY company_id
HAVING positive_fcf_yrs >= 5
ORDER BY positive_fcf_yrs DESC;

-- 5. Sector Median ROE Comparison (Latest Year per company)
SELECT s.broad_sector, ROUND(AVG(r.return_on_equity_pct), 2) AS avg_roe
FROM financial_ratios r
JOIN sectors s ON r.company_id = s.company_id
JOIN (
    SELECT company_id, MAX(year) as max_year
    FROM financial_ratios
    GROUP BY company_id
) latest ON r.company_id = latest.company_id AND r.year = latest.max_year
GROUP BY s.broad_sector
ORDER BY avg_roe DESC;

-- 6. Capital Allocation Pattern Count (Latest Year per company CFO/CFI/CFF signs)
SELECT 
    (CASE WHEN operating_activity > 0 THEN '+' ELSE '-' END) || ' ' ||
    (CASE WHEN investing_activity > 0 THEN '+' ELSE '-' END) || ' ' ||
    (CASE WHEN financing_activity > 0 THEN '+' ELSE '-' END) AS cfo_cfi_cff_pattern,
    COUNT(*) AS company_count
FROM cashflow c
JOIN (
    SELECT company_id, MAX(year) as max_year
    FROM cashflow
    GROUP BY company_id
) latest ON c.company_id = latest.company_id AND c.year = latest.max_year
GROUP BY cfo_cfi_cff_pattern
ORDER BY company_count DESC;

-- 7. 5-Year Revenue CAGR > 15% (Comparing 2024-03 vs 2019-03)
SELECT p1.company_id, c.company_name, 
       ROUND((POWER(CAST(p1.sales AS REAL) / p2.sales, 0.2) - 1) * 100, 2) AS sales_cagr_5yr
FROM profitandloss p1
JOIN profitandloss p2 ON p1.company_id = p2.company_id AND p2.year = '2019-03'
JOIN companies c ON p1.company_id = c.id
WHERE p1.year = '2024-03' AND p2.sales > 0 AND sales_cagr_5yr > 15.0
ORDER BY sales_cagr_5yr DESC;

-- 8. Missing Annual Reports (Checking documentation gaps)
SELECT c.id as company_id, c.company_name
FROM companies c
LEFT JOIN documents d ON c.id = d.company_id AND d.annual_report IS NOT NULL
WHERE d.company_id IS NULL
ORDER BY c.company_name ASC;

-- 9. Peer Group Rankings by ROE (Latest Year per company)
SELECT p.peer_group_name, r.company_id, r.return_on_equity_pct,
       RANK() OVER (PARTITION BY p.peer_group_name ORDER BY r.return_on_equity_pct DESC) as peer_rank
FROM financial_ratios r
JOIN peer_groups p ON r.company_id = p.company_id
JOIN (
    SELECT company_id, MAX(year) as max_year
    FROM financial_ratios
    GROUP BY company_id
) latest ON r.company_id = latest.company_id AND r.year = latest.max_year
ORDER BY p.peer_group_name, peer_rank;

-- 10. Null / Missing Data Check on Master Company Table
SELECT 
    SUM(CASE WHEN website IS NULL THEN 1 ELSE 0 END) as null_websites,
    SUM(CASE WHEN roce_percentage IS NULL THEN 1 ELSE 0 END) as null_roce,
    SUM(CASE WHEN roe_percentage IS NULL THEN 1 ELSE 0 END) as null_roe,
    SUM(CASE WHEN book_value IS NULL THEN 1 ELSE 0 END) as null_book_value
FROM companies;
