import os
import sqlite3
import pandas as pd


def log_anomaly(
    log_path: str,
    company_id: str,
    year: str,
    metric_name: str,
    start_val: float,
    end_val: float,
    category: str,
    explanation: str,
):
    """Writes anomaly warnings with category and explanation to log file."""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    msg = f"[{category}] Company {company_id}, Year {year}, Metric {metric_name}: Base ({start_val}), End ({end_val}) - Category: {category} - Explanation: {explanation}\n"
    with open(log_path, "a") as f:
        f.write(msg)


def calculate_cagr(
    start_val: float,
    end_val: float,
    n_years: int,
    company_id: str = None,
    year: str = None,
    metric_name: str = None,
    log_path: str = None,
) -> tuple[float | None, str | None]:
    """
    Calculates Compound Annual Growth Rate (CAGR) %.
    Formula: ((end_val / start_val) ^ (1/n_years) - 1) * 100
    Returns (cagr_value, flag).
    Handles 6 edge cases.
    """
    if n_years <= 0:
        return None, "INSUFFICIENT"

    if start_val is None or pd.isna(start_val) or end_val is None or pd.isna(end_val):
        return None, "INSUFFICIENT"

    if start_val == 0:
        return None, "ZERO_BASE"

    if start_val > 0 and end_val > 0:
        val = float(((end_val / start_val) ** (1.0 / n_years) - 1.0) * 100)
        return val, None

    if start_val > 0 and end_val <= 0:
        return None, "DECLINE_TO_LOSS"

    if start_val < 0 and end_val > 0:
        if log_path and company_id and year and metric_name:
            log_anomaly(
                log_path,
                company_id,
                year,
                metric_name,
                start_val,
                end_val,
                "TURNAROUND",
                "Decline from loss base to profit end value",
            )
        return None, "TURNAROUND"

    if start_val < 0 and end_val <= 0:
        return None, "BOTH_NEGATIVE"

    return None, None


class CAGRCalculationEngine:
    def __init__(self, db_path: str, log_path: str):
        self.db_path = db_path
        self.log_path = log_path

        # Clear log if exists to ensure clean run
        if os.path.exists(self.log_path):
            try:
                os.remove(self.log_path)
            except PermissionError:
                pass

    def run_cagr_pipeline(self) -> pd.DataFrame:
        """
        Loads P&L data and calculates 3yr, 5yr, and 10yr CAGR for Sales, Net Profit, and EPS.
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at: {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        df_pl = pd.read_sql_query(
            "SELECT company_id, year, sales, net_profit, eps FROM profitandloss", conn
        )
        conn.close()

        # Build lookup dictionary: (company_id, year) -> {sales, net_profit, eps}
        lookup = {}
        for _, row in df_pl.iterrows():
            lookup[(row["company_id"], row["year"])] = {
                "sales": row["sales"],
                "net_profit": row["net_profit"],
                "eps": row["eps"],
            }

        def get_lookback_year(year_str: str, lookback: int) -> str | None:
            try:
                parts = year_str.split("-")
                y = int(parts[0])
                return f"{y - lookback:04d}-{parts[1]}"
            except Exception:
                return None

        cagr_results = []
        for _, row in df_pl.iterrows():
            co = row["company_id"]
            yr = row["year"]

            res = {
                "company_id": co,
                "year": yr,
                "sales_cagr_3yr": None,
                "sales_cagr_3yr_flag": None,
                "sales_cagr_5yr": None,
                "sales_cagr_5yr_flag": None,
                "sales_cagr_10yr": None,
                "sales_cagr_10yr_flag": None,
                "pat_cagr_3yr": None,
                "pat_cagr_3yr_flag": None,
                "pat_cagr_5yr": None,
                "pat_cagr_5yr_flag": None,
                "pat_cagr_10yr": None,
                "pat_cagr_10yr_flag": None,
                "eps_cagr_3yr": None,
                "eps_cagr_3yr_flag": None,
                "eps_cagr_5yr": None,
                "eps_cagr_5yr_flag": None,
                "eps_cagr_10yr": None,
                "eps_cagr_10yr_flag": None,
            }

            def evaluate_cagr_metric(
                metric_key: str, n_years: int
            ) -> tuple[float | None, str | None]:
                start_yr = get_lookback_year(yr, n_years)
                if (co, start_yr) in lookup:
                    start_val = lookup[(co, start_yr)][metric_key]
                    end_val = row[metric_key]
                    return calculate_cagr(
                        start_val=start_val,
                        end_val=end_val,
                        n_years=n_years,
                        company_id=co,
                        year=yr,
                        metric_name=f"{metric_key}_{n_years}yr",
                        log_path=self.log_path,
                    )
                return None, "INSUFFICIENT"

            res["sales_cagr_3yr"], res["sales_cagr_3yr_flag"] = evaluate_cagr_metric(
                "sales", 3
            )
            res["sales_cagr_5yr"], res["sales_cagr_5yr_flag"] = evaluate_cagr_metric(
                "sales", 5
            )
            res["sales_cagr_10yr"], res["sales_cagr_10yr_flag"] = evaluate_cagr_metric(
                "sales", 10
            )

            res["pat_cagr_3yr"], res["pat_cagr_3yr_flag"] = evaluate_cagr_metric(
                "net_profit", 3
            )
            res["pat_cagr_5yr"], res["pat_cagr_5yr_flag"] = evaluate_cagr_metric(
                "net_profit", 5
            )
            res["pat_cagr_10yr"], res["pat_cagr_10yr_flag"] = evaluate_cagr_metric(
                "net_profit", 10
            )

            res["eps_cagr_3yr"], res["eps_cagr_3yr_flag"] = evaluate_cagr_metric(
                "eps", 3
            )
            res["eps_cagr_5yr"], res["eps_cagr_5yr_flag"] = evaluate_cagr_metric(
                "eps", 5
            )
            res["eps_cagr_10yr"], res["eps_cagr_10yr_flag"] = evaluate_cagr_metric(
                "eps", 10
            )

            cagr_results.append(res)

        return pd.DataFrame(cagr_results)

    def print_cagr_summary(self):
        """Runs calculations and prints count of successfully calculated CAGR fields."""
        df_cagr = self.run_cagr_pipeline()
        print("\n=== SPRINT 2: CAGR ENGINE VALIDATION ===")
        print(f"Total records processed: {len(df_cagr)}")
        print(
            f"Sales CAGR Calculated: 3Yr = {df_cagr['sales_cagr_3yr'].notna().sum()} | 5Yr = {df_cagr['sales_cagr_5yr'].notna().sum()} | 10Yr = {df_cagr['sales_cagr_10yr'].notna().sum()}"
        )

        if os.path.exists(self.log_path):
            with open(self.log_path, "r") as f:
                lines = f.readlines()
            print(f"\nTotal turnaround edge cases logged: {len(lines)}")
        else:
            print("\nNo turnaround edge cases logged.")


if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(project_root, "data", "nifty100.db")
    log = os.path.join(project_root, "output", "ratio_edge_cases.log")

    engine = CAGRCalculationEngine(db_path=db, log_path=log)
    engine.print_cagr_summary()
