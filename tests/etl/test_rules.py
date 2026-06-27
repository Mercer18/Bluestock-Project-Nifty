import pytest
import pandas as pd
from src.etl.validator import DataValidator


@pytest.fixture
def validator():
    return DataValidator()


def test_validate_companies_ok(validator):
    df = pd.DataFrame(
        [
            {
                "id": "TCS",
                "company_name": "Tata Consultancy Services",
                "face_value": 1.0,
            },
            {"id": "INFY", "company_name": "Infosys Ltd", "face_value": 5.0},
        ]
    )
    df_clean = validator.validate_companies(df)
    assert len(df_clean) == 2
    assert len(validator.failures) == 0


def test_validate_companies_duplicate(validator):
    df = pd.DataFrame(
        [
            {"id": "TCS", "company_name": "TCS 1", "face_value": 1.0},
            {"id": "TCS", "company_name": "TCS 2", "face_value": 1.0},
        ]
    )
    with pytest.raises(ValueError) as exc:
        validator.validate_companies(df)
    assert "Duplicate company tickers found" in str(exc.value)
    assert len(validator.failures) == 1
    assert validator.failures[0]["severity"] == "CRITICAL"


def test_validate_companies_ticker_length(validator):
    df = pd.DataFrame(
        [
            {
                "id": "T",
                "company_name": "Too Short",
                "face_value": 1.0,
            },  # Invalid (length 1)
            {
                "id": "A" * 15,
                "company_name": "Too Long",
                "face_value": 1.0,
            },  # Invalid (length 15)
            {"id": "TCS", "company_name": "Valid", "face_value": 1.0},
        ]
    )
    df_clean = validator.validate_companies(df)
    assert len(df_clean) == 1
    assert df_clean.iloc[0]["id"] == "TCS"
    assert len(validator.failures) == 2
    assert validator.failures[0]["severity"] == "CRITICAL"


def test_validate_companies_null_face_value(validator):
    df = pd.DataFrame(
        [{"id": "TVSMOTOR", "company_name": "TVS Motor", "face_value": None}]
    )
    df_clean = validator.validate_companies(df)
    assert len(df_clean) == 1
    assert df_clean.iloc[0]["face_value"] == 1.0
    assert len(validator.failures) == 1
    assert validator.failures[0]["field"] == "face_value"
    assert validator.failures[0]["severity"] == "WARNING"


def test_validate_profitandloss_duplicates_and_orphans(validator):
    pl_df = pd.DataFrame(
        [
            {
                "company_id": "TCS",
                "year": "2023-03",
                "sales": 100,
                "expenses": 80,
                "operating_profit": 20,
                "opm_percentage": 20.0,
            },
            {
                "company_id": "TCS",
                "year": "2023-03",
                "sales": 100,
                "expenses": 75,
                "operating_profit": 25,
                "opm_percentage": 25.0,
            },  # Duplicate (keeps last)
            {
                "company_id": "ORPHAN",
                "year": "2023-03",
                "sales": 100,
                "expenses": 80,
                "operating_profit": 20,
                "opm_percentage": 20.0,
            },  # Orphan
        ]
    )
    valid_companies = {"TCS"}
    df_clean = validator.validate_profitandloss(pl_df, valid_companies)

    assert len(df_clean) == 1
    assert df_clean.iloc[0]["operating_profit"] == 25
    # Should log 1 duplicate critical/warning and 1 orphan critical failure
    assert len(validator.failures) == 2
    severities = [f["severity"] for f in validator.failures]
    assert "CRITICAL" in severities


def test_validate_profitandloss_opm_crosscheck(validator):
    pl_df = pd.DataFrame(
        [
            {
                "company_id": "TCS",
                "year": "2023-03",
                "sales": 100,
                "expenses": 80,
                "operating_profit": 20,
                "opm_percentage": 10.0,
            }  # Calculated OPM is 20%, reported is 10%
        ]
    )
    df_clean = validator.validate_profitandloss(pl_df, {"TCS"})
    assert len(df_clean) == 1
    assert len(validator.failures) == 1
    assert validator.failures[0]["field"] == "opm_percentage"
    assert validator.failures[0]["severity"] == "WARNING"


def test_validate_profitandloss_positive_sales(validator):
    pl_df = pd.DataFrame(
        [
            {
                "company_id": "TCS",
                "year": "2023-03",
                "sales": -10,
                "expenses": 10,
                "operating_profit": -20,
                "opm_percentage": 0.0,
            },
            {
                "company_id": "PNB",
                "year": "2023-03",
                "sales": 0,
                "expenses": 10,
                "operating_profit": -10,
                "opm_percentage": 0.0,
            },
        ]
    )
    validator.financial_sectors = {"PNB"}  # PNB is exempt
    df_clean = validator.validate_profitandloss(pl_df, {"TCS", "PNB"})
    assert len(df_clean) == 2
    # TCS sales <= 0 should log warning; PNB sales <= 0 should be ignored
    assert len(validator.failures) == 1
    assert validator.failures[0]["company_id"] == "TCS"
    assert validator.failures[0]["field"] == "sales"
    assert validator.failures[0]["severity"] == "WARNING"


def test_validate_balancesheet_balance_and_fixed_assets(validator):
    bs_df = pd.DataFrame(
        [
            {
                "company_id": "TCS",
                "year": "2023-03",
                "equity_capital": 10,
                "total_assets": 100,
                "total_liabilities": 105,
                "fixed_assets": -5,
            }  # Mismatch (5% diff) & Negative fixed assets
        ]
    )
    df_clean = validator.validate_balancesheet(bs_df, {"TCS"})
    assert len(df_clean) == 1
    assert df_clean.iloc[0]["fixed_assets"] == 0  # Coerced

    # 1 warning for BS mismatch, 1 warning for negative fixed assets, 1 info for strict balance mismatch (DQ-15)
    assert len(validator.failures) == 3
    issues = [f["issue"] for f in validator.failures]
    assert any("Balance sheet mismatch" in iss for iss in issues)
    assert any("Negative fixed assets coerced to 0" in iss for iss in issues)


def test_validate_cashflow_net_check(validator):
    cf_df = pd.DataFrame(
        [
            {
                "company_id": "TCS",
                "year": "2023-03",
                "operating_activity": 100,
                "investing_activity": -40,
                "financing_activity": -20,
                "net_cash_flow": 10,
            }  # Reported is 10, calc is 40 (diff > 10 Cr)
        ]
    )
    df_clean = validator.validate_cashflow(cf_df, {"TCS"})
    assert len(df_clean) == 1
    assert df_clean.iloc[0]["net_cash_flow"] == 40  # Coerced
    assert len(validator.failures) == 1
    assert validator.failures[0]["severity"] == "WARNING"
