import pytest
from decimal import Decimal
from pydantic import ValidationError
from app.models import Transaction, ProcessingJob, TallyVoucher, JobStatus, VoucherType
import uuid
from datetime import datetime


def make_transaction(**kwargs):
    defaults = dict(
        date="20240101",
        narration="Test narration",
        withdrawal=Decimal("0.00"),
        deposit=Decimal("100.00"),
        closing_balance=Decimal("1000.00"),
    )
    defaults.update(kwargs)
    return Transaction(**defaults)


def test_transaction_negative_withdrawal_raises():
    with pytest.raises(ValidationError):
        make_transaction(withdrawal=Decimal("-1.00"))


def test_transaction_negative_deposit_raises():
    with pytest.raises(ValidationError):
        make_transaction(deposit=Decimal("-0.01"))


def test_transaction_negative_closing_balance_raises():
    with pytest.raises(ValidationError):
        make_transaction(closing_balance=Decimal("-100.00"))


def test_transaction_zero_amounts_accepted():
    t = make_transaction(withdrawal=Decimal("0.00"), deposit=Decimal("0.00"), closing_balance=Decimal("0.00"))
    assert t.withdrawal == Decimal("0.00")
    assert t.deposit == Decimal("0.00")


def test_transaction_parse_error_defaults_false():
    t = make_transaction()
    assert t.parse_error is False


def test_transaction_id_auto_assigned():
    t = make_transaction()
    assert t.id != ""
    assert len(t.id) == 36  # UUID format


def test_transaction_optional_fields_default_none():
    t = make_transaction()
    assert t.reference_number is None
    assert t.assigned_ledger is None


def test_processing_job_default_status():
    job = ProcessingJob(
        job_id=uuid.uuid4(),
        created_at=datetime.utcnow(),
    )
    assert job.status == JobStatus.pending
    assert job.transactions == []


def test_tally_voucher_fields():
    v = TallyVoucher(
        voucher_type=VoucherType.Payment,
        date="20240101",
        narration="Test",
        debit_ledger="Expenses",
        credit_ledger="HDFC Bank",
        amount=Decimal("500.00"),
    )
    assert v.voucher_type == VoucherType.Payment
    assert v.amount == Decimal("500.00")
