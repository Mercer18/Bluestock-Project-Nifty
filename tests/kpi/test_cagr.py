import os
import pytest
from src.analytics.cagr import calculate_cagr


def test_cagr_normal():
    # 1. Positive + Positive (normal)
    val, flag = calculate_cagr(100.0, 133.1, 3)
    assert pytest.approx(val, abs=1e-2) == 10.0
    assert flag is None

    val, flag = calculate_cagr(100.0, 200.0, 5)
    assert pytest.approx(val, abs=1e-2) == 14.8698
    assert flag is None

    # Zero growth
    val, flag = calculate_cagr(100.0, 100.0, 5)
    assert val == 0.0
    assert flag is None


def test_cagr_decline_to_loss():
    # 2. Positive + Negative -> DECLINE_TO_LOSS
    val, flag = calculate_cagr(100.0, -10.0, 3)
    assert val is None
    assert flag == "DECLINE_TO_LOSS"

    val, flag = calculate_cagr(100.0, 0.0, 3)
    assert val is None
    assert flag == "DECLINE_TO_LOSS"


def test_cagr_turnaround():
    # 3. Negative + Positive -> TURNAROUND
    val, flag = calculate_cagr(-50.0, 100.0, 3)
    assert val is None
    assert flag == "TURNAROUND"


def test_cagr_both_negative():
    # 4. Negative + Negative -> BOTH_NEGATIVE
    val, flag = calculate_cagr(-50.0, -10.0, 3)
    assert val is None
    assert flag == "BOTH_NEGATIVE"

    val, flag = calculate_cagr(-50.0, 0.0, 3)
    assert val is None
    assert flag == "BOTH_NEGATIVE"


def test_cagr_zero_base():
    # 5. Zero base -> ZERO_BASE
    val, flag = calculate_cagr(0.0, 100.0, 3)
    assert val is None
    assert flag == "ZERO_BASE"


def test_cagr_insufficient():
    # 6. Less than n years of data / Null -> INSUFFICIENT
    val, flag = calculate_cagr(None, 100.0, 3)
    assert val is None
    assert flag == "INSUFFICIENT"

    val, flag = calculate_cagr(100.0, None, 3)
    assert val is None
    assert flag == "INSUFFICIENT"

    val, flag = calculate_cagr(100.0, 120.0, 0)
    assert val is None
    assert flag == "INSUFFICIENT"


def test_cagr_turnaround_logging(tmp_path):
    log_file = os.path.join(tmp_path, "ratio_edge_cases.log")

    val, flag = calculate_cagr(
        start_val=-50.0,
        end_val=100.0,
        n_years=3,
        company_id="TESTCO",
        year="2024-03",
        metric_name="net_profit_3yr",
        log_path=log_file,
    )

    assert val is None
    assert flag == "TURNAROUND"
    assert os.path.exists(log_file)
    with open(log_file, "r") as f:
        content = f.read()
    assert "[TURNAROUND]" in content
    assert "TESTCO" in content
