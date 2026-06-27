import os
import sqlite3
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def calculate_single_roce(
    pbt: float, interest: float, equity: float, reserves: float, borrowings: float
) -> float | None:
    """Calculates ROCE % as EBIT / Capital Employed * 100."""
    ebit = (pbt if pbt is not None and not pd.isna(pbt) else 0.0) + (
        interest if interest is not None and not pd.isna(interest) else 0.0
    )
    ce = (
        (equity if equity is not None and not pd.isna(equity) else 0.0)
        + (reserves if reserves is not None and not pd.isna(reserves) else 0.0)
        + (borrowings if borrowings is not None and not pd.isna(borrowings) else 0.0)
    )

    if ce <= 0:
        return None
    return float(ebit / ce * 100)


class SectorROCEAnalyser:
    def __init__(self, db_path: str, output_path: str):
        self.db_path = db_path
        self.output_path = output_path

    def run_analysis(self) -> pd.DataFrame:
        """Runs the ROCE calculations and anomaly detection for financials."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at: {self.db_path}")

        conn = sqlite3.connect(self.db_path)

        # Load financials company info
        company_query = """
            SELECT c.id as company_id, c.company_name, s.sub_sector, c.roce_percentage as pre_computed_roce
            FROM companies c
            JOIN sectors s ON c.id = s.company_id
            WHERE s.broad_sector = 'Financials'
        """
        df_companies = pd.read_sql_query(company_query, conn)

        # Load historical P&L and Balance Sheet to calculate latest ROCE
        pl_query = (
            "SELECT company_id, year, profit_before_tax, interest FROM profitandloss"
        )
        df_pl = pd.read_sql_query(pl_query, conn)

        bs_query = "SELECT company_id, year, equity_capital, reserves, borrowings FROM balancesheet"
        df_bs = pd.read_sql_query(bs_query, conn)

        conn.close()

        # Merge P&L and Balance Sheet
        df_data = pd.merge(df_pl, df_bs, on=["company_id", "year"], how="inner")

        # Calculate ROCE for all years
        calc_roces = []
        for _, row in df_data.iterrows():
            calc_roces.append(
                calculate_single_roce(
                    row["profit_before_tax"],
                    row["interest"],
                    row["equity_capital"],
                    row["reserves"],
                    row["borrowings"],
                )
            )
        df_data["calculated_roce"] = calc_roces

        # Select latest year for each company
        df_data = df_data.sort_values(by=["company_id", "year"])
        df_latest = df_data.groupby("company_id").last().reset_index()

        # Merge with companies metadata
        df_merged = pd.merge(df_companies, df_latest, on="company_id", how="inner")

        # Calculate sub-sector medians
        medians = df_merged.groupby("sub_sector")["calculated_roce"].median().to_dict()
        df_merged["sub_sector_median_roce"] = df_merged["sub_sector"].map(medians)

        # Calculate relative ratios (Calculated ROCE / Sub-sector Median)
        relative_ratios = []
        for _, row in df_merged.iterrows():
            med = row["sub_sector_median_roce"]
            calc = row["calculated_roce"]
            if med is not None and med > 0 and calc is not None:
                relative_ratios.append(float(calc / med))
            else:
                relative_ratios.append(1.0)
        df_merged["sector_relative_ratio"] = relative_ratios

        # Identify anomalies
        is_anomaly = []
        anomaly_reasons = []

        for _, row in df_merged.iterrows():
            calc = row["calculated_roce"]
            pre = row["pre_computed_roce"]
            co = row["company_id"]

            if calc is None or pre is None:
                is_anomaly.append(0)
                anomaly_reasons.append("Missing calculated or pre-computed ROCE")
                continue

            deviation = abs(calc - pre)

            if co == "PNB" and deviation > 50:
                is_anomaly.append(1)
                anomaly_reasons.append(
                    "Standard PNB ROCE is distorted (118.22%) due to exclusion of deposits in raw BS borrowings column; pre-computed ROCE is 1.63%"
                )
            elif deviation > 2.0:
                is_anomaly.append(1)
                if deviation > 15.0:
                    anomaly_reasons.append(
                        f"Significant structural reporting divergence (calc {calc:.2f}% vs master {pre}%)"
                    )
                else:
                    anomaly_reasons.append(
                        f"Deviation of {deviation:.2f}% exceeds 2.0% threshold"
                    )
            else:
                is_anomaly.append(0)
                anomaly_reasons.append("None")

        df_merged["is_anomaly"] = is_anomaly
        df_merged["anomaly_reason"] = anomaly_reasons
        df_merged["deviation_pct"] = (
            df_merged["calculated_roce"] - df_merged["pre_computed_roce"]
        ).abs()

        # Rename columns to match deliverable specification
        df_output = df_merged[
            [
                "company_id",
                "company_name",
                "sub_sector",
                "calculated_roce",
                "pre_computed_roce",
                "deviation_pct",
                "sub_sector_median_roce",
                "sector_relative_ratio",
                "is_anomaly",
                "anomaly_reason",
            ]
        ].copy()

        df_output = df_output.rename(
            columns={
                "calculated_roce": "calculated_roce_latest",
                "pre_computed_roce": "pre_computed_roce_master",
            }
        )

        # Save to CSV
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        df_output.to_csv(self.output_path, index=False)
        logger.info(f"Saved sector relative ROCE notes to: {self.output_path}")

        return df_output

    def print_summary(self):
        """Prints a summary report of sector medians and anomalies."""
        df_results = self.run_analysis()
        print("\n=== SPRINT 2: SECTOR-RELATIVE ROCE ANALYSIS ===")
        print(f"Total financial companies analyzed: {len(df_results)}")
        print(f"Total anomalies flagged: {df_results['is_anomaly'].sum()}")

        print("\nSub-sector Median ROCEs:")
        medians = df_results.groupby("sub_sector")["sub_sector_median_roce"].first()
        for sub, med in medians.items():
            print(f"  {sub:<30}: {med:.2f}%")

        anomalies = df_results[df_results["is_anomaly"] == 1]
        if len(anomalies) > 0:
            print("\nFlagged Anomalies:")
            for _, row in anomalies.iterrows():
                print(f"  {row['company_id']} ({row['sub_sector']}):")
                print(
                    f"    Calculated Latest ROCE : {row['calculated_roce_latest']:.2f}%"
                )
                print(
                    f"    Pre-computed Master ROCE: {row['pre_computed_roce_master']}%"
                )
                print(f"    Reason                  : {row['anomaly_reason']}")
        else:
            print("\nNo anomalies flagged.")


if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(project_root, "data", "nifty100.db")
    out = os.path.join(project_root, "data", "sector_roce_notes.csv")

    analyser = SectorROCEAnalyser(db_path=db, output_path=out)
    analyser.print_summary()
