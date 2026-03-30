"""
Shared utilities for bank statement parsers.
"""
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Optional


DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%Y-%m-%d",
]


def normalize_date(date_str: str) -> Optional[str]:
    """
    Normalize a date string to YYYYMMDD format.
    Returns None if the date cannot be parsed.
    """
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y%m%d")
        except ValueError:
            continue
    return None


def clean_amount(value: str) -> Decimal:
    """
    Strip commas, currency symbols, and whitespace from a numeric string.
    Returns Decimal("0.00") for empty/None values.
    """
    if not value or not str(value).strip():
        return Decimal("0.00")
    cleaned = re.sub(r"[₹$,\s]", "", str(value).strip())
    # Handle Dr/Cr suffixes sometimes found in SBI statements
    cleaned = re.sub(r"(Dr|Cr)$", "", cleaned, flags=re.IGNORECASE).strip()
    if not cleaned:
        return Decimal("0.00")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0.00")
