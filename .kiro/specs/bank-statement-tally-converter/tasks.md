# Implementation Plan: Bank Statement Tally Converter

## Overview

Incremental implementation of the FastAPI + LangGraph + Groq + Streamlit pipeline. Each task builds on the previous, ending with a fully wired application. All code is Python; tests use pytest + Hypothesis.

## Tasks

- [x] 1. Project scaffolding and configuration
  - Create the directory structure: `app/`, `app/pipeline/`, `app/pipeline/parsers/`, `frontend/`, `tests/`, `tests/fixtures/`
  - Create `requirements.txt` with: fastapi, uvicorn, pydantic, pdfplumber, langgraph, groq, streamlit, python-dotenv, hypothesis, pytest, httpx
  - Create `.env.example` with `GROQ_API_KEY=your_key_here` and a description comment
  - Create `.gitignore` excluding `.env`, `__pycache__`, `*.pyc`, `.venv`, `*.pdf`, `*.xml` output files
  - Create `README.md` with setup instructions (clone, create venv, pip install, copy .env.example, run uvicorn and streamlit)
  - Create `app/config.py` that reads `GROQ_API_KEY` from env via `python-dotenv`; raise a `ConfigurationError` with a descriptive message and `sys.exit(1)` if missing
  - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 2. Data models
  - [x] 2.1 Implement Pydantic v2 models in `app/models.py`
    - Define `JobStatus` and `VoucherType` enums
    - Define `Transaction` with all fields and the `must_be_non_negative` validator for `withdrawal`, `deposit`, `closing_balance`
    - Define `ProcessingJob` and `TallyVoucher` models
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  - [x]* 2.2 Write unit tests for `Transaction` model in `tests/test_models.py`
    - Test that negative `withdrawal`, `deposit`, `closing_balance` raise `ValidationError`
    - Test that zero amounts are accepted and `parse_error` defaults to `False`
    - _Requirements: 5.3, 11.4_
  - [x]* 2.3 Write property test for negative amount rejection
    - **Property 7: Negative amounts are always rejected by the data model**
    - **Validates: Requirements 5.3**
    - Use `st.decimals(max_value=Decimal("-0.01"))` for each amount field
    - _tests/test_properties.py_

- [x] 3. XML generator
  - [x] 3.1 Implement `app/xml_generator.py`
    - Implement `generate_tally_xml(transactions, bank_ledger_name) -> str` using `xml.etree.ElementTree`
    - Build `ENVELOPE > HEADER > BODY > IMPORTDATA > REQUESTDATA > TALLYMESSAGE > VOUCHER` hierarchy
    - Determine voucher type per the design table (Payment / Receipt / Contra)
    - Emit two `LEDGERENTRIES.LIST` elements per voucher with correct `ISDEEMEDPOSITIVE` values
    - Implement `parse_tally_xml(xml_str) -> list[TallyVoucher]` helper for round-trip testing
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  - [x]* 3.2 Write unit tests for XML generator in `tests/test_xml_generator.py`
    - One test per voucher type (Receipt, Payment, Contra) verifying element names, ledger assignments, `ISDEEMEDPOSITIVE`
    - One test verifying the full `ENVELOPE > BODY > IMPORTDATA > REQUESTDATA > TALLYMESSAGE > VOUCHER` hierarchy
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 11.1, 11.2_
  - [x]* 3.3 Write property test for voucher type selection
    - **Property 10: Voucher type is determined correctly by transaction amounts**
    - **Validates: Requirements 8.2, 8.3, 8.4**
    - Use `st.decimals(min_value=0)` pairs for withdrawal/deposit
    - _tests/test_properties.py_
  - [x]* 3.4 Write property test for XML hierarchy
    - **Property 11: Generated XML conforms to Tally TDL hierarchy**
    - **Validates: Requirements 8.1, 8.5**
    - Use `st.lists(transaction_strategy(), min_size=1)`
    - _tests/test_properties.py_
  - [x]* 3.5 Write property test for XML round-trip
    - **Property 12: XML generation round-trip**
    - **Validates: Requirements 8.8, 11.5**
    - Use `st.lists(transaction_strategy(), min_size=1)`
    - Assert `generate_tally_xml(parse_tally_xml(xml), bank) == xml`
    - _tests/test_properties.py_

