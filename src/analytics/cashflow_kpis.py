import os
import sqlite3
import pandas as pd
import numpy as np


def calculate_fcf(cfo: float, cfi: float) -> float | None:
    """Calculates Free Cash Flow (FCF) = CFO + CFI."""
    if (cfo is None or pd.isna(cfo)) and (cfi is None or pd.isna(cfi)):
        return None
    cfo_val = cfo if cfo is not None and not pd.isna(cfo) else 0.0
    cfi_val = cfi if cfi is not None and not pd.isna(cfi) else 0.0
    return float(cfo_val + cfi_val)


def calculate_cfo_quality_ratio(cfo: float, net_profit: float) -> float | None:
    """Calculates single year CFO Quality ratio = CFO / Net Profit."""
    if net_profit is None or pd.isna(net_profit) or net_profit == 0:
        return None
    if cfo is None or pd.isna(cfo):
        return None
    return float(cfo / net_profit)


def calculate_cfo_quality_5yr_avg(
    df_company: pd.DataFrame, current_year: str
) -> float | None:
    """Calculates CFO / PAT ratio averaged over a 5-year window up to current_year."""
    try:
        parts = current_year.split("-")
        curr_y = int(parts[0])
        suffix = parts[1]
    except Exception:
        return None

    years_window = [f"{curr_y - i:04d}-{suffix}" for i in range(5)]
    df_window = df_company[df_company["year"].isin(years_window)]

    ratios = []
    for _, r in df_window.iterrows():
        cfo = r["operating_activity"]
        pat = r["net_profit"]
        if pat is not None and not pd.isna(pat) and pat != 0:
            if cfo is not None and not pd.isna(cfo):
                ratios.append(cfo / pat)

    if len(ratios) == 0:
        return None
    return float(np.mean(ratios))


def classify_cfo_quality_label(avg_score: float | None) -> str | None:
    """Classifies CFO Quality: >1.0 = High Quality, 0.5-1.0 = Moderate, <0.5 = Accrual Risk."""
    if avg_score is None:
        return None
    if avg_score > 1.0:
        return "High Quality"
    elif avg_score >= 0.5:
        return "Moderate"
    else:
        return "Accrual Risk"


def calculate_capex_intensity(cfi: float, sales: float) -> float | None:
    """Calculates CapEx Intensity = abs(CFI) / Sales * 100."""
    if sales is None or pd.isna(sales) or sales <= 0:
        return None
    if cfi is None or pd.isna(cfi):
        return None
    return float(abs(cfi) / sales * 100)


def classify_capex_intensity_label(intensity: float | None) -> str | None:
    """Classifies CapEx Intensity: <3% = Asset Light, 3-8% = Moderate, >8% = Capital Intensive."""
    if intensity is None:
        return None
    if intensity < 3.0:
        return "Asset Light"
    elif intensity <= 8.0:
        return "Moderate"
    else:
        return "Capital Intensive"


def calculate_fcf_conversion(fcf: float, op_profit: float) -> float | None:
    """Calculates FCF Conversion Rate = FCF / Operating Profit * 100."""
    if op_profit is None or pd.isna(op_profit) or op_profit == 0:
        return None
    if fcf is None or pd.isna(fcf):
        return None
    return float(fcf / op_profit * 100)


def classify_capital_allocation(
    cfo: float, cfi: float, cff: float, cfo_quality: float = None
) -> str:
    """Classifies capital allocation strategy based on signs of CFO, CFI, CFF (updated for Sprint 2)."""
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
    elif pattern == ("+", "+", "-"):
        return "Liquidating Assets"
    elif pattern == ("-", "+", "+"):
        return "Distress Signal"
    elif pattern == ("-", "-", "+"):
        return "Growth Funded by Debt"
    elif pattern == ("+", "+", "+"):
        return "Cash Accumulator"
    elif pattern == ("-", "-", "-"):
        return "Pre-Revenue"
    elif pattern == ("+", "-", "+"):
        return "Mixed"
    else:
        return "Mixed"


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

        # Load P&L
        df_pl = pd.read_sql_query(
            "SELECT company_id, year, sales, operating_profit, net_profit FROM profitandloss",
            conn,
        )

        # Load Balance Sheet
        df_bs = pd.read_sql_query(
            "SELECT company_id, year, borrowings FROM balancesheet", conn
        )

        conn.close()

        # Merge datasets
        df = pd.merge(df_cf, df_pl, on=["company_id", "year"], how="inner")
        df = pd.merge(df, df_bs, on=["company_id", "year"], how="inner")
        return df

    def compute_all_kpis(self) -> pd.DataFrame:
        """Runs computations for FCF, 5-year average quality score, capex intensity, conversion, and allocation labels."""
        df = self.load_raw_data()

        # Build company-specific dataframes lookup for rolling calculations
        company_dfs = {
            co: df[df["company_id"] == co].copy() for co in df["company_id"].unique()
        }

        fcf_list = []
        cfo_q_list = []
        cfo_q_label_list = []
        capex_int_list = []
        capex_int_label_list = []
        fcf_conv_list = []
        alloc_list = []
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

            # 5-Year Average CFO Quality
            cfo_q_avg = calculate_cfo_quality_5yr_avg(company_dfs[co], yr)
            cfo_q_list.append(cfo_q_avg)
            cfo_q_label_list.append(classify_cfo_quality_label(cfo_q_avg))

            # CapEx Intensity
            capex_int = calculate_capex_intensity(cfi, row["sales"])
            capex_int_list.append(capex_int)
            capex_int_label_list.append(classify_capex_intensity_label(capex_int))

            # FCF Conversion
            fcf_conv = calculate_fcf_conversion(fcf, row["operating_profit"])
            fcf_conv_list.append(fcf_conv)

            # Allocation Label
            label = classify_capital_allocation(cfo, cfi, cff, cfo_q_avg)
            alloc_list.append(label)

            cfo_sign_list.append("+" if (cfo or 0.0) > 0 else "-")
            cfi_sign_list.append("+" if (cfi or 0.0) > 0 else "-")
            cff_sign_list.append("+" if (cff or 0.0) > 0 else "-")

        df["fcf"] = fcf_list
        df["cfo_quality_avg"] = cfo_q_list
        df["cfo_quality_label"] = cfo_q_label_list
        df["capex_intensity"] = capex_int_list
        df["capex_intensity_label"] = capex_int_label_list
        df["fcf_conversion"] = fcf_conv_list
        df["pattern_label"] = alloc_list
        df["cfo_sign"] = cfo_sign_list
        df["cfi_sign"] = cfi_sign_list
        df["cff_sign"] = cff_sign_list

        return df

    def save_deliverables(self):
        """Generates CSV files in the output directory."""
        df_results = self.compute_all_kpis()
        os.makedirs(self.output_dir, exist_ok=True)

        # Save output/capital_allocation.csv
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


if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(project_root, "data", "nifty100.db")
    out_dir = os.path.join(project_root, "output")

    engine = CashFlowKPIEngine(db_path=db, output_dir=out_dir)
    engine.save_deliverables()
