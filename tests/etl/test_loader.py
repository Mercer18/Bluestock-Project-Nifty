import pytest
import pandas as pd
import numpy as np
from src.etl.loader import clean_dataframe_strings, ETLEngine

def test_clean_dataframe_strings_headers():
    df = pd.DataFrame(columns=["  ticker  ", " sales_growth \n"])
    df_clean = clean_dataframe_strings(df)
    assert list(df_clean.columns) == ["ticker", "sales_growth"]

def test_clean_dataframe_strings_values():
    df = pd.DataFrame({
        "ticker": [" tcs ", "  infy  ", None],
        "value": [10.0, 20.0, np.nan]
    })
    df_clean = clean_dataframe_strings(df)
    assert df_clean.iloc[0]["ticker"] == "tcs"
    assert df_clean.iloc[1]["ticker"] == "infy"
    assert pd.isna(df_clean.iloc[2]["ticker"])

def test_clean_dataframe_strings_empty_cells():
    df = pd.DataFrame({
        "ticker": ["", "  ", "pnb"]
    })
    df_clean = clean_dataframe_strings(df)
    assert pd.isna(df_clean.iloc[0]["ticker"])
    assert pd.isna(df_clean.iloc[1]["ticker"])
    assert df_clean.iloc[2]["ticker"] == "pnb"

def test_etl_engine_init():
    # Test initialization metrics setup
    etl = ETLEngine(db_path="mock.db", raw_dir="raw", supporting_dir="supp")
    assert etl.db_path == "mock.db"
    assert etl.raw_dir == "raw"
    assert etl.supporting_dir == "supp"
    assert len(etl.audit_records) == 0

def test_etl_engine_audit_log_fields():
    etl = ETLEngine(db_path="mock.db", raw_dir="raw", supporting_dir="supp")
    # Simulate a table insert audit log
    etl.audit_records.append({
        "table_name": "companies",
        "rows_in": 92,
        "rows_out": 92,
        "rejected": 0,
        "timestamp": "2026-06-18 12:00:00",
        "runtime_s": "0.0150"
    })
    assert len(etl.audit_records) == 1
    assert etl.audit_records[0]["table_name"] == "companies"
    assert etl.audit_records[0]["rows_out"] == 92

def test_load_excel_file_not_found():
    from src.etl.loader import load_excel_file
    with pytest.raises(FileNotFoundError):
        load_excel_file("non_existent_file.xlsx")

def test_dataframe_ticker_normalisation():
    df = pd.DataFrame({
        "company_id": [" tcs ", "  infy  "]
    })
    from src.etl.normaliser import normalize_ticker
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    assert df.iloc[0]["company_id"] == "TCS"
    assert df.iloc[1]["company_id"] == "INFY"

def test_dataframe_year_normalisation():
    df = pd.DataFrame({
        "year": ["Mar-23", "FY23"]
    })
    from src.etl.normaliser import normalize_year
    df["year"] = df["year"].apply(normalize_year)
    assert df.iloc[0]["year"] == "2023-03"
    assert df.iloc[1]["year"] == "2023-03"

def test_etl_engine_failures_init():
    etl = ETLEngine(db_path="mock.db", raw_dir="raw", supporting_dir="supp")
    assert len(etl.validator.failures) == 0

def test_financial_sectors_init():
    etl = ETLEngine(db_path="mock.db", raw_dir="raw", supporting_dir="supp")
    assert len(etl.validator.financial_sectors) == 0
