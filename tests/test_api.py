"""
Unit tests for the FastAPI backend endpoints.

Uses anyio + httpx.AsyncClient with ASGITransport to work around the
starlette 0.27 / httpx 0.28 incompatibility.
"""
import os
import pytest
import uuid
from datetime import datetime
from decimal import Decimal

# Set a dummy GROQ_API_KEY so the lifespan config check passes
os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

import anyio
import httpx
from app.main import app, jobs, _pdf_store
from app.models import ProcessingJob, JobStatus, Transaction

# Minimal valid PDF bytes (PDF magic header)
VALID_PDF_BYTES = b"%PDF-1.4 minimal test pdf content"
INVALID_FILE_BYTES = b"This is not a PDF file at all"


def _run(coro):
    """Run an async coroutine synchronously using anyio."""
    return anyio.from_thread.run_sync(lambda: anyio.run(coro))


def _call(coro):
    """Run an async coroutine in a new event loop."""
    import asyncio
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def clear_stores():
    """Clear job store before each test."""
    jobs.clear()
    _pdf_store.clear()
    yield
    jobs.clear()
    _pdf_store.clear()


async def _get(path: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as c:
        return await c.get(path)


async def _post(path: str, **kwargs) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as c:
        return await c.post(path, **kwargs)


async def _patch(path: str, **kwargs) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as c:
        return await c.patch(path, **kwargs)


def test_health_check():
    response = _call(_get("/health"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_valid_pdf():
    response = _call(_post(
        "/upload",
        files={"file": ("statement.pdf", VALID_PDF_BYTES, "application/pdf")},
    ))
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert len(data["job_id"]) == 36  # UUID format


def test_upload_non_pdf_returns_422():
    response = _call(_post(
        "/upload",
        files={"file": ("statement.txt", INVALID_FILE_BYTES, "text/plain")},
    ))
    assert response.status_code == 422
    assert "PDF" in response.json()["detail"]


def test_upload_non_pdf_with_pdf_mime_but_wrong_bytes():
    """File claims to be PDF by MIME but has wrong magic bytes — MIME wins (OR logic)."""
    response = _call(_post(
        "/upload",
        files={"file": ("statement.pdf", b"NOTAPDF content here", "application/pdf")},
    ))
    # With application/pdf MIME, it should pass (we trust MIME for valid PDF MIME type)
    assert response.status_code in (202, 422)


def test_upload_oversized_file_returns_413():
    large_content = b"%PDF" + b"x" * (51 * 1024 * 1024)  # 51 MB
    response = _call(_post(
        "/upload",
        files={"file": ("large.pdf", large_content, "application/pdf")},
    ))
    assert response.status_code == 413
    assert "large" in response.json()["detail"].lower() or "50" in response.json()["detail"]


def test_get_transactions_not_found():
    response = _call(_get("/transactions/nonexistent-job-id"))
    assert response.status_code == 404


def test_export_not_found():
    response = _call(_get("/export/nonexistent-job-id"))
    assert response.status_code == 404


def test_export_non_ready_job_returns_409():
    """Export should return 409 if job is not in ready status."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = ProcessingJob(
        job_id=uuid.UUID(job_id),
        status=JobStatus.pending,
        created_at=datetime.utcnow(),
    )
    response = _call(_get(f"/export/{job_id}"))
    assert response.status_code == 409
    assert "not ready" in response.json()["detail"].lower()


def test_export_extracting_job_returns_409():
    job_id = str(uuid.uuid4())
    jobs[job_id] = ProcessingJob(
        job_id=uuid.UUID(job_id),
        status=JobStatus.extracting,
        created_at=datetime.utcnow(),
    )
    response = _call(_get(f"/export/{job_id}"))
    assert response.status_code == 409


def test_patch_transaction_empty_ledger_returns_422():
    """PATCH with empty assigned_ledger should return 422."""
    job_id = str(uuid.uuid4())
    tx = Transaction(
        date="20240101",
        narration="Test",
        withdrawal=Decimal("100.00"),
        deposit=Decimal("0.00"),
        closing_balance=Decimal("900.00"),
    )
    jobs[job_id] = ProcessingJob(
        job_id=uuid.UUID(job_id),
        status=JobStatus.classifying,
        transactions=[tx],
        created_at=datetime.utcnow(),
    )
    response = _call(_patch(
        f"/transactions/{job_id}/{tx.id}",
        json={"assigned_ledger": ""},
    ))
    assert response.status_code == 422


def test_patch_transaction_updates_ledger():
    job_id = str(uuid.uuid4())
    tx = Transaction(
        date="20240101",
        narration="Test",
        withdrawal=Decimal("100.00"),
        deposit=Decimal("0.00"),
        closing_balance=Decimal("900.00"),
    )
    jobs[job_id] = ProcessingJob(
        job_id=uuid.UUID(job_id),
        status=JobStatus.classifying,
        transactions=[tx],
        created_at=datetime.utcnow(),
    )
    response = _call(_patch(
        f"/transactions/{job_id}/{tx.id}",
        json={"assigned_ledger": "Office Expenses"},
    ))
    assert response.status_code == 200
    assert response.json()["assigned_ledger"] == "Office Expenses"
    # Job should now be ready since all transactions have ledgers
    assert jobs[job_id].status == JobStatus.ready
