# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- Axis Bank statement parser (`app/pipeline/parsers/axis.py`)
- Kotak Mahindra Bank statement parser (`app/pipeline/parsers/kotak.py`)
- CONTRIBUTING.md with parser extension guide

---

## [1.0.0] - 2026-03-31

### Added
- FastAPI backend with `/upload`, `/process`, `/transactions`, `/export`, `/health` endpoints
- LangGraph extraction pipeline with `classify_document → deterministic_extract / fallback_llm_extract` nodes
- Deterministic parsers for HDFC, ICICI, SBI bank statement PDFs using pdfplumber
- Groq LLM fallback extraction for unrecognised or scanned PDFs (`meta-llama/llama-4-scout-17b-16e-instruct`)
- Groq LLM ledger classifier mapping narrations to Tally ledger accounts (batches of 20)
- Tally XML generator producing `ENVELOPE > HEADER > BODY > IMPORTDATA > REQUESTDATA > TALLYMESSAGE > VOUCHER` hierarchy
- Support for Payment, Receipt, and Contra voucher types with correct `ISDEEMEDPOSITIVE` values
- Pydantic v2 data models: `Transaction`, `ProcessingJob`, `TallyVoucher`
- Streamlit frontend with 3-step workflow: upload → review → download
- Shared parser utilities: `normalize_date()` and `clean_amount()`
- Pytest unit tests for models, XML generator, parsers, and API endpoints
- Hypothesis property-based tests for all 12 correctness properties
- `.env.example`, `.gitignore`, `README.md`, `pytest.ini`

### Technical details
- In-memory job store (Python dict) — no database required for MVP
- PDF validation via magic bytes (`%PDF`) and MIME type check
- 50 MB file size limit on uploads
- Graceful fallback to `Miscellaneous Expenses` ledger on LLM classification failure
- `ConfigurationError` on startup if `GROQ_API_KEY` is missing
