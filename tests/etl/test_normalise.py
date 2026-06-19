import pytest
from src.etl.normaliser import normalize_ticker, normalize_year

# 15+ test cases for tickers
@pytest.mark.parametrize("ticker_in, expected", [
    ("TCS", "TCS"),
    (" tcs ", "TCS"),
    ("HDFCBANK", "HDFCBANK"),
    ("  hdfcbank  ", "HDFCBANK"),
    ("infy", "INFY"),
    (" INFY ", "INFY"),
    ("reliance", "RELIANCE"),
    ("RELIANCE ", "RELIANCE"),
    ("  tata motors ", "TATA MOTORS"),
    ("M&M", "M&M"),
    ("  m&m  ", "M&M"),
    ("BAJAJ-AUTO", "BAJAJ-AUTO"),
    ("bajaj-auto", "BAJAJ-AUTO"),
    ("  BAJAJ-AUTO ", "BAJAJ-AUTO"),
    ("LICI", "LICI"),
    (" lici ", "LICI")
])
def test_normalize_ticker(ticker_in, expected):
    assert normalize_ticker(ticker_in) == expected

# 20+ test cases for years
@pytest.mark.parametrize("year_in, expected", [
    ("Mar-23", "2023-03"),
    ("Mar 23", "2023-03"),
    ("March-2023", "2023-03"),
    ("March 2023", "2023-03"),
    ("2023", "2023-03"),
    (2023, "2023-03"),
    (2023.0, "2023-03"),
    ("FY23", "2023-03"),
    ("FY 23", "2023-03"),
    ("FY-23", "2023-03"),
    ("FY2023", "2023-03"),
    ("Dec-22", "2022-12"),
    ("Dec 22", "2022-12"),
    ("December-2022", "2022-12"),
    ("Jun-23", "2023-06"),
    ("Jun 23", "2023-06"),
    ("June-2023", "2023-06"),
    ("2023-03", "2023-03"),
    ("2022-12", "2022-12"),
    ("2023-06", "2023-06"),
    # Invalid formats should result in PARSE_ERROR
    ("garbage", "PARSE_ERROR"),
    ("invalid_date", "PARSE_ERROR"),
    ("", "PARSE_ERROR"),
    (None, "PARSE_ERROR"),
    ("123", "PARSE_ERROR"),
    ("Mar-123", "PARSE_ERROR")
])
def test_normalize_year(year_in, expected):
    assert normalize_year(year_in) == expected
