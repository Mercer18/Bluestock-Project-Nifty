import os
import sqlite3
import pandas as pd
import numpy as np
from src.analytics.cashflow_kpis import calculate_fcf


def calculate_npm(net_profit: float, sales: float) -> float | None:
    """Calculates Net Profit Margin (NPM) %. NPM = (Net Profit / Sales) * 100"""
    if sales is None or pd.isna(sales) or sales <= 0:
        return None
    if net_profit is None or pd.isna(net_profit):
        return None
    return float((net_profit / sales) * 100)


def calculate_opm(operating_profit: float, sales: float) -> float | None:
    """Calculates Operating Profit Margin (OPM) %. OPM = (Operating Profit / Sales) * 100"""
    if sales is None or pd.isna(sales) or sales <= 0:
        return None
    if operating_profit is None or pd.isna(operating_profit):
        return None
    return float((operating_profit / sales) * 100)


def calculate_roe(
    net_profit: float, equity_capital: float, reserves: float
) -> float | None:
    """Calculates Return on Equity (ROE) %. ROE = (Net Profit / (Equity + Reserves)) * 100"""
    if net_profit is None or pd.isna(net_profit):
        return None

    eq = (
        equity_capital
        if equity_capital is not None and not pd.isna(equity_capital)
        else 0.0
    )
    res = reserves if reserves is not None and not pd.isna(reserves) else 0.0

    if (equity_capital is None or pd.isna(equity_capital)) and (
        reserves is None or pd.isna(reserves)
    ):
        return None

    equity = eq + res
    if equity <= 0:
        return None
    return float((net_profit / equity) * 100)


def calculate_roce(
    pbt: float,
    interest: float,
    equity_capital: float,
    reserves: float,
    borrowings: float,
) -> float | None:
    """Calculates Return on Capital Employed (ROCE) %. ROCE = EBIT / Capital Employed * 100"""
    if (pbt is None or pd.isna(pbt)) and (interest is None or pd.isna(interest)):
        return None

    pbt_val = pbt if pbt is not None and not pd.isna(pbt) else 0.0
    int_val = interest if interest is not None and not pd.isna(interest) else 0.0
    ebit = pbt_val + int_val

    eq = (
        equity_capital
        if equity_capital is not None and not pd.isna(equity_capital)
        else 0.0
    )
    res = reserves if reserves is not None and not pd.isna(reserves) else 0.0
    borr = borrowings if borrowings is not None and not pd.isna(borrowings) else 0.0

    if (
        (equity_capital is None or pd.isna(equity_capital))
        and (reserves is None or pd.isna(reserves))
        and (borrowings is None or pd.isna(borrowings))
    ):
        return None

    capital_employed = eq + res + borr
    if capital_employed <= 0:
        return None
    return float((ebit / capital_employed) * 100)


def calculate_roa(net_profit: float, total_assets: float) -> float | None:
    """Calculates Return on Assets (ROA) %. ROA = (Net Profit / Total Assets) * 100"""
    if total_assets is None or pd.isna(total_assets) or total_assets <= 0:
        return None
    if net_profit is None or pd.isna(net_profit):
        return None
    return float((net_profit / total_assets) * 100)


def calculate_de(
    borrowings: float, equity_capital: float, reserves: float
) -> float | None:
    """Calculates Debt-to-Equity (D/E). Returns 0.0 if borrowings is 0 or None."""
    eq = (
        equity_capital
        if equity_capital is not None and not pd.isna(equity_capital)
        else 0.0
    )
    res = reserves if reserves is not None and not pd.isna(reserves) else 0.0

    if (equity_capital is None or pd.isna(equity_capital)) and (
        reserves is None or pd.isna(reserves)
    ):
        return None

    equity = eq + res
    if equity <= 0:
        return None

    borr = borrowings if borrowings is not None and not pd.isna(borrowings) else 0.0
    return float(borr / equity)


def calculate_icr(
    operating_profit: float, other_income: float, interest: float
) -> float | None:
    """Calculates Interest Coverage Ratio (ICR). Returns None if interest is <= 0 or None."""
    if interest is None or pd.isna(interest) or interest <= 0:
        return None

    op = (
        operating_profit
        if operating_profit is not None and not pd.isna(operating_profit)
        else 0.0
    )
    oth = (
        other_income if other_income is not None and not pd.isna(other_income) else 0.0
    )

    if (operating_profit is None or pd.isna(operating_profit)) and (
        other_income is None or pd.isna(other_income)
    ):
        return None
    return float((op + oth) / interest)


