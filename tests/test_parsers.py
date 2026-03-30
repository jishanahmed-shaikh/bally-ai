"""
Tests for bank statement parsers and shared utilities.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from app.pipeline.parsers.utils import normalize_date, clean_amount
from app.pipeline.parsers import hdfc, icici, sbi


# --- Utility function tests ---

class TestNormalizeDate:
    def test_dd_mm_yyyy_slash(self):
        assert normalize_date("01/01/2024") == "20240101"

    def test_dd_mm_yyyy_dash(self):
        assert normalize_date("15-03-2024") == "20240315"

    def test_dd_mon_yyyy(self):
        assert normalize_date("25 Dec 2023") == "20231225"

    def test_dd_month_yyyy(self):
        assert normalize_date("10 January 2024") == "20240110"

    def test_invalid_date_returns_none(self):
        assert normalize_date("not-a-date") is None

    def test_empty_string_returns_none(self):
        assert normalize_date("") is None

    def test_iso_format(self):
        assert normalize_date("2024-06-15") == "20240615"


class TestCleanAmount:
    def test_plain_number(self):
        assert clean_amount("1000.00") == Decimal("1000.00")

    def test_with_commas(self):
        assert clean_amount("1,23,456.78") == Decimal("123456.78")

    def test_with_rupee_symbol(self):
        assert clean_amount("₹500.00") == Decimal("500.00")

    def test_empty_string(self):
        assert clean_amount("") == Decimal("0.00")

    def test_none_value(self):
        assert clean_amount(None) == Decimal("0.00")

    def test_with_spaces(self):
        assert clean_amount("  1,000.00  ") == Decimal("1000.00")

    def test_dr_suffix(self):
        assert clean_amount("500.00Dr") == Decimal("500.00")

    def test_cr_suffix(self):
        assert clean_amount("1000.00Cr") == Decimal("1000.00")


# --- Parser tests using mocked pdfplumber ---

def _make_mock_pdf(tables_per_page):
    """Create a mock pdfplumber PDF with given tables."""
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_tables.return_value = tables_per_page
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    return mock_pdf


class TestHDFCParser:
    def test_parse_standard_hdfc_table(self):
        table = [
            ["Date", "Narration", "Value Dt", "Ref No./Cheque No.", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"],
            ["01/01/2024", "UPI/Zomato/123456", "01/01/2024", "REF001", "500.00", "", "9500.00"],
            ["02/01/2024", "NEFT/Salary/Company", "02/01/2024", "REF002", "", "50000.00", "59500.00"],
        ]
        mock_pdf = _make_mock_pdf([table])
        with patch("pdfplumber.open", return_value=mock_pdf):
            transactions = hdfc.parse("dummy.pdf")

        assert len(transactions) == 2
        assert transactions[0].date == "20240101"
        assert transactions[0].narration == "UPI/Zomato/123456"
        assert transactions[0].withdrawal == Decimal("500.00")
        assert transactions[0].deposit == Decimal("0.00")
        assert transactions[1].deposit == Decimal("50000.00")
        assert transactions[1].withdrawal == Decimal("0.00")

    def test_parse_skips_empty_rows(self):
        table = [
            ["Date", "Narration", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"],
            ["", "", "", "", ""],
            ["01/01/2024", "Test", "100.00", "", "900.00"],
        ]
        mock_pdf = _make_mock_pdf([table])
        with patch("pdfplumber.open", return_value=mock_pdf):
            transactions = hdfc.parse("dummy.pdf")
        assert len(transactions) == 1


class TestICICIParser:
    def test_parse_standard_icici_table(self):
        table = [
            ["S No.", "Value Date", "Transaction Date", "Cheque Number", "Transaction Remarks", "Withdrawal Amount (INR)", "Deposit Amount (INR)", "Balance (INR)"],
            ["1", "01/01/2024", "01/01/2024", "", "ATM/Cash Withdrawal", "2000.00", "", "8000.00"],
            ["2", "03/01/2024", "03/01/2024", "CHQ001", "Cheque Deposit", "", "5000.00", "13000.00"],
        ]
        mock_pdf = _make_mock_pdf([table])
        with patch("pdfplumber.open", return_value=mock_pdf):
            transactions = icici.parse("dummy.pdf")

        assert len(transactions) == 2
        assert transactions[0].withdrawal == Decimal("2000.00")
        assert transactions[1].deposit == Decimal("5000.00")


class TestSBIParser:
    def test_parse_standard_sbi_table(self):
        table = [
            ["Txn Date", "Value Date", "Description", "Ref No./Cheque No.", "Debit", "Credit", "Balance"],
            ["01 Jan 2024", "01 Jan 2024", "BY TRANSFER-UPI", "UPI123", "1000.00", "", "9000.00"],
            ["05 Jan 2024", "05 Jan 2024", "BY CLEARING-CHQ", "CHQ456", "", "25000.00", "34000.00"],
        ]
        mock_pdf = _make_mock_pdf([table])
        with patch("pdfplumber.open", return_value=mock_pdf):
            transactions = sbi.parse("dummy.pdf")

        assert len(transactions) == 2
        assert transactions[0].date == "20240101"
        assert transactions[0].withdrawal == Decimal("1000.00")
        assert transactions[1].deposit == Decimal("25000.00")
