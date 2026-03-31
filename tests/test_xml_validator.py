"""
Tests for app/utils/xml_validator.py
"""
from decimal import Decimal
from app.models import Transaction
from app.xml_generator import generate_tally_xml
from app.utils.xml_validator import validate_tally_xml, ValidationResult


def make_transaction(withdrawal="100.00", deposit="0.00", ledger="Office Expenses"):
    return Transaction(
        date="20240101",
        narration="Test narration",
        withdrawal=Decimal(withdrawal),
        deposit=Decimal(deposit),
        closing_balance=Decimal("900.00"),
        assigned_ledger=ledger,
    )


def test_valid_xml_passes_validation():
    t = make_transaction()
    xml_str = generate_tally_xml([t], "HDFC Bank")
    result = validate_tally_xml(xml_str)
    assert result.valid is True
    assert result.errors == []


def test_valid_receipt_passes_validation():
    t = make_transaction(withdrawal="0.00", deposit="500.00", ledger="Sales")
    xml_str = generate_tally_xml([t], "HDFC Bank")
    result = validate_tally_xml(xml_str)
    assert result.valid is True


def test_multiple_transactions_pass_validation():
    transactions = [
        make_transaction(withdrawal="100.00", ledger="Expenses"),
        make_transaction(deposit="200.00", ledger="Sales"),
        make_transaction(withdrawal="50.00", deposit="50.00", ledger="Cash"),
    ]
    xml_str = generate_tally_xml(transactions, "HDFC Bank")
    result = validate_tally_xml(xml_str)
    assert result.valid is True


def test_invalid_xml_string_fails():
    result = validate_tally_xml("this is not xml at all")
    assert result.valid is False
    assert any("parse error" in e.lower() for e in result.errors)


def test_wrong_root_element_fails():
    result = validate_tally_xml("<ROOT><BODY/></ROOT>")
    assert result.valid is False
    assert any("ENVELOPE" in e for e in result.errors)


def test_missing_body_fails():
    result = validate_tally_xml("<ENVELOPE></ENVELOPE>")
    assert result.valid is False
    assert any("BODY" in e for e in result.errors)


def test_validation_result_bool():
    assert bool(ValidationResult(valid=True)) is True
    assert bool(ValidationResult(valid=False, errors=["error"])) is False
