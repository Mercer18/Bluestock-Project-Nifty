from src.analytics.ratios import (
    calculate_npm,
    calculate_opm,
    calculate_roe,
    calculate_roce,
    calculate_roa,
)


# 1. Net Profit Margin (NPM) Tests
def test_npm_normal():
    assert calculate_npm(15.0, 100.0) == 15.0
    assert calculate_npm(-10.0, 100.0) == -10.0
    assert calculate_npm(0.0, 50.0) == 0.0


def test_npm_zero_or_negative_sales():
    assert calculate_npm(10.0, 0.0) is None
    assert calculate_npm(10.0, -50.0) is None


def test_npm_null_inputs():
    assert calculate_npm(None, 100.0) is None
    assert calculate_npm(15.0, None) is None
    assert calculate_npm(None, None) is None


# 2. Operating Profit Margin (OPM) Tests
def test_opm_normal():
    assert calculate_opm(25.0, 100.0) == 25.0
    assert calculate_opm(-5.0, 50.0) == -10.0


def test_opm_zero_or_negative_sales():
    assert calculate_opm(20.0, 0.0) is None
    assert calculate_opm(20.0, -100.0) is None


def test_opm_null_inputs():
    assert calculate_opm(None, 100.0) is None
    assert calculate_opm(25.0, None) is None


# 3. Return on Equity (ROE) Tests
def test_roe_normal():
    # Net profit = 15, Equity = 20, Reserves = 80 -> Equity+Reserves = 100 -> ROE = 15%
    assert calculate_roe(15.0, 20.0, 80.0) == 15.0
    # Negative Net profit
    assert calculate_roe(-10.0, 50.0, 50.0) == -10.0


def test_roe_zero_or_negative_equity():
    # Equity + Reserves <= 0
    assert calculate_roe(15.0, 0.0, 0.0) is None
    assert calculate_roe(15.0, -10.0, -10.0) is None
    assert calculate_roe(15.0, 10.0, -20.0) is None


def test_roe_null_inputs():
    # One or both are None
    assert calculate_roe(None, 50.0, 50.0) is None
    assert calculate_roe(15.0, None, None) is None
    # If net profit exists and one of equity/reserves is None, it should default the None to 0.0
    assert calculate_roe(15.0, 100.0, None) == 15.0
    assert calculate_roe(15.0, None, 100.0) == 15.0


# 4. Return on Capital Employed (ROCE) Tests
def test_roce_normal():
    # PBT = 80, Interest = 20 -> EBIT = 100
    # Equity = 200, Reserves = 200, Borrowings = 100 -> Capital Employed = 500
    # ROCE = 100 / 500 * 100 = 20%
    assert calculate_roce(80.0, 20.0, 200.0, 200.0, 100.0) == 20.0

    # EBIT negative
    assert calculate_roce(-120.0, 20.0, 200.0, 200.0, 100.0) == -20.0


def test_roce_zero_or_negative_capital_employed():
    # Capital Employed <= 0
    assert calculate_roce(80.0, 20.0, 0.0, 0.0, 0.0) is None
    assert calculate_roce(80.0, 20.0, -100.0, -100.0, 100.0) is None


def test_roce_null_inputs():
    # PBT and Interest are both None
    assert calculate_roce(None, None, 200.0, 200.0, 100.0) is None
    # Capital Employed fields are all None
    assert calculate_roce(80.0, 20.0, None, None, None) is None

    # Individual Null defaults
    # PBT = None (0) + Interest = 20 -> EBIT = 20. Capital Employed = 100 -> ROCE = 20%
    assert calculate_roce(None, 20.0, 100.0, None, None) == 20.0
    assert calculate_roce(20.0, None, None, 100.0, None) == 20.0


# 5. Return on Assets (ROA) Tests
def test_roa_normal():
    assert calculate_roa(10.0, 100.0) == 10.0
    assert calculate_roa(-5.0, 100.0) == -5.0
    assert calculate_roa(0.0, 50.0) == 0.0


def test_roa_zero_or_negative_assets():
    assert calculate_roa(10.0, 0.0) is None
    assert calculate_roa(10.0, -10.0) is None


def test_roa_null_inputs():
    assert calculate_roa(None, 100.0) is None
    assert calculate_roa(10.0, None) is None
    assert calculate_roa(None, None) is None
