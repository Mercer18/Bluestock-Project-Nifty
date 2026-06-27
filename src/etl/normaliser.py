import re

MONTH_MAP = {
    "jan": "01",
    "feb": "02",
    "mar": "03",
    "apr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "aug": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dec": "12",
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}


def normalize_ticker(ticker: str) -> str:
    """
    Normalises the ticker: strip whitespace, convert to uppercase.
    """
    if not isinstance(ticker, str):
        ticker = str(ticker)
    return ticker.strip().upper()


def normalize_year(year_val) -> str:
    """
    Normalises diverse year formats into YYYY-MM.
    If parsing fails, returns 'PARSE_ERROR'.
    """
    if year_val is None:
        return "PARSE_ERROR"

    # Convert to string and clean
    val_str = str(year_val).strip()
    if not val_str:
        return "PARSE_ERROR"

    # Pattern 1: Already YYYY-MM
    if re.match(r"^\d{4}-\d{2}$", val_str):
        return val_str

    # Pattern 2: Pure integer or float (e.g. 2023 or 2023.0)
    if re.match(r"^\d{4}(\.0)?$", val_str):
        year = val_str.split(".")[0]
        return f"{year}-03"  # Assume March close

    # Pattern 3: FY prefix (e.g. FY23, FY 23, FY-23, FY2023)
    fy_match = re.match(r"^FY\s*-?\s*(\d{2}|\d{4})$", val_str, re.IGNORECASE)
    if fy_match:
        yr_part = fy_match.group(1)
        if len(yr_part) == 2:
            yr_part = "20" + yr_part
        return f"{yr_part}-03"

    # Pattern 4: Month and Year (e.g. Mar-23, Mar 23, March-2023, Dec-22)
    # Match strings containing alpha month and 2 or 4 digit year
    month_yr_match = re.match(r"^([a-zA-Z]+)\s*[-/]?\s*(\d{2}|\d{4})$", val_str)
    if month_yr_match:
        m_name = month_yr_match.group(1).lower()
        yr_part = month_yr_match.group(2)

        # Resolve month
        m_num = MONTH_MAP.get(m_name)
        if not m_num:
            return "PARSE_ERROR"

        # Resolve year
        if len(yr_part) == 2:
            yr_part = "20" + yr_part
        elif len(yr_part) != 4:
            return "PARSE_ERROR"

        return f"{yr_part}-{m_num}"

    # Pattern 5: Year and Month in other order or style (e.g. 2023-Mar)
    yr_month_match = re.match(r"^(\d{4})\s*[-/]?\s*([a-zA-Z]+)$", val_str)
    if yr_month_match:
        yr_part = yr_month_match.group(1)
        m_name = yr_month_match.group(2).lower()
        m_num = MONTH_MAP.get(m_name)
        if m_num:
            return f"{yr_part}-{m_num}"

    return "PARSE_ERROR"
