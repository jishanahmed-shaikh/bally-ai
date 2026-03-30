"""
Unit tests for app/xml_generator.py
"""
import xml.etree.ElementTree as ET
from decimal import Decimal
import pytest

from app.models import Transaction
from app.xml_generator import generate_tally_xml, parse_tally_xml


def make_transaction(withdrawal="0.00", deposit="0.00", ledger="Test Ledger"):
    return Transaction(
        date="20240101",
        narration="Test narration",
        withdrawal=Decimal(withdrawal),
        deposit=Decimal(deposit),
        closing_balance=Decimal("1000.00"),
        assigned_ledger=ledger,
    )


def test_payment_voucher():
    """withdrawal=500, deposit=0 → Payment; debit=assigned_ledger ISDEEMEDPOSITIVE=Yes, credit=bank No."""
    t = make_transaction(withdrawal="500.00", deposit="0.00", ledger="Meals & Entertainment")
    xml_str = generate_tally_xml([t], "HDFC Bank")
    root = ET.fromstring(xml_str)

    voucher = root.find(".//VOUCHER")
    assert voucher is not None
    assert voucher.get("VCHTYPE") == "Payment"
    assert voucher.findtext("VOUCHERTYPENAME") == "Payment"

    entries = voucher.findall("LEDGERENTRIES.LIST")
    assert len(entries) == 2

    debit = entries[0]
    assert debit.findtext("LEDGERNAME") == "Meals & Entertainment"
    assert debit.findtext("ISDEEMEDPOSITIVE") == "Yes"
    assert Decimal(debit.findtext("AMOUNT")) == Decimal("-500.00")

    credit = entries[1]
    assert credit.findtext("LEDGERNAME") == "HDFC Bank"
    assert credit.findtext("ISDEEMEDPOSITIVE") == "No"
    assert Decimal(credit.findtext("AMOUNT")) == Decimal("500.00")


def test_receipt_voucher():
    """withdrawal=0, deposit=300 → Receipt; debit=bank ISDEEMEDPOSITIVE=Yes, credit=assigned_ledger No."""
    t = make_transaction(withdrawal="0.00", deposit="300.00", ledger="Sales")
    xml_str = generate_tally_xml([t], "HDFC Bank")
    root = ET.fromstring(xml_str)

    voucher = root.find(".//VOUCHER")
    assert voucher is not None
    assert voucher.get("VCHTYPE") == "Receipt"
    assert voucher.findtext("VOUCHERTYPENAME") == "Receipt"

    entries = voucher.findall("LEDGERENTRIES.LIST")
    assert len(entries) == 2

    debit = entries[0]
    assert debit.findtext("LEDGERNAME") == "HDFC Bank"
    assert debit.findtext("ISDEEMEDPOSITIVE") == "Yes"
    assert Decimal(debit.findtext("AMOUNT")) == Decimal("-300.00")

    credit = entries[1]
    assert credit.findtext("LEDGERNAME") == "Sales"
    assert credit.findtext("ISDEEMEDPOSITIVE") == "No"
    assert Decimal(credit.findtext("AMOUNT")) == Decimal("300.00")


def test_contra_voucher():
    """withdrawal=100, deposit=100 → Contra."""
    t = make_transaction(withdrawal="100.00", deposit="100.00", ledger="Cash")
    xml_str = generate_tally_xml([t], "HDFC Bank")
    root = ET.fromstring(xml_str)

    voucher = root.find(".//VOUCHER")
    assert voucher is not None
    assert voucher.get("VCHTYPE") == "Contra"
    assert voucher.findtext("VOUCHERTYPENAME") == "Contra"


def test_xml_hierarchy():
    """Verify ENVELOPE > BODY > IMPORTDATA > REQUESTDATA > TALLYMESSAGE > VOUCHER path exists."""
    t = make_transaction(withdrawal="100.00")
    xml_str = generate_tally_xml([t], "HDFC Bank")
    root = ET.fromstring(xml_str)

    assert root.tag == "ENVELOPE"
    body = root.find("BODY")
    assert body is not None
    importdata = body.find("IMPORTDATA")
    assert importdata is not None
    requestdata = importdata.find("REQUESTDATA")
    assert requestdata is not None
    tallymessage = requestdata.find("TALLYMESSAGE")
    assert tallymessage is not None
    voucher = tallymessage.find("VOUCHER")
    assert voucher is not None


def test_multiple_transactions():
    """Generate XML with 3 transactions, verify 3 VOUCHER elements."""
    transactions = [
        make_transaction(withdrawal="100.00", ledger="Expenses"),
        make_transaction(deposit="200.00", ledger="Sales"),
        make_transaction(withdrawal="50.00", deposit="50.00", ledger="Cash"),
    ]
    xml_str = generate_tally_xml(transactions, "HDFC Bank")
    root = ET.fromstring(xml_str)

    vouchers = root.findall(".//VOUCHER")
    assert len(vouchers) == 3
