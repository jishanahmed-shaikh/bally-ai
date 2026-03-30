from decimal import Decimal
from enum import Enum
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator
import uuid


class JobStatus(str, Enum):
    pending = "pending"
    extracting = "extracting"
    classifying = "classifying"
    ready = "ready"
    failed = "failed"


class VoucherType(str, Enum):
    Receipt = "Receipt"
    Payment = "Payment"
    Contra = "Contra"


class Transaction(BaseModel):
    id: str = ""
    date: str  # YYYYMMDD
    narration: str
    reference_number: Optional[str] = None
    withdrawal: Decimal
    deposit: Decimal
    closing_balance: Decimal
    assigned_ledger: Optional[str] = None
    parse_error: bool = False

    def model_post_init(self, __context):
        if not self.id:
            object.__setattr__(self, 'id', str(uuid.uuid4()))

    @field_validator("withdrawal", "deposit", "closing_balance", mode="before")
    @classmethod
    def must_be_non_negative(cls, v):
        val = Decimal(str(v))
        if val < 0:
            raise ValueError(f"Amount must be non-negative, got {val}")
        return val


class ProcessingJob(BaseModel):
    job_id: UUID
    status: JobStatus = JobStatus.pending
    transactions: List[Transaction] = []
    created_at: datetime
    bank_ledger_name: str = "Bank Account"
    error_detail: Optional[str] = None


class TallyVoucher(BaseModel):
    voucher_type: VoucherType
    date: str  # YYYYMMDD
    narration: str
    debit_ledger: str
    credit_ledger: str
    amount: Decimal
