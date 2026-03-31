"""
FastAPI backend for the Bank Statement Tally Converter.

Endpoints:
  POST /upload                          - Upload and validate PDF
  POST /process/{job_id}               - Run extraction + classification pipeline
  GET  /transactions/{job_id}          - Get transactions for a job
  PATCH /transactions/{job_id}/{tx_id} - Update assigned_ledger for a transaction
  GET  /export/{job_id}                - Generate and download Tally XML
  GET  /health                         - Health check
"""
import os
import uuid
import tempfile
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel

from app.models import ProcessingJob, JobStatus, Transaction
from app.pipeline.graph import run_pipeline
from app.classifier import classify_transactions
from app.xml_generator import generate_tally_xml
from app.config import get_config, ConfigurationError
from app.utils.tally_ledgers import get_ledger_list

# In-memory job store
jobs: dict[str, ProcessingJob] = {}

# Separate store for PDF bytes (not part of Pydantic model)
_pdf_store: dict[str, bytes] = {}

# PDF magic bytes
PDF_MAGIC = b"%PDF"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate configuration on startup."""
    try:
        get_config()
    except ConfigurationError as e:
        import sys
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)
    yield


app = FastAPI(
    title="Bank Statement Tally Converter",
    description="Convert Indian bank statement PDFs to Tally ERP 9 / Tally Prime XML",
    version="1.0.0",
    lifespan=lifespan,
)


class UploadResponse(BaseModel):
    job_id: str
    message: str


class LedgerUpdateRequest(BaseModel):
    assigned_ledger: str


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/banks")
def list_supported_banks():
    """List all banks supported by the deterministic parser."""
    return {
        "deterministic": [
            {"id": "hdfc", "name": "HDFC Bank"},
            {"id": "icici", "name": "ICICI Bank"},
            {"id": "sbi", "name": "State Bank of India"},
            {"id": "axis", "name": "Axis Bank"},
            {"id": "kotak", "name": "Kotak Mahindra Bank"},
            {"id": "pnb", "name": "Punjab National Bank"},
            {"id": "bob", "name": "Bank of Baroda"},
        ],
        "fallback": "All other banks are processed via Groq LLM fallback extraction.",
    }


@app.get("/ledgers")
def list_ledgers():
    """Return the canonical list of Tally ledger names available for assignment."""
    return {"ledgers": get_ledger_list()}


@app.get("/jobs")
def list_jobs():
    """List all processing jobs with their current status."""
    return {
        "total": len(jobs),
        "jobs": [
            {
                "job_id": str(job.job_id),
                "status": job.status,
                "transaction_count": len(job.transactions),
                "created_at": job.created_at.isoformat(),
                "bank_ledger_name": job.bank_ledger_name,
                "error_detail": job.error_detail,
            }
            for job in jobs.values()
        ],
    }


@app.post("/upload", status_code=202)
async def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    """Upload and validate a bank statement PDF."""
    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is 50 MB, got {len(content) / 1024 / 1024:.1f} MB."
        )

    # Validate PDF by checking magic bytes and MIME type
    is_pdf_mime = file.content_type in ("application/pdf", "application/x-pdf")
    is_pdf_bytes = content[:4] == PDF_MAGIC

    if not (is_pdf_mime or is_pdf_bytes):
        raise HTTPException(
            status_code=422,
            detail="Invalid file type. Only PDF files are accepted. Please upload a valid bank statement PDF."
        )

    # Create job
    job_id = str(uuid.uuid4())
    job = ProcessingJob(
        job_id=uuid.UUID(job_id),
        status=JobStatus.pending,
        created_at=datetime.utcnow(),
    )

    jobs[job_id] = job
    _pdf_store[job_id] = content

    return UploadResponse(
        job_id=job_id,
        message="PDF uploaded successfully. Call POST /process/{job_id} to extract transactions."
    )


@app.post("/process/{job_id}")
async def process_job(job_id: str, bank_ledger_name: str = "Bank Account"):
    """Run the extraction and classification pipeline on an uploaded PDF."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    job = jobs[job_id]
    if job.status not in (JobStatus.pending, JobStatus.failed):
        raise HTTPException(
            status_code=409,
            detail=f"Job is already in status '{job.status}'. Only pending or failed jobs can be processed."
        )

    pdf_content = _pdf_store.get(job_id)
    if not pdf_content:
        raise HTTPException(status_code=404, detail="PDF content not found for this job.")

    # Update status to extracting
    jobs[job_id] = job.model_copy(update={"status": JobStatus.extracting, "bank_ledger_name": bank_ledger_name})

    # Write PDF to temp file for pdfplumber
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_content)
        tmp_path = tmp.name

    try:
        # Run LangGraph extraction pipeline
        result = run_pipeline(tmp_path)

        if result.get("error") and not result.get("transactions"):
            jobs[job_id] = jobs[job_id].model_copy(update={
                "status": JobStatus.failed,
                "error_detail": result["error"],
            })
            raise HTTPException(status_code=500, detail=f"Extraction failed: {result['error']}")

        transactions = result.get("transactions", [])

        # Update status to classifying
        jobs[job_id] = jobs[job_id].model_copy(update={
            "status": JobStatus.classifying,
            "transactions": transactions,
        })

        # Run ledger classification
        classified = classify_transactions(transactions)

        # Check if all ledgers are assigned
        all_assigned = all(t.assigned_ledger for t in classified)
        final_status = JobStatus.ready if all_assigned else JobStatus.classifying

        jobs[job_id] = jobs[job_id].model_copy(update={
            "status": final_status,
            "transactions": classified,
        })

        return {
            "job_id": job_id,
            "status": final_status,
            "transaction_count": len(classified),
            "message": f"Extracted {len(classified)} transactions. Review ledger assignments and call GET /export/{job_id} to download XML."
        }

    except HTTPException:
        raise
    except Exception as e:
        jobs[job_id] = jobs[job_id].model_copy(update={
            "status": JobStatus.failed,
            "error_detail": str(e),
        })
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.get("/transactions/{job_id}")
def get_transactions(job_id: str):
    """Get all transactions for a job, including ledger suggestions and parse errors."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job.status,
        "transaction_count": len(job.transactions),
        "transactions": [t.model_dump() for t in job.transactions],
    }


@app.patch("/transactions/{job_id}/{tx_id}")
def update_transaction_ledger(job_id: str, tx_id: str, body: LedgerUpdateRequest):
    """Update the assigned_ledger for a specific transaction."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    if not body.assigned_ledger or not body.assigned_ledger.strip():
        raise HTTPException(
            status_code=422,
            detail="assigned_ledger cannot be empty or null."
        )

    job = jobs[job_id]
    updated_transactions = []
    found = False

    for t in job.transactions:
        if t.id == tx_id:
            updated_transactions.append(t.model_copy(update={"assigned_ledger": body.assigned_ledger.strip()}))
            found = True
        else:
            updated_transactions.append(t)

    if not found:
        raise HTTPException(status_code=404, detail=f"Transaction '{tx_id}' not found in job '{job_id}'.")

    # Check if all transactions now have ledgers assigned
    all_assigned = all(t.assigned_ledger for t in updated_transactions)
    new_status = JobStatus.ready if all_assigned else job.status

    jobs[job_id] = job.model_copy(update={
        "transactions": updated_transactions,
        "status": new_status,
    })

    return {
        "job_id": job_id,
        "tx_id": tx_id,
        "assigned_ledger": body.assigned_ledger.strip(),
        "job_status": new_status,
    }


@app.get("/export/{job_id}")
def export_tally_xml(job_id: str):
    """Generate and return the Tally XML file for a completed job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    job = jobs[job_id]

    if job.status != JobStatus.ready:
        raise HTTPException(
            status_code=409,
            detail=f"Job is not ready for export. Current status: '{job.status}'. All transactions must have an assigned_ledger before exporting."
        )

    xml_content = generate_tally_xml(job.transactions, job.bank_ledger_name)

    return FastAPIResponse(
        content=xml_content,
        media_type="application/xml",
        headers={
            "Content-Disposition": f"attachment; filename=tally_import_{job_id[:8]}.xml"
        }
    )


@app.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str):
    """Delete a job and its associated PDF from the in-memory store."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    jobs.pop(job_id, None)
    _pdf_store.pop(job_id, None)
    return None
