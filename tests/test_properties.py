"""
Property-based tests using Hypothesis.
Each test references the design property it validates.
"""
import pytest
from decimal import Decimal
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from pydantic import ValidationError
from app.models import Transaction, VoucherType


# --- Composite strategy for valid Transaction objects ---

@st.composite
def transaction_strategy(draw, require_ledger=True):
    """Generate valid Transaction objects."""
    date = draw(st.dates(min_value=__import__('datetime').date(2000, 1, 1))).strftime("%Y%m%d")
    narration = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    assume(narration.strip())
    withdrawal = draw(st.decimals(min_value=Decimal("0.00"), max_value=Decimal("999999.99"), allow_nan=False, allow_infinity=False).map(lambda x: x.quantize(Decimal("0.01"))))
    deposit = draw(st.decimals(min_value=Decimal("0.00"), max_value=Decimal("999999.99"), allow_nan=False, allow_infinity=False).map(lambda x: x.quantize(Decimal("0.01"))))
    closing_balance = draw(st.decimals(min_value=Decimal("0.00"), max_value=Decimal("9999999.99"), allow_nan=False, allow_infinity=False).map(lambda x: x.quantize(Decimal("0.01"))))
    assigned_ledger = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'))).map(str.strip)) if require_ledger else None
    assume(not require_ledger or (assigned_ledger and assigned_ledger.strip()))
    return Transaction(
        date=date,
        narration=narration.strip() or "Narration",
        withdrawal=withdrawal,
        deposit=deposit,
        closing_balance=closing_balance,
        assigned_ledger=assigned_ledger if (not require_ledger or (assigned_ledger and assigned_ledger.strip())) else "Miscellaneous",
    )


# --- Property 7: Negative amounts are always rejected by the data model ---
# Validates: Requirements 5.3

@given(amount=st.decimals(max_value=Decimal("-0.01"), allow_nan=False, allow_infinity=False))
@settings(max_examples=100)
def test_negative_withdrawal_always_rejected(amount):
    """Property 7: negative withdrawal raises ValidationError."""
    with pytest.raises(ValidationError):
        Transaction(
            date="20240101",
            narration="Test",
            withdrawal=amount,
            deposit=Decimal("0.00"),
            closing_balance=Decimal("0.00"),
        )


@given(amount=st.decimals(max_value=Decimal("-0.01"), allow_nan=False, allow_infinity=False))
@settings(max_examples=100)
def test_negative_deposit_always_rejected(amount):
    """Property 7: negative deposit raises ValidationError."""
    with pytest.raises(ValidationError):
        Transaction(
            date="20240101",
            narration="Test",
            withdrawal=Decimal("0.00"),
            deposit=amount,
            closing_balance=Decimal("0.00"),
        )
