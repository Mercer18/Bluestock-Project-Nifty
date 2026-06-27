import os
import sqlite3
import pytest
import pandas as pd
from src.analytics.ratios import calculate_book_value_per_share
from src.analytics.sector_roce import calculate_single_roce


def test_calculate_book_value_per_share():
    # Normal case
    assert calculate_book_value_per_share(10.0, 90.0) == 1.0
    # Zero/Negative equity capital
    assert calculate_book_value_per_share(0.0, 90.0) is None
    assert calculate_book_value_per_share(-5.0, 90.0) is None
    # None cases
    assert calculate_book_value_per_share(None, 90.0) is None
    assert calculate_book_value_per_share(10.0, None) == 0.1


def test_calculate_single_roce():
    # Normal case: EBIT = 100, CE = 100 -> 100%
    assert calculate_single_roce(80.0, 20.0, 10.0, 40.0, 50.0) == 100.0
    # Zero Capital Employed
    assert calculate_single_roce(80.0, 20.0, 0.0, 0.0, 0.0) is None
    # Negative Capital Employed
    assert calculate_single_roce(80.0, 20.0, -10.0, -20.0, 10.0) is None
    # Null defaults
    assert calculate_single_roce(None, 20.0, 100.0, None, None) == 20.0


def test_database_populated_counts():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db_path = os.path.join(project_root, "data", "nifty100.db")

    if not os.path.exists(db_path):
        pytest.skip("Database file not available for integration test.")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM financial_ratios")
    cnt = cursor.fetchone()[0]
    conn.close()

    assert cnt == 1155


def test_sector_roce_notes_generated():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    csv_path = os.path.join(project_root, "data", "sector_roce_notes.csv")

    if not os.path.exists(csv_path):
        pytest.skip("Sector ROCE notes CSV file not available for integration test.")

    df = pd.read_csv(csv_path)
    assert len(df) == 22
    assert "company_id" in df.columns
    assert "is_anomaly" in df.columns
    pnb_row = df[df["company_id"] == "PNB"]
    assert len(pnb_row) == 1
    assert pnb_row["is_anomaly"].values[0] == 1
