import pytest
from src.analytics.ratios import calculate_de, calculate_icr, calculate_asset_turnover

# 1. Debt-to-Equity (D/E) Tests
def test_de_normal():
    # Borrowings = 50, Equity = 100, Reserves = 100 -> Shareholders' Equity = 200 -> D/E = 0.25
    assert calculate_de(50.0, 100.0, 100.0) == 0.25
    assert calculate_de(150.0, 50.0, 50.0) == 1.5

def test_de_zero_borrowings():
    # Borrowings = 0 -> D/E = 0.0
    assert calculate_de(0.0, 100.0, 100.0) == 0.0
    assert calculate_de(None, 100.0, 100.0) == 0.0

def test_de_negative_or_zero_equity():
    # Equity + Reserves <= 0 -> D/E = None
    assert calculate_de(50.0, 0.0, 0.0) is None
    assert calculate_de(50.0, -10.0, -10.0) is None
    assert calculate_de(50.0, 10.0, -20.0) is None

def test_de_null_inputs():
    assert calculate_de(50.0, None, None) is None
    # If borrowings is None, treated as 0.0
    assert calculate_de(None, 50.0, 50.0) == 0.0
    # One of equity/reserves is None, treated as 0.0
    assert calculate_de(50.0, 100.0, None) == 0.5
    assert calculate_de(50.0, None, 100.0) == 0.5

# 2. Interest Coverage Ratio (ICR) Tests
def test_icr_normal():
    # Operating Profit = 80, Other Income = 20 -> EBIT = 100. Interest = 10 -> ICR = 10.0
    assert calculate_icr(80.0, 20.0, 10.0) == 10.0
    # Negative Operating Profit
    assert calculate_icr(-30.0, 10.0, 10.0) == -2.0

def test_icr_debt_free():
    # Interest = 0, negative, or None -> ICR = 999.0 (interpreted as 'Debt Free')
    assert calculate_icr(80.0, 20.0, 0.0) == 999.0
    assert calculate_icr(80.0, 20.0, -5.0) == 999.0
    assert calculate_icr(80.0, 20.0, None) == 999.0

def test_icr_null_inputs():
    # Operating Profit and Other Income both None -> ICR = None
    assert calculate_icr(None, None, 10.0) is None
    # One of EBIT parts None -> defaults to 0.0
    assert calculate_icr(80.0, None, 10.0) == 8.0
    assert calculate_icr(None, 20.0, 10.0) == 2.0

# 3. Asset Turnover Tests
def test_asset_turnover_normal():
    # Sales = 500, Total Assets = 250 -> Asset Turnover = 2.0
    assert calculate_asset_turnover(500.0, 250.0) == 2.0
    assert calculate_asset_turnover(0.0, 100.0) == 0.0

def test_asset_turnover_zero_or_negative_assets():
    assert calculate_asset_turnover(500.0, 0.0) is None
    assert calculate_asset_turnover(500.0, -50.0) is None

def test_asset_turnover_null_inputs():
    assert calculate_asset_turnover(None, 250.0) is None
    assert calculate_asset_turnover(500.0, None) is None