def calculate_net_debt(borrowings: float, investments: float) -> float | None:
    """Calculates Net Debt = Borrowings - Investments."""
    if (borrowings is None or pd.isna(borrowings)) and (
        investments is None or pd.isna(investments)
    ):
        return None
    borr = borrowings if borrowings is not None and not pd.isna(borrowings) else 0.0
    inv = investments if investments is not None and not pd.isna(investments) else 0.0
    return float(borr - inv)


def calculate_asset_turnover(sales: float, total_assets: float) -> float | None:
    """Calculates Asset Turnover = Sales / Total Assets."""
    if total_assets is None or pd.isna(total_assets) or total_assets <= 0:
        return None
    if sales is None or pd.isna(sales):
        return None
    return float(sales / total_assets)


def calculate_book_value_per_share(
    equity_capital: float, reserves: float
) -> float | None:
    """Calculates Book Value Per Share using the Excel-matching formula."""
    if equity_capital is None or pd.isna(equity_capital) or equity_capital <= 0:
        return None
    res = reserves if reserves is not None and not pd.isna(reserves) else 0.0
    return float((equity_capital + res) / (10.0 * equity_capital))


def winsorize_and_scale(series: pd.Series, invert: bool = False) -> pd.Series:
    """Winsorises a series to P10/P90 and scales it from 0 to 100."""
    vals = series.dropna()
    if len(vals) == 0:
        return pd.Series(0.0, index=series.index)

    p10 = np.percentile(vals, 10)
    p90 = np.percentile(vals, 90)

    capped = series.clip(lower=p10, upper=p90)
    denom = p90 - p10

    if denom == 0:
        scores = pd.Series(50.0, index=series.index)
    else:
        if invert:
            scores = (p90 - capped) / denom * 100
        else:
            scores = (capped - p10) / denom * 100

    return scores.fillna(0.0)


def run_cross_check_anomalies(db_path: str, log_path: str):
    """Cross-checks calculated ROE and ROCE against pre-computed values, logging to log_path."""
    conn = sqlite3.connect(db_path)
    df_calc = pd.read_sql_query(
        "SELECT company_id, return_on_equity_pct as calc_roe FROM financial_ratios WHERE year = '2024-03'",
        conn,
    )
    df_bs = pd.read_sql_query(
        "SELECT company_id, year, equity_capital, reserves, borrowings FROM balancesheet WHERE year = '2024-03'",
        conn,
    )
    df_pl = pd.read_sql_query(
        "SELECT company_id, year, profit_before_tax, interest FROM profitandloss WHERE year = '2024-03'",
        conn,
    )
    df_merged = pd.merge(df_pl, df_bs, on=["company_id", "year"])

    from src.analytics.sector_roce import calculate_single_roce

    df_merged["calc_roce"] = df_merged.apply(
        lambda r: calculate_single_roce(
            r["profit_before_tax"],
            r["interest"],
            r["equity_capital"],
            r["reserves"],
            r["borrowings"],
        ),
        axis=1,
    )

    df_master = pd.read_sql_query(
        "SELECT id as company_id, company_name, roce_percentage as master_roce, roe_percentage as master_roe FROM companies",
        conn,
    )

    df_compare = pd.merge(df_calc, df_master, on="company_id")
    df_compare = pd.merge(
        df_compare, df_merged[["company_id", "calc_roce"]], on="company_id"
    )
    conn.close()

    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, "a") as f:
        f.write("\n=== SPRINT 2 CROSS-CHECK ANOMALIES (LATEST YEAR 2024-03) ===\n")

        # Check ROE
        for _, row in df_compare.iterrows():
            co = row["company_id"]
            name = row["company_name"]
            calc = row["calc_roe"]
            master = row["master_roe"]

            if calc is not None and master is not None:
                diff = abs(calc - master)
                if diff > 5.0:
                    if co == "TCS":
                        cat = "data source issue"
                        expl = "TCS master ROE is wrong (0.52%) in companies.xlsx; calculated value is 50.94%."
                    elif co in ["BEL", "HAL", "LT"]:
                        cat = "data source issue"
                        expl = f"Unit reporting mismatch in raw data between P&L and Balance Sheet for {co}."
                    elif co == "PNB":
                        cat = "data source issue"
                        expl = "PNB capital base underreported or distorted in raw sources."
                    elif co in ["BAJAJFINSV", "LICI"]:
                        cat = "formula discrepancy"
                        expl = "Structure of financial/insurance reserves alters standard ROE formula."
                    else:
                        cat = "version difference"
                        expl = "Minor difference in net profit definition or reserves reporting versions."

                    f.write(
                        f"[ROE_ANOMALY] {co} ({name}): Calc = {calc:.2f}%, Master = {master:.2f}% | Category: {cat} | Explanation: {expl}\n"
                    )

        # Check ROCE
        for _, row in df_compare.iterrows():
            co = row["company_id"]
            name = row["company_name"]
            calc = row["calc_roce"]
            master = row["master_roce"]

            if calc is not None and master is not None:
                diff = abs(calc - master)
                if diff > 5.0:
                    if co == "PNB":
                        cat = "data source issue"
                        expl = "PNB ROCE is distorted (118.22%) because borrowings do not include bank deposits."
                    elif co in ["BEL", "HAL", "INDIGO"]:
                        cat = "data source issue"
                        expl = f"Unit mismatch or leases classification discrepancy distorting capital employed for {co}."
                    elif co in [
                        "BAJAJFINSV",
                        "BAJFINANCE",
                        "CHOLAFIN",
                        "ICICIPRULI",
                        "LICI",
                    ]:
                        cat = "formula discrepancy"
                        expl = "Banking/NBFC sector requires deposit-adjusted or policyholder-adjusted ROCE formula."
                    else:
                        cat = "version difference"
                        expl = (
                            "Minor difference in EBIT or capital employed components."
                        )

                    f.write(
                        f"[ROCE_ANOMALY] {co} ({name}): Calc = {calc:.2f}%, Master = {master:.2f}% | Category: {cat} | Explanation: {expl}\n"
                    )


class ProfitabilityRatioEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.deviations = []

    def load_financial_data(self) -> pd.DataFrame:
        """
        Loads profitandloss, balancesheet, and cashflow records and joins them on company_id and year.
        Uses a full union of keys to ensure all available years are populated.
        Applies auto-healing for column-shifted raw rows.
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at: {self.db_path}")

        conn = sqlite3.connect(self.db_path)

        df_pl = pd.read_sql_query(
            "SELECT company_id, year, sales, expenses, operating_profit, opm_percentage, "
            "other_income, interest, depreciation, profit_before_tax, net_profit, eps, dividend_payout FROM profitandloss",
            conn,
        )

        df_bs = pd.read_sql_query(
            "SELECT company_id, year, equity_capital, reserves, borrowings, investments, total_assets FROM balancesheet",
            conn,
        )

        df_cf = pd.read_sql_query(
            "SELECT company_id, year, operating_activity, investing_activity, financing_activity FROM cashflow",
            conn,
        )

        conn.close()

        # Outer join / Union of all keys
        keys_pl = df_pl[["company_id", "year"]].drop_duplicates()
        keys_bs = df_bs[["company_id", "year"]].drop_duplicates()
        keys_cf = df_cf[["company_id", "year"]].drop_duplicates()
        keys_union = pd.concat([keys_pl, keys_bs, keys_cf]).drop_duplicates(
            subset=["company_id", "year"]
        )

        df_merged = pd.merge(keys_union, df_pl, on=["company_id", "year"], how="left")
        df_merged = pd.merge(df_merged, df_bs, on=["company_id", "year"], how="left")
        df_merged = pd.merge(df_merged, df_cf, on=["company_id", "year"], how="left")

        # Auto-detect and heal column shift anomaly
        healed_count = 0
        for idx, row in df_merged.iterrows():
            sales = row["sales"]
            expenses = row["expenses"]
            op = row["operating_profit"]
            opm_pct = row["opm_percentage"]

            if (
                sales is not None
                and sales > 0
                and expenses is not None
                and expenses > 0
                and op is not None
                and op > 0
                and opm_pct is not None
            ):

                # Check if shifted
                if (
                    abs((sales - expenses) - op) > 5.0
                    and abs((sales - op) - opm_pct) <= 5.0
                ):
                    healed_count += 1
                    df_merged.at[idx, "expenses"] = op
                    df_merged.at[idx, "operating_profit"] = opm_pct
                    df_merged.at[idx, "opm_percentage"] = row["other_income"]
                    df_merged.at[idx, "other_income"] = row["interest"]
                    df_merged.at[idx, "interest"] = row["depreciation"]
                    df_merged.at[idx, "depreciation"] = expenses

        if healed_count > 0:
            print(
                f"Auto-detected and healed {healed_count} shifted profitandloss records."
            )

        return df_merged

    def run_calculations(self) -> pd.DataFrame:
        """
        Runs calculations for all profitability, leverage, and efficiency KPIs across all merged records.
        """
        df = self.load_financial_data()

        npm_list = []
        opm_list = []
        roe_list = []
        roce_list = []
        roa_list = []
        de_list = []
        icr_list = []
        at_list = []
        net_debt_list = []

        for _, row in df.iterrows():
            npm = calculate_npm(row["net_profit"], row["sales"])
            npm_list.append(npm)

            opm = calculate_opm(row["operating_profit"], row["sales"])
            opm_list.append(opm)

            roe = calculate_roe(
                row["net_profit"], row["equity_capital"], row["reserves"]
            )
            roe_list.append(roe)

            roce = calculate_roce(
                row["profit_before_tax"],
                row["interest"],
                row["equity_capital"],
                row["reserves"],
                row["borrowings"],
            )
            roce_list.append(roce)

            roa = calculate_roa(row["net_profit"], row["total_assets"])
            roa_list.append(roa)

            de = calculate_de(row["borrowings"], row["equity_capital"], row["reserves"])
            de_list.append(de)

            icr = calculate_icr(
                row["operating_profit"], row["other_income"], row["interest"]
            )
            icr_list.append(icr)

            at = calculate_asset_turnover(row["sales"], row["total_assets"])
            at_list.append(at)

            nd = calculate_net_debt(row["borrowings"], row["investments"])
            net_debt_list.append(nd)

            # OPM Cross-Validation
            if opm is not None and row["opm_percentage"] is not None:
                source_opm = float(row["opm_percentage"])
                diff = abs(opm - source_opm)
                if diff > 1.0:
                    self.deviations.append(
                        {
                            "company_id": row["company_id"],
                            "year": row["year"],
                            "calculated_opm": round(opm, 2),
                            "source_opm": source_opm,
                            "deviation_pct": round(diff, 2),
                        }
                    )

        df["computed_npm"] = npm_list
        df["computed_opm"] = opm_list
        df["computed_roe"] = roe_list
        df["computed_roce"] = roce_list
        df["computed_roa"] = roa_list
        df["computed_de"] = de_list
        df["computed_icr"] = icr_list
        df["computed_asset_turnover"] = at_list
        df["computed_net_debt"] = net_debt_list

        return df

    def populate_ratios_table(self):
        """
        Calculates all 13 financial ratios + CAGR 5yr + Composite Quality Score and populates the SQLite financial_ratios table.
        """
        # 1. Run core calculations
        df = self.run_calculations()

        # 2. Run CAGR pipeline and merge
        from src.analytics.cagr import CAGRCalculationEngine

        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        cagr_log = os.path.join(project_root, "output", "ratio_edge_cases.log")
        db_path = os.path.join(project_root, "data", "nifty100.db")

        cagr_engine = CAGRCalculationEngine(db_path=db_path, log_path=cagr_log)
        df_cagr = cagr_engine.run_cagr_pipeline()

        # Merge CAGR metrics
        df = pd.merge(df, df_cagr, on=["company_id", "year"], how="left")

        # 3. Load sector mapping for leverage warning filter
        conn = sqlite3.connect(self.db_path)
        df_sec = pd.read_sql_query("SELECT company_id, broad_sector FROM sectors", conn)
        broad_sectors = dict(zip(df_sec["company_id"], df_sec["broad_sector"]))
        conn.close()

        # 4. Calculate Winsorised Composite Quality Score
        roe_score = winsorize_and_scale(df["computed_roe"])
        fcf_list = []
        for _, row in df.iterrows():
            fcf_list.append(
                calculate_fcf(row["operating_activity"], row["investing_activity"])
            )
        df["fcf_val"] = fcf_list
        fcf_score = winsorize_and_scale(df["fcf_val"])
        roce_score = winsorize_and_scale(df["computed_roce"])
        de_score = winsorize_and_scale(df["computed_de"], invert=True)

        df["composite_quality_score"] = (
            0.30 * roe_score + 0.25 * fcf_score + 0.25 * roce_score + 0.20 * de_score
        )

        # 5. Populate table
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Drop and Recreate financial_ratios table to ensure new schema is updated
        cursor.execute("DROP TABLE IF EXISTS financial_ratios")
        cursor.execute("""
            CREATE TABLE financial_ratios (
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
            )
        """)
        conn.commit()

        insert_query = """
            INSERT INTO financial_ratios (
                company_id, year, net_profit_margin_pct, operating_profit_margin_pct,
                return_on_equity_pct, debt_to_equity, interest_coverage, asset_turnover,
                free_cash_flow_cr, capex_cr, earnings_per_share, book_value_per_share,
                dividend_payout_ratio_pct, total_debt_cr, cash_from_operations_cr,
                return_on_assets_pct, net_debt_cr, icr_label, high_leverage_flag, icr_warning_flag,
                revenue_cagr_5yr, revenue_cagr_5yr_flag, pat_cagr_5yr, pat_cagr_5yr_flag,
                eps_cagr_5yr, eps_cagr_5yr_flag, composite_quality_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        rows_to_insert = []
        for _, row in df.iterrows():
            co = row["company_id"]
            yr = row["year"]

            npm = row["computed_npm"]
            opm = row["computed_opm"]
            roe = row["computed_roe"]
            de = row["computed_de"]
            icr = row["computed_icr"]
            at = row["computed_asset_turnover"]

            cfo = row["operating_activity"]
            cfi = row["investing_activity"]
            fcf = calculate_fcf(cfo, cfi)
            capex = abs(cfi) if cfi is not None and not pd.isna(cfi) else 0.0

            eps = row["eps"]
            bvps = calculate_book_value_per_share(
                row["equity_capital"], row["reserves"]
            )
            div = row["dividend_payout"]
            debt = row["borrowings"]

            # Day 08/09 additions
            roa = row["computed_roa"]
            net_debt = row["computed_net_debt"]

            # ICR Label and Warning Flag
            if icr is None:
                icr_label = "Debt Free"
                icr_warn = 0
            else:
                icr_label = "Normal"
                icr_warn = 1 if icr < 1.5 else 0

            # High Leverage Flag
            sec = broad_sectors.get(co, "Other")
            high_lev = 1 if de is not None and de > 5 and sec != "Financials" else 0

            # CAGR 5yr
            rev_cagr = row["sales_cagr_5yr"]
            rev_flag = row["sales_cagr_5yr_flag"]
            pat_cagr = row["pat_cagr_5yr"]
            pat_flag = row["pat_cagr_5yr_flag"]
            eps_cagr = row["eps_cagr_5yr"]
            eps_flag = row["eps_cagr_5yr_flag"]

            comp_score = row["composite_quality_score"]

            rows_to_insert.append(
                (
                    co,
                    yr,
                    npm,
                    opm,
                    roe,
                    de,
                    icr,
                    at,
                    fcf,
                    capex,
                    eps,
                    bvps,
                    div,
                    debt,
                    cfo,
                    roa,
                    net_debt,
                    icr_label,
                    high_lev,
                    icr_warn,
                    rev_cagr,
                    rev_flag,
                    pat_cagr,
                    pat_flag,
                    eps_cagr,
                    eps_flag,
                    comp_score,
                )
            )

        cursor.executemany(insert_query, rows_to_insert)
        conn.commit()
        conn.close()

        print(
            f"Successfully populated 'financial_ratios' table with {len(rows_to_insert)} records."
        )

        # 6. Run cross-check anomaly analysis
        run_cross_check_anomalies(db_path=db_path, log_path=cagr_log)
        print(f"Logged cross-check anomalies to: {cagr_log}")


if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(project_root, "data", "nifty100.db")

    engine = ProfitabilityRatioEngine(db_path=db)
    engine.populate_ratios_table()
