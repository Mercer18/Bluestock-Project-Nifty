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
        """Generates all Sprint 5 cash flow intelligence deliverables."""
        df_results = self.compute_all_kpis()
        os.makedirs(self.output_dir, exist_ok=True)

        # 1. Save output/capital_allocation.csv (All years)
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

        # Load sector mapping from database
        conn = sqlite3.connect(self.db_path)
        df_sectors = pd.read_sql_query("SELECT company_id, broad_sector as sector FROM sectors", conn)
        conn.close()

        # Merge sectors
        df_merged = df_results.merge(df_sectors, on="company_id", how="left")

        # 2. Compute 5-year FCF CAGR dynamically
        company_dfs = {co: df_merged[df_merged["company_id"] == co].copy() for co in df_merged["company_id"].unique()}
        
        fcf_cagrs = []
        for idx, row in df_merged.iterrows():
            co = row["company_id"]
            yr = row["year"]
            try:
                parts = yr.split("-")
                curr_y = int(parts[0])
                suffix = parts[1]
                start_year = f"{curr_y - 5:04d}-{suffix}"
                df_co = company_dfs[co]
                start_fcf = df_co[df_co["year"] == start_year]["fcf"].values
                end_fcf = row["fcf"]
                if len(start_fcf) > 0 and not pd.isna(start_fcf[0]) and not pd.isna(end_fcf):
                    s_val = start_fcf[0]
                    if s_val <= 0:
                        fcf_cagrs.append(np.nan) # Turnaround or negative base
                    else:
                        fcf_cagrs.append(float(((end_fcf / s_val) ** 0.2) - 1.0) * 100.0)
                else:
                    fcf_cagrs.append(np.nan)
            except Exception:
                fcf_cagrs.append(np.nan)
                
        df_merged["fcf_cagr_5yr"] = fcf_cagrs

        # 3. Compute flags for 2024-03 latest year
        # Distress flag: CFO < 0 and CFF > 0 in latest year
        df_merged["distress_flag"] = np.where(
            (df_merged["operating_activity"] < 0) & (df_merged["financing_activity"] > 0),
            1, 0
        )

        # Deleveraging flag: CFF < 0 and borrowings declining YoY
        deleveraging = []
        for idx, row in df_merged.iterrows():
            co = row["company_id"]
            yr = row["year"]
            cff = row["financing_activity"]
            borr = row["borrowings"]
            try:
                parts = yr.split("-")
                curr_y = int(parts[0])
                suffix = parts[1]
                prev_year = f"{curr_y - 1:04d}-{suffix}"
                df_co = company_dfs[co]
                prev_borr = df_co[df_co["year"] == prev_year]["borrowings"].values
                if len(prev_borr) > 0 and (cff or 0.0) < 0 and borr < prev_borr[0]:
                    deleveraging.append(1)
                else:
                    deleveraging.append(0)
            except Exception:
                deleveraging.append(0)
                
        df_merged["deleveraging_flag"] = deleveraging

        # Latest year filter (2024-03)
        df_latest = df_merged[df_merged["year"] == "2024-03"].copy()

        # Prepare cashflow_intelligence output columns
        # columns: company_id, sector, cfo_quality_score, cfo_quality_label, capex_intensity_pct, capex_label, fcf_cagr_5yr, fcf_conversion_pct, distress_flag, deleveraging_flag, capital_allocation_label
        df_cf_intel = df_latest[[
            "company_id", "sector", "cfo_quality_avg", "cfo_quality_label", 
            "capex_intensity", "capex_intensity_label", "fcf_cagr_5yr", 
            "fcf_conversion", "distress_flag", "deleveraging_flag", "pattern_label"
        ]].rename(columns={
            "cfo_quality_avg": "cfo_quality_score",
            "capex_intensity": "capex_intensity_pct",
            "capex_intensity_label": "capex_label",
            "fcf_conversion": "fcf_conversion_pct",
            "pattern_label": "capital_allocation_label"
        })

        intel_path = os.path.join(self.output_dir, "cashflow_intelligence.xlsx")
        df_cf_intel.to_excel(intel_path, index=False, sheet_name="CF Intelligence")
        print(f"Saved Cash Flow Intelligence to: {intel_path}")

        # 4. Save output/distress_alerts.csv
        # include: company_id, CFO, CFF, net_profit
        df_distress = df_latest[df_latest["distress_flag"] == 1][[
            "company_id", "operating_activity", "financing_activity", "net_profit"
        ]].rename(columns={
            "operating_activity": "CFO",
            "financing_activity": "CFF"
        })
        distress_path = os.path.join(self.output_dir, "distress_alerts.csv")
        df_distress.to_csv(distress_path, index=False)
        print(f"Saved Distress Alerts to: {distress_path}")

        # 5. Save output/pattern_changes.csv (2024 vs 2023 pattern changes)
        pattern_changes = []
        for co in df_merged["company_id"].unique():
            df_co = company_dfs[co]
            p_23 = df_co[df_co["year"] == "2023-03"]["pattern_label"].values
            p_24 = df_co[df_co["year"] == "2024-03"]["pattern_label"].values
            if len(p_23) > 0 and len(p_24) > 0 and p_23[0] != p_24[0]:
                pattern_changes.append({
                    "company_id": co,
                    "previous_pattern": p_23[0],
                    "latest_pattern": p_24[0]
                })
        df_changes = pd.DataFrame(pattern_changes)
        changes_path = os.path.join(self.output_dir, "pattern_changes.csv")
        df_changes.to_csv(changes_path, index=False)
        print(f"Saved Pattern Changes to: {changes_path}")


if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(project_root, "data", "nifty100.db")
    out_dir = os.path.join(project_root, "output")

    engine = CashFlowKPIEngine(db_path=db, output_dir=out_dir)
    engine.save_deliverables()
