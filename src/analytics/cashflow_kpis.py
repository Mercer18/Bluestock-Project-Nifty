import os
import sqlite3
import pandas as pd


def calculate_fcf(cfo: float, cfi: float) -> float | None:
    """Calculates Free Cash Flow (FCF) = CFO + CFI."""
    if (cfo is None or pd.isna(cfo)) and (cfi is None or pd.isna(cfi)):
        return None
    cfo_val = cfo if cfo is not None and not pd.isna(cfo) else 0.0
    cfi_val = cfi if cfi is not None and not pd.isna(cfi) else 0.0
    return float(cfo_val + cfi_val)


def calculate_cfo_quality(cfo: float, net_profit: float) -> float | None:
    """Calculates CFO Quality Score = CFO / Net Profit."""
    if net_profit is None or pd.isna(net_profit) or net_profit == 0:
        return None
    if cfo is None or pd.isna(cfo):
        return None
    return float(cfo / net_profit)


def calculate_capex_intensity(cfi: float, sales: float) -> float | None:
    """Calculates CapEx Intensity = abs(CFI) / Sales * 100."""
    if sales is None or pd.isna(sales) or sales <= 0:
        return None
    if cfi is None or pd.isna(cfi):
        return None
    return float(abs(cfi) / sales * 100)


def calculate_fcf_conversion(fcf: float, op_profit: float) -> float | None:
    """Calculates FCF Conversion Rate = FCF / Operating Profit * 100."""
    if op_profit is None or pd.isna(op_profit) or op_profit <= 0:
        return None
    if fcf is None or pd.isna(fcf):
        return None
    return float(fcf / op_profit * 100)


def classify_capital_allocation(
    cfo: float, cfi: float, cff: float, cfo_quality: float = None
) -> str:
    """Classifies capital allocation strategy based on signs of CFO, CFI, CFF."""
    cfo_val = cfo if cfo is not None and not pd.isna(cfo) else 0.0
    cfi_val = cfi if cfi is not None and not pd.isna(cfi) else 0.0
    cff_val = cff if cff is not None and not pd.isna(cff) else 0.0

    cfo_sign = "+" if cfo_val > 0 else "-"
    cfi_sign = "+" if cfi_val > 0 else "-"
    cff_sign = "+" if cff_val > 0 else "-"

    pattern = (cfo_sign, cfi_sign, cff_sign)

    if pattern == ("+", "-", "-"):
        if cfo_quality is not None and cfo_quality > 1.0:
            return "Shareholder Returns"
        return "Reinvestor"
    elif pattern == ("+", "-", "+"):
        return "Growth / Expansion"
    elif pattern == ("+", "+", "-"):
        return "Deleveraging / Divestment"
    elif pattern == ("+", "+", "+"):
        return "Capital Accumulation"
    elif pattern == ("-", "-", "+"):
        return "Start-up / Early Stage"
    elif pattern == ("-", "+", "+"):
        return "Distress Signal"
    elif pattern == ("-", "-", "-"):
        return "Capital Depletion"
    elif pattern == ("-", "+", "-"):
        return "Contraction / Restructuring"

    return "Other"


