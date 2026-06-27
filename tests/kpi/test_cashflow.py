import pandas as pd
from src.analytics.cashflow_kpis import (
    calculate_fcf,
    calculate_cfo_quality_ratio,
    calculate_cfo_quality_5yr_avg,
    classify_cfo_quality_label,
    calculate_capex_intensity,
    classify_capex_intensity_label,
    classify_capital_allocation,
)


def test_calculate_fcf():
    assert calculate_fcf(100.0, -50.0) == 50.0
    assert calculate_fcf(-100.0, -50.0) == -150.0
    assert calculate_fcf(100.0, None) == 100.0
    assert calculate_fcf(None, -50.0) == -50.0
    assert calculate_fcf(None, None) is None


def test_calculate_cfo_quality_ratio():
    assert calculate_cfo_quality_ratio(100.0, 50.0) == 2.0
    assert calculate_cfo_quality_ratio(100.0, 0.0) is None
    assert calculate_cfo_quality_ratio(100.0, -50.0) == -2.0
    assert calculate_cfo_quality_ratio(None, 50.0) is None


def test_cfo_quality_5yr_avg():
    # Construct a dummy company dataframe
    df = pd.DataFrame(
        [
            {
                "year": "2020-03",
                "operating_activity": 100.0,
                "net_profit": 50.0,
            },  # ratio = 2.0
            {
                "year": "2021-03",
                "operating_activity": 150.0,
                "net_profit": 75.0,
            },  # ratio = 2.0
            {
                "year": "2022-03",
                "operating_activity": 50.0,
                "net_profit": 50.0,
            },  # ratio = 1.0
            {
                "year": "2023-03",
                "operating_activity": 80.0,
                "net_profit": 80.0,
            },  # ratio = 1.0
            {
                "year": "2024-03",
                "operating_activity": 120.0,
                "net_profit": 80.0,
            },  # ratio = 1.5
        ]
    )

    # 5-year average up to 2024-03 should be (2.0 + 2.0 + 1.0 + 1.0 + 1.5) / 5 = 1.5
    assert calculate_cfo_quality_5yr_avg(df, "2024-03") == 1.5

    # 5-year average up to 2022-03 should be (2.0 + 2.0 + 1.0) / 3 = 1.6667
    avg_2022 = calculate_cfo_quality_5yr_avg(df, "2022-03")
    assert round(avg_2022, 4) == 1.6667


def test_classify_cfo_quality_label():
    assert classify_cfo_quality_label(1.5) == "High Quality"
    assert classify_cfo_quality_label(0.8) == "Moderate"
    assert classify_cfo_quality_label(0.3) == "Accrual Risk"
    assert classify_cfo_quality_label(None) is None


def test_calculate_capex_intensity():
    assert calculate_capex_intensity(-50.0, 1000.0) == 5.0
    assert calculate_capex_intensity(50.0, 0.0) is None
    assert calculate_capex_intensity(None, 1000.0) is None


def test_classify_capex_intensity_label():
    assert classify_capex_intensity_label(2.5) == "Asset Light"
    assert classify_capex_intensity_label(5.0) == "Moderate"
    assert classify_capex_intensity_label(10.0) == "Capital Intensive"
    assert classify_capex_intensity_label(None) is None


def test_classify_capital_allocation():
    # 1. (+,-,-) with high cfo_quality -> Shareholder Returns
    assert classify_capital_allocation(100, -50, -20, 1.5) == "Shareholder Returns"
    # 2. (+,-,-) with low cfo_quality -> Reinvestor
    assert classify_capital_allocation(100, -50, -20, 0.5) == "Reinvestor"
    # 3. (+,+,-) -> Liquidating Assets
    assert classify_capital_allocation(100, 50, -20) == "Liquidating Assets"
    # 4. (-,+,+) -> Distress Signal
    assert classify_capital_allocation(-100, 50, 20) == "Distress Signal"
    # 5. (-,-,+) -> Growth Funded by Debt
    assert classify_capital_allocation(-100, -50, 20) == "Growth Funded by Debt"
    # 6. (+,+,+) -> Cash Accumulator
    assert classify_capital_allocation(100, 50, 20) == "Cash Accumulator"
    # 7. (-,-,-) -> Pre-Revenue
    assert classify_capital_allocation(-100, -50, -20) == "Pre-Revenue"
    # 8. (+,-,+) -> Mixed
    assert classify_capital_allocation(100, -50, 20) == "Mixed"
