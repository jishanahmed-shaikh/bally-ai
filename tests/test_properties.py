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


# --- Property 10: Voucher type is determined correctly by transaction amounts ---
# Validates: Requirements 8.2, 8.3, 8.4
import xml.etree.ElementTree as ET
from app.xml_generator import generate_tally_xml, parse_tally_xml, generate_tally_xml_from_vouchers


@given(
    withdrawal=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("99999.99"), allow_nan=False, allow_infinity=False).map(lambda x: x.quantize(Decimal("0.01"))),
)
@settings(max_examples=100)
def test_payment_voucher_type_selection(withdrawal):
    """Property 10: withdrawal>0, deposit==0 → Payment voucher."""
    t = Transaction(date="20240101", narration="Test", withdrawal=withdrawal, deposit=Decimal("0.00"), closing_balance=Decimal("1000.00"), assigned_ledger="Expenses")
    xml_str = generate_tally_xml([t], "HDFC Bank")
    root = ET.fromstring(xml_str)
    voucher = root.find(".//VOUCHER")
    assert voucher is not None
    assert voucher.get("VCHTYPE") == "Payment"


@given(
    deposit=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("99999.99"), allow_nan=False, allow_infinity=False).map(lambda x: x.quantize(Decimal("0.01"))),
)
@settings(max_examples=100)
def test_receipt_voucher_type_selection(deposit):
    """Property 10: deposit>0, withdrawal==0 → Receipt voucher."""
    t = Transaction(date="20240101", narration="Test", withdrawal=Decimal("0.00"), deposit=deposit, closing_balance=Decimal("1000.00"), assigned_ledger="Sales")
    xml_str = generate_tally_xml([t], "HDFC Bank")
    root = ET.fromstring(xml_str)
    voucher = root.find(".//VOUCHER")
    assert voucher is not None
    assert voucher.get("VCHTYPE") == "Receipt"


@given(transactions=st.lists(transaction_strategy(require_ledger=True), min_size=1, max_size=10))
@settings(max_examples=100)
def test_xml_hierarchy_property(transactions):
    """Property 11: Generated XML conforms to Tally TDL hierarchy."""
    xml_str = generate_tally_xml(transactions, "HDFC Bank")
    root = ET.fromstring(xml_str)
    assert root.tag == "ENVELOPE"
    body = root.find("BODY")
    assert body is not None
    importdata = body.find("IMPORTDATA")
    assert importdata is not None
    requestdata = importdata.find("REQUESTDATA")
    assert requestdata is not None
    tallymessages = requestdata.findall("TALLYMESSAGE")
    assert len(tallymessages) == len(transactions)


@given(transactions=st.lists(transaction_strategy(require_ledger=True), min_size=1, max_size=5))
@settings(max_examples=50)
def test_xml_roundtrip(transactions):
    """Property 12: XML generation round-trip."""
    xml_str = generate_tally_xml(transactions, "HDFC Bank")
    reparsed = parse_tally_xml(xml_str)
    regenerated = generate_tally_xml_from_vouchers(reparsed, "HDFC Bank")
    reparsed2 = parse_tally_xml(regenerated)
    # Verify same number of vouchers and same types
    assert len(reparsed) == len(reparsed2)
    for v1, v2 in zip(reparsed, reparsed2):
        assert v1.voucher_type == v2.voucher_type
        assert v1.amount == v2.amount
        assert v1.debit_ledger == v2.debit_ledger
        assert v1.credit_ledger == v2.credit_ledger


# --- Property 4: Date normalization is consistent ---
# Validates: Requirements 2.3
import re
import datetime as dt_module
from app.pipeline.parsers.utils import normalize_date, clean_amount


@given(date=st.dates(min_value=dt_module.date(2000, 1, 1), max_value=dt_module.date(2030, 12, 31)))
@settings(max_examples=100)
def test_date_normalization_dd_mm_yyyy(date):
    """Property 4: DD/MM/YYYY input normalizes to valid YYYYMMDD."""
    input_str = date.strftime("%d/%m/%Y")
    result = normalize_date(input_str)
    assert result is not None
    assert len(result) == 8
    assert re.match(r"^\d{8}$", result)
    assert result == date.strftime("%Y%m%d")


@given(date=st.dates(min_value=dt_module.date(2000, 1, 1), max_value=dt_module.date(2030, 12, 31)))
@settings(max_examples=100)
def test_date_normalization_dd_mon_yyyy(date):
    """Property 4: DD Mon YYYY input normalizes to valid YYYYMMDD."""
    input_str = date.strftime("%d %b %Y")
    result = normalize_date(input_str)
    assert result is not None
    assert result == date.strftime("%Y%m%d")


# --- Property 5: Numeric field cleaning preserves value ---
# Validates: Requirements 2.4

@given(
    value=st.decimals(min_value=Decimal("0.00"), max_value=Decimal("9999999.99"), allow_nan=False, allow_infinity=False).map(lambda x: x.quantize(Decimal("0.01")))
)
@settings(max_examples=100)
def test_numeric_cleaning_preserves_value(value):
    """Property 5: formatting with commas/symbols and cleaning returns original value."""
    # Format with Indian number system commas
    formatted = f"₹{value:,}"
    result = clean_amount(formatted)
    assert result == value
