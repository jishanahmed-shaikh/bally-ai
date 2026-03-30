"""
Axis Bank statement parser.
Handles the standard Axis Bank account statement PDF format.

Column layout: Date | Transaction Details | Chq/Ref Number | Value Date | Withdrawal | Deposit | Balance
"""
import pdfplumber
from typing import Optional
from app.models import Transaction
from app.pipeline.parsers.utils import normalize_date, clean_amount

AXIS_KEYWORDS = ["axis bank", "axis", "transaction details", "chq/ref number"]

AXIS_COLUMNS = {
    "date": ["date"],
    "narration": ["transaction details", "narration", "description", "particulars"],
    "ref_no": ["chq/ref number", "chq/ref no", "ref no", "cheque no"],
    "withdrawal": ["withdrawal", "debit", "dr"],
    "deposit": ["deposit", "credit", "cr"],
    "balance": ["balance"],
}


def _find_column_index(headers: list[str], keywords: list[str]) -> Optional[int]:
    for i, h in enumerate(headers):
        h_lower = h.lower().strip()
        for kw in keywords:
            if kw in h_lower:
                return i
    return None


def _map_row(row: list, col_map: dict) -> Optional[Transaction]:
    try:
        date_raw = row[col_map["date"]] if col_map.get("date") is not None else ""
        narration_raw = row[col_map["narration"]] if col_map.get("narration") is not None else ""
        ref_raw = row[col_map.get("ref_no", -1)] if col_map.get("ref_no") is not None else ""
        withdrawal_raw = row[col_map["withdrawal"]] if col_map.get("withdrawal") is not None else ""
        deposit_raw = row[col_map["deposit"]] if col_map.get("deposit") is not None else ""
        balance_raw = row[col_map["balance"]] if col_map.get("balance") is not None else ""

        date = normalize_date(str(date_raw or "").strip())
        narration = str(narration_raw or "").strip()

        if not date or not narration:
            return None

        return Transaction(
            date=date,
            narration=narration,
            reference_number=str(ref_raw or "").strip() or None,
            withdrawal=clean_amount(str(withdrawal_raw or "")),
            deposit=clean_amount(str(deposit_raw or "")),
            closing_balance=clean_amount(str(balance_raw or "")),
        )
    except Exception:
        return None


def parse(pdf_path: str) -> list[Transaction]:
    """Parse an Axis Bank statement PDF and return a list of Transaction objects."""
    transactions = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue

                header_row = None
                header_idx = 0
                for i, row in enumerate(table):
                    if row and any(
                        cell and any(kw in str(cell).lower() for kw in ["date", "transaction", "withdrawal", "deposit"])
                        for cell in row
                    ):
                        header_row = [str(c or "").strip() for c in row]
                        header_idx = i
                        break

                if header_row is None:
                    continue

                col_map = {}
                for field, keywords in AXIS_COLUMNS.items():
                    idx = _find_column_index(header_row, keywords)
                    if idx is not None:
                        col_map[field] = idx

                if "date" not in col_map or "narration" not in col_map:
                    continue

                for row in table[header_idx + 1:]:
                    if not row or all(not cell for cell in row):
                        continue
                    t = _map_row([str(c or "").strip() for c in row], col_map)
                    if t:
                        transactions.append(t)

    return transactions
