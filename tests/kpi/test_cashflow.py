from src.analytics.cashflow_kpis import (
    calculate_fcf,
    calculate_cfo_quality,
    calculate_capex_intensity,
    calculate_fcf_conversion,
    classify_capital_allocation,
)


# 1. Free Cash Flow (FCF) Tests
def test_fcf_normal():
    assert calculate_fcf(100.0, -50.0) == 50.0
    assert calculate_fcf(-30.0, -20.0) == -50.0


def test_fcf_null_defaults():
    assert calculate_fcf(100.0, None) == 100.0
    assert calculate_fcf(None, -50.0) == -50.0
    assert calculate_fcf(None, None) is None


# 2. CFO Quality Score Tests
def test_cfo_quality_normal():
    assert calculate_cfo_quality(150.0, 100.0) == 1.5
    assert calculate_cfo_quality(-50.0, 100.0) == -0.5


def test_cfo_quality_zero_profit():
    assert calculate_cfo_quality(100.0, 0.0) is None
    assert calculate_cfo_quality(100.0, None) is None


# 3. CapEx Intensity Tests
def test_capex_intensity_normal():
    # abs(cfi) / sales * 100
    # abs(-80.0) / 1000.0 * 100 = 8.0%
    assert calculate_capex_intensity(-80.0, 1000.0) == 8.0


def test_capex_intensity_zero_or_negative_sales():
    assert calculate_capex_intensity(-80.0, 0.0) is None
    assert calculate_capex_intensity(-80.0, -100.0) is None


# 4. FCF Conversion Rate Tests
def test_fcf_conversion_normal():
    # fcf / op_profit * 100
    # 50.0 / 200.0 * 100 = 25.0%
    assert calculate_fcf_conversion(50.0, 200.0) == 25.0


def test_fcf_conversion_zero_or_negative_profit():
    assert calculate_fcf_conversion(50.0, 0.0) is None
    assert calculate_fcf_conversion(50.0, -50.0) is None


# 5. Capital Allocation Classification Matrix Tests
def test_classify_capital_allocation():
    # (+, -, -)
    assert (
        classify_capital_allocation(100.0, -50.0, -20.0, 1.5) == "Shareholder Returns"
    )
    assert classify_capital_allocation(100.0, -50.0, -20.0, 0.8) == "Reinvestor"

    # (+, -, +)
    assert classify_capital_allocation(100.0, -50.0, 20.0) == "Growth / Expansion"

    # (+, +, -)
    assert (
        classify_capital_allocation(100.0, 50.0, -20.0) == "Deleveraging / Divestment"
    )

    # (+, +, +)
    assert classify_capital_allocation(100.0, 50.0, 20.0) == "Capital Accumulation"

    # (-, -, +)
    assert classify_capital_allocation(-100.0, -50.0, 20.0) == "Start-up / Early Stage"

    # (-, +, +)
    assert classify_capital_allocation(-100.0, 50.0, 20.0) == "Distress Signal"

    # (-, -, -)
    assert classify_capital_allocation(-100.0, -50.0, -20.0) == "Capital Depletion"

    # (-, +, -)
    assert (
        classify_capital_allocation(-100.0, 50.0, -20.0)
        == "Contraction / Restructuring"
    )
