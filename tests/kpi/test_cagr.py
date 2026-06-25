import os
import pytest
from src.analytics.cagr import calculate_cagr

def test_cagr_normal():
    # 3-year CAGR: start = 100, end = 133.1 -> CAGR = 10.0%
    assert pytest.approx(calculate_cagr(100.0, 133.1, 3), abs=1e-2) == 10.0
    # 5-year CAGR: start = 100, end = 200 -> CAGR = 14.87%
    assert pytest.approx(calculate_cagr(100.0, 200.0, 5), abs=1e-2) == 14.8698
    # Zero growth
    assert calculate_cagr(100.0, 100.0, 5) == 0.0

def test_cagr_zero_or_negative_base():
    # start <= 0 and end > 0 -> returns None (logged turnaround)
    assert calculate_cagr(-50.0, 100.0, 3) is None
    assert calculate_cagr(0.0, 100.0, 3) is None
    
    # start <= 0 and end <= 0 -> returns None
    assert calculate_cagr(-50.0, -100.0, 3) is None
    assert calculate_cagr(-50.0, 0.0, 3) is None

def test_cagr_null_inputs():
    assert calculate_cagr(None, 100.0, 3) is None
    assert calculate_cagr(100.0, None, 3) is None
    assert calculate_cagr(100.0, 120.0, 0) is None
    assert calculate_cagr(100.0, 120.0, -5) is None

def test_cagr_turnaround_logging(tmp_path):
    log_file = os.path.join(tmp_path, "ratio_edge_cases.log")
    
    # Run calculation with turnaround
    res = calculate_cagr(
        start_val=-50.0,
        end_val=100.0,
        n_years=3,
        company_id="TESTCO",
        year="2024-03",
        metric_name="net_profit_3yr",
        log_path=log_file
    )
    
    assert res is None
    assert os.path.exists(log_file)
    with open(log_file, "r") as f:
        content = f.read()
    assert "[TURNAROUND]" in content
    assert "TESTCO" in content
    assert "2024-03" in content
    assert "net_profit_3yr" in content