- [ ] 4. Checkpoint - core models and XML
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Bank statement parsers
  - [x] 5.1 Implement `app/pipeline/parsers/hdfc.py`
    - Define HDFC column layout constants
    - Implement `parse(pdf_path) -> list[Transaction]` using pdfplumber
    - Normalize dates to `YYYYMMDD` and strip commas/currency symbols from numeric fields
    - Set `withdrawal` or `deposit` to `0.00` when the cell is empty
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 9.1_
  - [x] 5.2 Implement `app/pipeline/parsers/icici.py`
    - Same structure as HDFC parser with ICICI-specific column layout
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 9.2_
  - [x] 5.3 Implement `app/pipeline/parsers/sbi.py`
    - Same structure as HDFC parser with SBI-specific column layout
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 9.3_
  - [x]* 5.4 Write unit tests for parsers in `tests/test_parsers.py`
    - One test per bank using fixture PDF files in `tests/fixtures/`
    - Verify field extraction, date normalization, and amount parsing
    - _Requirements: 9.1, 9.2, 9.3, 11.3_
  - [x]* 5.5 Write property test for date normalization
    - **Property 4: Date normalization is consistent**
    - **Validates: Requirements 2.3**
    - Use `st.dates()` formatted as `DD/MM/YYYY`, `DD-MM-YYYY`, `DD MMM YYYY`
    - Assert output matches `YYYYMMDD` pattern
    - _tests/test_properties.py_
  - [x]* 5.6 Write property test for numeric field cleaning
    - **Property 5: Numeric field cleaning preserves value**
    - **Validates: Requirements 2.4**
    - Use `st.decimals(min_value=0)` formatted with commas and currency symbols
    - Assert parsed `Decimal` equals the original value
    - _tests/test_properties.py_

- [x] 6. LangGraph extraction pipeline
  - [x] 6.1 Implement `app/pipeline/graph.py`
    - Define `PipelineState` TypedDict with `pdf_path`, `bank_type`, `transactions`, `error` fields
    - Implement `classify_document` node: read PDF text with pdfplumber, detect HDFC/ICICI/SBI by header keywords, set `bank_type`
    - Implement `deterministic_extract` node: dispatch to the correct bank parser based on `bank_type`; escalate pages with no rows to `fallback_llm_extract`
    - Implement `fallback_llm_extract` node: send page text to Groq (`meta-llama/llama-4-scout-17b-16e-instruct`) with a structured JSON prompt; parse response into `Transaction` objects; set `parse_error=True` for unparseable dates
    - Wire nodes with conditional edges: `classify_document` routes to `deterministic_extract` (known bank) or `fallback_llm_extract` (unknown)
    - Compile and expose `pipeline` as the runnable graph
    - _Requirements: 2.6, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 4.5, 9.4, 9.5_
  - [x]* 6.2 Write property test for LLM-extracted transactions with invalid dates
    - **Property 6: LLM-extracted transactions with invalid dates are flagged**
    - **Validates: Requirements 3.3**
    - Simulate LLM returning transactions with unparseable date strings; assert `parse_error == True`
    - _tests/test_properties.py_
  - [x]* 6.3 Write property test for extracted transactions having required fields
    - **Property 3: Extracted transactions always contain required fields**
    - **Validates: Requirements 2.2, 2.5**
    - Use `st.lists(transaction_strategy())` to verify all fields are present and non-negative
    - _tests/test_properties.py_

- [x] 7. Groq ledger classifier
  - [x] 7.1 Implement `app/classifier.py`
    - Implement `classify_transactions(transactions: list[Transaction]) -> list[Transaction]`
    - Use `from groq import Groq` with model `meta-llama/llama-4-scout-17b-16e-instruct`
    - Build prompt with narration + hardcoded list of ~30 common Tally ledger names
    - Parse LLM response and populate `assigned_ledger` on each transaction
    - _Requirements: 6.1, 6.2_
  - [x]* 7.2 Write property test for classification populating all ledger assignments
    - **Property 8: Classification populates all ledger assignments**
    - **Validates: Requirements 6.1**
    - Mock the Groq client; assert every transaction in the returned list has a non-empty `assigned_ledger`
    - _tests/test_properties.py_

