# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- Axis Bank statement parser (`app/pipeline/parsers/axis.py`)
- Kotak Mahindra Bank statement parser (`app/pipeline/parsers/kotak.py`)
- Punjab National Bank (PNB) parser (`app/pipeline/parsers/pnb.py`)
- Bank of Baroda (BOB) parser (`app/pipeline/parsers/bob.py`)
- `GET /banks` endpoint listing all supported deterministic parsers
- `GET /ledgers` endpoint returning canonical Tally ledger list
- `GET /jobs` endpoint listing all in-memory processing jobs
- `DELETE /jobs/{job_id}` endpoint for job cleanup
- `app/utils/tally_ledgers.py` — single source of truth for 38 Tally ledger names
- `app/utils/xml_validator.py` — structural validation of generated Tally XML
- XML validation wired into `GET /export/{job_id}` before file is returned
- Dockerfile and docker-compose.yml for containerised deployment
- GitHub Actions CI workflow (`.github/workflows/ci.yml`)
- CONTRIBUTING.md with parser extension guide
- CHANGELOG.md

### Changed
- `app/classifier.py` now imports ledger list from `app/utils/tally_ledgers.py`
- Streamlit frontend fetches ledger list and bank list dynamically from API
- `/banks` endpoint updated to include all 7 supported banks

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
