import os
import time
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from src.etl.normaliser import normalize_ticker, normalize_year
from src.etl.validator import DataValidator

def clean_dataframe_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Strips leading/trailing whitespaces from columns and string cells."""
    df.columns = [str(col).strip() for col in df.columns]
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].apply(lambda x: str(x).strip() if pd.notna(x) else x)
            df[col] = df[col].replace("", np.nan)
    return df

def load_excel_file(filepath: str, header: int = 1) -> pd.DataFrame:
    """Loads an Excel file and applies basic string and key normalisation."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Excel file not found at: {filepath}")
        
    df = pd.read_excel(filepath, header=header)
    df = clean_dataframe_strings(df)
    
    # Normalise tickers
    if "id" in df.columns and filepath.endswith("companies.xlsx"):
        df["id"] = df["id"].apply(normalize_ticker)
    elif "company_id" in df.columns:
        df["company_id"] = df["company_id"].apply(normalize_ticker)
        
    # Normalise years
    if "year" in df.columns:
        df["year"] = df["year"].apply(normalize_year)
    elif "Year" in df.columns:
        df["Year"] = df["Year"].apply(normalize_year)
        
    return df

class ETLEngine:
    def __init__(self, db_path: str, raw_dir: str, supporting_dir: str):
        self.db_path = db_path
        self.raw_dir = raw_dir
        self.supporting_dir = supporting_dir
        self.validator = DataValidator()
        self.audit_records = []

    def init_database(self, schema_path: str):
        """Initializes database schema."""
        print(f"Initializing database at: {self.db_path}")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Remove database if exists to ensure clean loading
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass
            
        with sqlite3.connect(self.db_path) as conn:
            with open(schema_path, "r") as f:
                conn.executescript(f.read())
        print("Database initialized successfully.")

    def run(self):
        """Executes the full end-to-end ETL Ingestion and Validation."""
        start_time = time.time()
        
        # 1. Load Sectors first to identify financial companies (needed for DQ-06 check)
        sectors_path = os.path.join(self.supporting_dir, "sectors.xlsx")
        df_sectors_raw = load_excel_file(sectors_path, header=0)
        
        financial_cos = df_sectors_raw[
            df_sectors_raw["broad_sector"].str.lower() == "financials"
        ]["company_id"].unique()
        self.validator.financial_sectors = set(financial_cos)
        print(f"Identified {len(financial_cos)} financial companies (exempt from DQ-06).")

        # 2. Ingest and Validate Master Company Table
        comp_path = os.path.join(self.raw_dir, "companies.xlsx")
        df_comp_raw = load_excel_file(comp_path, header=1)
        df_comp = self.validator.validate_companies(df_comp_raw)
        valid_companies = set(df_comp["id"].unique())
        print(f"Validated companies master: {len(df_comp)} companies loaded.")

        # 3. Load & Validate profitandloss
        pl_path = os.path.join(self.raw_dir, "profitandloss.xlsx")
        df_pl_raw = load_excel_file(pl_path, header=1)
        df_pl = self.validator.validate_profitandloss(df_pl_raw, valid_companies)

        # 4. Load & Validate balancesheet
        bs_path = os.path.join(self.raw_dir, "balancesheet.xlsx")
        df_bs_raw = load_excel_file(bs_path, header=1)
        df_bs = self.validator.validate_balancesheet(df_bs_raw, valid_companies)

        # 5. Load & Validate cashflow
        cf_path = os.path.join(self.raw_dir, "cashflow.xlsx")
        df_cf_raw = load_excel_file(cf_path, header=1)
        df_cf = self.validator.validate_cashflow(df_cf_raw, valid_companies)

        # DQ-16 Check low coverage warning across financial tables
        self.validator.check_coverage(df_pl, df_bs, df_cf, valid_companies)

        # 6. Load & Validate analysis
        an_path = os.path.join(self.raw_dir, "analysis.xlsx")
        df_an_raw = load_excel_file(an_path, header=1)
        df_an = self.validator.validate_analysis(df_an_raw, valid_companies)

        # 7. Load & Validate documents
        doc_path = os.path.join(self.raw_dir, "documents.xlsx")
        df_doc_raw = load_excel_file(doc_path, header=1)
        df_doc = self.validator.validate_documents(df_doc_raw, valid_companies)

        # 8. Load & Validate prosandcons
        pc_path = os.path.join(self.raw_dir, "prosandcons.xlsx")
        df_pc_raw = load_excel_file(pc_path, header=1)
        df_pc = self.validator.validate_prosandcons(df_pc_raw, valid_companies)

        # 9. Load sectors (validate orphans and deduplicate)
        df_sectors = df_sectors_raw[df_sectors_raw["company_id"].isin(valid_companies)].copy()
        df_sectors = df_sectors.dropna(subset=["company_id"])
        df_sectors = df_sectors.drop_duplicates(subset=["company_id"], keep="last")
        for co in df_sectors_raw[~df_sectors_raw["company_id"].isin(valid_companies)]["company_id"].unique():
            self.validator.log_failure(co, "N/A", "company_id", f"Orphan sector record for company: {co} (DQ-03)", "CRITICAL")

        # 10. Load market cap (validate orphans and deduplicate)
        mc_path = os.path.join(self.supporting_dir, "market_cap.xlsx")
        df_mc_raw = load_excel_file(mc_path, header=0)
        df_mc = df_mc_raw[df_mc_raw["company_id"].isin(valid_companies)].copy()
        df_mc = df_mc.dropna(subset=["company_id", "year"])
        df_mc = df_mc.drop_duplicates(subset=["company_id", "year"], keep="last")
        for co in df_mc_raw[~df_mc_raw["company_id"].isin(valid_companies)]["company_id"].unique():
            self.validator.log_failure(co, "N/A", "company_id", f"Orphan market_cap record for company: {co} (DQ-03)", "CRITICAL")

        # 11. Load stock prices (validate orphans and deduplicate)
        sp_path = os.path.join(self.supporting_dir, "stock_prices.xlsx")
        df_sp_raw = load_excel_file(sp_path, header=0)
        df_sp = df_sp_raw[df_sp_raw["company_id"].isin(valid_companies)].copy()
        df_sp = df_sp.dropna(subset=["company_id", "date"])
        df_sp = df_sp.drop_duplicates(subset=["company_id", "date"], keep="last")
        for co in df_sp_raw[~df_sp_raw["company_id"].isin(valid_companies)]["company_id"].unique():
            self.validator.log_failure(co, "N/A", "company_id", f"Orphan stock_prices record for company: {co} (DQ-03)", "CRITICAL")

        # 12. Load peer groups (validate orphans and deduplicate)
        pg_path = os.path.join(self.supporting_dir, "peer_groups.xlsx")
        df_pg_raw = load_excel_file(pg_path, header=0)
        df_pg = df_pg_raw[df_pg_raw["company_id"].isin(valid_companies)].copy()
        df_pg = df_pg.dropna(subset=["company_id", "peer_group_name"])
        df_pg = df_pg.drop_duplicates(subset=["company_id", "peer_group_name"], keep="last")
        for co in df_pg_raw[~df_pg_raw["company_id"].isin(valid_companies)]["company_id"].unique():
            self.validator.log_failure(co, "N/A", "company_id", f"Orphan peer_groups record for company: {co} (DQ-03)", "CRITICAL")

        # 13. Load financial ratios (validate orphans and deduplicate)
        fr_path = os.path.join(self.supporting_dir, "financial_ratios.xlsx")
        df_fr_raw = load_excel_file(fr_path, header=0)
        df_fr = df_fr_raw[df_fr_raw["company_id"].isin(valid_companies)].copy()
        df_fr = df_fr.dropna(subset=["company_id", "year"])
        df_fr = df_fr.drop_duplicates(subset=["company_id", "year"], keep="last")
        for co in df_fr_raw[~df_fr_raw["company_id"].isin(valid_companies)]["company_id"].unique():
            self.validator.log_failure(co, "N/A", "company_id", f"Orphan financial_ratios record for company: {co} (DQ-03)", "CRITICAL")

        # Write data to SQLite tables
        print("Writing validated datasets to SQLite database...")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            
            # Helper to log insert audit metrics
            def insert_table(df_to_load: pd.DataFrame, table_name: str, raw_count: int):
                t_start = time.time()
                # Drop id column if not PK autoincrement in database tables
                df_to_db = df_to_load.copy()
                if "id" in df_to_db.columns and table_name not in ("companies", "prosandcons", "stock_prices"):
                    df_to_db = df_to_db.drop(columns=["id"])
                
                # In documents table, rename Year -> year, Annual_Report -> annual_report
                if table_name == "documents":
                    df_to_db = df_to_db.rename(columns={"Year": "year", "Annual_Report": "annual_report"})
                # In prosandcons, stock_prices, and analysis, drop id so it autoincrements
                if table_name in ("prosandcons", "stock_prices", "analysis") and "id" in df_to_db.columns:
                    df_to_db = df_to_db.drop(columns=["id"])

                df_to_db.to_sql(table_name, conn, if_exists="append", index=False)
                t_run = time.time() - t_start
                loaded_cnt = len(df_to_load)
                rej_cnt = raw_count - loaded_cnt
                self.audit_records.append({
                    "table_name": table_name,
                    "rows_in": raw_count,
                    "rows_out": loaded_cnt,
                    "rejected": rej_cnt,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "runtime_s": f"{t_run:.4f}"
                })
                print(f"  Loaded table '{table_name}': {loaded_cnt} rows inserted (rejected {rej_cnt}).")

            # Load tables in dependency order
            insert_table(df_comp, "companies", len(df_comp_raw))
            insert_table(df_pl, "profitandloss", len(df_pl_raw))
            insert_table(df_bs, "balancesheet", len(df_bs_raw))
            insert_table(df_cf, "cashflow", len(df_cf_raw))
            insert_table(df_an, "analysis", len(df_an_raw))
            insert_table(df_doc, "documents", len(df_doc_raw))
            insert_table(df_pc, "prosandcons", len(df_pc_raw))
            insert_table(df_sectors, "sectors", len(df_sectors_raw))
            insert_table(df_mc, "market_cap", len(df_mc_raw))
            insert_table(df_sp, "stock_prices", len(df_sp_raw))
            insert_table(df_pg, "peer_groups", len(df_pg_raw))
            insert_table(df_fr, "financial_ratios", len(df_fr_raw))

        # Save audits and failures logs
        failures_path = os.path.join(os.path.dirname(self.db_path), "validation_failures.csv")
        self.validator.save_failures(failures_path)

        audit_path = os.path.join(os.path.dirname(self.db_path), "load_audit.csv")
        pd.DataFrame(self.audit_records).to_csv(audit_path, index=False)
        print(f"Audit log successfully generated at: {audit_path}")
        print(f"ETL pipeline finished in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(project_root, "data", "nifty100.db")
    schema = os.path.join(project_root, "src", "etl", "schema.sql")
    raw = os.path.join(project_root, "data", "raw")
    supp = os.path.join(project_root, "data", "supporting")

    etl = ETLEngine(db_path=db, raw_dir=raw, supporting_dir=supp)
    etl.init_database(schema)
    etl.run()
