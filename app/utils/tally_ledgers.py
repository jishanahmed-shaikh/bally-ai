"""
Canonical list of Tally ledger names and helper utilities.

This module centralises the ledger list so both the classifier
and the frontend can reference the same source of truth.
"""

TALLY_LEDGERS: list[str] = [
    # Income
    "Sales",
    "Interest Income",
    "Commission Received",
    "Rent Received",
    "Dividend Income",
    # Expenses
    "Purchases",
    "Bank Charges",
    "Interest Expense",
    "Salary",
    "Rent",
    "Electricity Charges",
    "Telephone Charges",
    "Internet Charges",
    "Office Expenses",
    "Travelling Expenses",
    "Conveyance",
    "Meals & Entertainment",
    "Printing & Stationery",
    "Repairs & Maintenance",
    "Professional Fees",
    "Audit Fees",
    "Advertisement",
    "Insurance",
    "Taxes & Duties",
    "Miscellaneous Expenses",
    # Tax liabilities
    "GST Payable",
    "TDS Payable",
    "Income Tax",
    # Assets / Cash
    "Cash",
    "Petty Cash",
    # Liabilities
    "Loan Account",
    "Sundry Creditors",
    # Capital
    "Capital Account",
    "Drawings",
    # Debtors
    "Sundry Debtors",
]

LEDGER_LIST_STR: str = "\n".join(f"- {ledger}" for ledger in TALLY_LEDGERS)


def is_valid_ledger(name: str) -> bool:
    """Return True if the given name is in the canonical ledger list."""
    return name.strip() in TALLY_LEDGERS


def get_ledger_list() -> list[str]:
    """Return a copy of the canonical ledger list."""
    return list(TALLY_LEDGERS)