- [x] 8. FastAPI backend
  - [x] 8.1 Implement `app/main.py` with all endpoints
    - In-memory job store: `jobs: dict[str, ProcessingJob] = {}`
    - `POST /upload`: validate MIME type and PDF header bytes (422 if not PDF, 413 if > 50 MB), store file, return `job_id` with 202
    - `POST /process/{job_id}`: run LangGraph pipeline then classifier; update job status through `extracting` -> `classifying` -> `ready`/`failed`
    - `GET /transactions/{job_id}`: return transactions list (404 if not found)
    - `PATCH /transactions/{job_id}/{tx_id}`: update `assigned_ledger`; return 422 if empty/null; set job to `ready` when all ledgers assigned
    - `GET /export/{job_id}`: return 409 if job not `ready`; call `generate_tally_xml` and return as downloadable XML attachment
    - `GET /health`: return `{"status": "ok"}`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.3, 7.1, 7.2, 7.3, 7.4, 8.6, 8.7_
  - [x]* 8.2 Write unit tests for API in `tests/test_api.py`
    - Test `/upload` rejects non-PDF with 422
    - Test `/upload` rejects files > 50 MB with 413
    - Test `/export` returns 409 for non-ready job
    - Use `httpx.AsyncClient` with FastAPI `TestClient`
    - _Requirements: 1.2, 1.3, 1.4, 8.7, 11.4_
  - [x]* 8.3 Write property test for unique job IDs
    - **Property 1: Valid PDF uploads always produce unique job IDs**
    - **Validates: Requirements 1.5**
    - Upload multiple valid PDFs and assert all returned `job_id` values are distinct
    - _tests/test_properties.py_
  - [x]* 8.4 Write property test for non-PDF rejection
    - **Property 2: Non-PDF files are always rejected**
    - **Validates: Requirements 1.2, 1.3**
    - Use `st.binary()` filtered to exclude valid PDF headers; assert response status is non-2xx
    - _tests/test_properties.py_
  - [x]* 8.5 Write property test for job ready status
    - **Property 9: Job reaches ready status when all ledgers are assigned**
    - **Validates: Requirements 7.4**
    - Construct a job where all transactions have `assigned_ledger` set; assert `status == ready`
    - _tests/test_properties.py_

- [ ] 9. Checkpoint - backend complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Streamlit frontend
  - [x] 10.1 Implement `frontend/app.py`
    - Step 1: File uploader widget -> POST to `/upload` then POST to `/process/{job_id}`; show spinner during processing
    - Step 2: Fetch `GET /transactions/{job_id}`; render editable `st.data_editor` table with a ledger column; PATCH on cell change
    - Step 3: Download XML button -> GET `/export/{job_id}`; offer file download via `st.download_button`
    - Read API base URL from `FASTAPI_URL` env var (default `http://localhost:8000`)
    - _Requirements: 7.1, 7.2_

- [-] 11. Final wiring and integration
  - [-] 11.1 Wire `app/config.py` startup check into `app/main.py` lifespan
    - Call config validation on FastAPI startup so missing env vars exit immediately
    - _Requirements: 10.4_
  - [ ] 11.2 Add `__init__.py` files to all packages and verify all imports resolve
    - Ensure `app/pipeline/parsers/` is a proper package
    - _Requirements: 9.5_

- [ ] 12. Final checkpoint - full integration
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with `@settings(max_examples=100)`
- The `transaction_strategy()` composite strategy (defined in `tests/test_properties.py`) generates valid `Transaction` objects with non-negative amounts, valid YYYYMMDD dates, non-empty narrations, and non-empty assigned ledgers
- Git commit after every top-level task with a detailed commit message