class CashFlowKPIEngine:
    def __init__(self, db_path: str, output_dir: str):
        self.db_path = db_path
        self.output_dir = output_dir

    def load_raw_data(self) -> pd.DataFrame:
        """Loads and merges cashflow, profitandloss, and balancesheet records."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at: {self.db_path}")

        conn = sqlite3.connect(self.db_path)

        # Load Cash Flow
        df_cf = pd.read_sql_query(
            "SELECT company_id, year, operating_activity, investing_activity, financing_activity FROM cashflow",
            conn,
        )

        # Load P&L (include sales, operating_profit, net_profit)
        # Note: We use computed OPM/operating profit or raw, here we use raw profitandloss table
        df_pl = pd.read_sql_query(
            "SELECT company_id, year, sales, operating_profit, net_profit FROM profitandloss",
            conn,
        )

        # Load Balance Sheet (include borrowings)
        df_bs = pd.read_sql_query(
            "SELECT company_id, year, borrowings FROM balancesheet", conn
        )

        conn.close()

        # Merge datasets
        df = pd.merge(df_cf, df_pl, on=["company_id", "year"], how="inner")
        df = pd.merge(df, df_bs, on=["company_id", "year"], how="inner")
        return df

    def compute_all_kpis(self) -> pd.DataFrame:
        """Runs computations for FCF, quality score, capex intensity, conversion, allocation labels, and deleveraging/distress flags."""
        df = self.load_raw_data()

        # Build lookup table for borrowings to check deleveraging YoY
        # (company_id, year) -> borrowings
        borrowings_lookup = {}
        for _, row in df.iterrows():
            borrowings_lookup[(row["company_id"], row["year"])] = row["borrowings"]

        def get_lookback_year(year_str: str) -> str | None:
            try:
                parts = year_str.split("-")
                return f"{int(parts[0]) - 1:04d}-{parts[1]}"
            except Exception:
                return None

        fcf_list = []
        cfo_q_list = []
        capex_int_list = []
        fcf_conv_list = []
        alloc_list = []
        deleveraging_list = []
        distress_list = []
        cfo_sign_list = []
        cfi_sign_list = []
        cff_sign_list = []

        for _, row in df.iterrows():
            co = row["company_id"]
            yr = row["year"]

            cfo = row["operating_activity"]
            cfi = row["investing_activity"]
            cff = row["financing_activity"]

            # FCF
            fcf = calculate_fcf(cfo, cfi)
            fcf_list.append(fcf)

            # CFO Quality
            cfo_q = calculate_cfo_quality(cfo, row["net_profit"])
            cfo_q_list.append(cfo_q)

            # CapEx Intensity
            capex_int = calculate_capex_intensity(cfi, row["sales"])
            capex_int_list.append(capex_int)

            # FCF Conversion
            fcf_conv = calculate_fcf_conversion(fcf, row["operating_profit"])
            fcf_conv_list.append(fcf_conv)

            # Allocation Label
            label = classify_capital_allocation(cfo, cfi, cff, cfo_q)
            alloc_list.append(label)

            # CFF signs for CSV
            cfo_sign_list.append("+" if (cfo or 0.0) > 0 else "-")
            cfi_sign_list.append("+" if (cfi or 0.0) > 0 else "-")
            cff_sign_list.append("+" if (cff or 0.0) > 0 else "-")

            # Deleveraging Flag
            # CFF < 0 AND borrowings declining YoY
            prev_yr = get_lookback_year(yr)
            is_deleveraging = 0
            if cff is not None and cff < 0:
                curr_borrowings = row["borrowings"]
                prev_borrowings = borrowings_lookup.get((co, prev_yr))
                if (
                    prev_borrowings is not None
                    and curr_borrowings is not None
                    and curr_borrowings < prev_borrowings
                ):
                    is_deleveraging = 1
            deleveraging_list.append(is_deleveraging)

            # Distress Flag
            # CFO < 0 and CFF > 0
            is_distress = 0
            if cfo is not None and cfo < 0 and cff is not None and cff > 0:
                is_distress = 1
            distress_list.append(is_distress)

        df["fcf"] = fcf_list
        df["cfo_quality"] = cfo_q_list
        df["capex_intensity"] = capex_int_list
        df["fcf_conversion"] = fcf_conv_list
        df["pattern_label"] = alloc_list
        df["cfo_sign"] = cfo_sign_list
        df["cfi_sign"] = cfi_sign_list
        df["cff_sign"] = cff_sign_list
        df["deleveraging_flag"] = deleveraging_list
        df["distress_flag"] = distress_list

        return df

    def save_deliverables(self):
        """Generates CSV files and populates database capital_allocation table."""
        df_results = self.compute_all_kpis()
        os.makedirs(self.output_dir, exist_ok=True)

        # 1. Save capital_allocation.csv
        alloc_path = os.path.join(self.output_dir, "capital_allocation.csv")
        df_alloc_csv = df_results[
            ["company_id", "year", "cfo_sign", "cfi_sign", "cff_sign", "pattern_label"]
        ].copy()
        df_alloc_csv = df_alloc_csv.rename(
            columns={
                "cfo_sign": "CFO_sign",
                "cfi_sign": "CFI_sign",
                "cff_sign": "CFF_sign",
            }
        )
        df_alloc_csv.to_csv(alloc_path, index=False)
        print(f"Saved Capital Allocation deliverables to: {alloc_path}")

        # 2. Save cashflow_intelligence.csv (containing full cash flow KPIs)
        cf_intel_path = os.path.join(self.output_dir, "cashflow_intelligence.csv")
        df_intel_csv = df_results[
            [
                "company_id",
                "year",
                "operating_activity",
                "investing_activity",
                "financing_activity",
                "fcf",
                "cfo_quality",
                "capex_intensity",
                "fcf_conversion",
                "pattern_label",
                "deleveraging_flag",
                "distress_flag",
            ]
        ].copy()
        df_intel_csv.to_csv(cf_intel_path, index=False)
        print(f"Saved Cash Flow Intelligence KPIs to: {cf_intel_path}")

        # 3. Populate capital_allocation table in nifty100.db
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS capital_allocation (
                company_id VARCHAR,
                year VARCHAR,
                cfo_sign VARCHAR,
                cfi_sign VARCHAR,
                cff_sign VARCHAR,
                pattern_label VARCHAR,
                PRIMARY KEY (company_id, year),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        conn.commit()

        # Insert/Replace records
        cursor.execute("DELETE FROM capital_allocation")
        for _, row in df_alloc_csv.iterrows():
            cursor.execute(
                "INSERT INTO capital_allocation (company_id, year, cfo_sign, cfi_sign, cff_sign, pattern_label) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    row["company_id"],
                    row["year"],
                    row["CFO_sign"],
                    row["CFI_sign"],
                    row["CFF_sign"],
                    row["pattern_label"],
                ),
            )
        conn.commit()
        conn.close()
        print("Successfully updated database table 'capital_allocation'.")

    def print_summary_report(self):
        """Runs calculations and prints count summary."""
        df_results = self.compute_all_kpis()
        print("\n=== SPRINT 2: CASH FLOW KPI ENGINE VALIDATION ===")
        print(f"Total company-year combinations evaluated: {len(df_results)}")
        print(f"Calculated FCF count: {df_results['fcf'].notna().sum()}")
        print(
            f"Calculated CFO Quality count: {df_results['cfo_quality'].notna().sum()}"
        )
        print(
            f"Calculated CapEx Intensity count: {df_results['capex_intensity'].notna().sum()}"
        )
        print(
            f"Calculated FCF Conversion count: {df_results['fcf_conversion'].notna().sum()}"
        )
        print(f"Flagged for Deleveraging: {df_results['deleveraging_flag'].sum()}")
        print(f"Flagged for Distress: {df_results['distress_flag'].sum()}")

        print("\nCapital Allocation Distribution:")
        print(df_results["pattern_label"].value_counts().to_string())


if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(project_root, "data", "nifty100.db")
    out_dir = os.path.join(project_root, "data")

    engine = CashFlowKPIEngine(db_path=db, output_dir=out_dir)
    engine.save_deliverables()
    engine.print_summary_report()
