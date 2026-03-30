# Requirements Document

## Introduction

A tool that converts Indian bank statements (PDF and scanned documents) into Tally ERP 9 / Tally Prime-compatible XML for import. The system extracts transactions from bank statement PDFs, normalizes and categorizes them using an AI-powered pipeline, and generates standards-compliant Tally XML with double-entry bookkeeping vouchers.

The MVP uses a FastAPI backend, pdfplumber + LangGraph for extraction, LangChain + LLM for ledger classification, and a Streamlit frontend.

## Glossary

- **System**: The PDF-to-Tally XML converter application as a whole
- **API**: The FastAPI backend service
- **Extractor**: The document parsing component (pdfplumber + LangGraph pipeline)
- **Classifier**: The LangChain-based narration-to-ledger mapping component
- **XML_Generator**: The Tally XML compilation component
- **Transaction**: A single bank statement row containing date, narration, reference number, withdrawal amount, deposit amount, and closing balance
- **Ledger**: A Tally account name (e.g., "Meals & Entertainment", "Bank Account")
- **Voucher**: A Tally XML entry representing a double-entry bookkeeping transaction
- **Narration**: The free-text description field in a bank statement row (e.g., "UPI/Zomato/123456")
- **Tally_XML**: The XML format conforming to the Tally TDL schema used for importing data into Tally ERP 9 and Tally Prime
- **LLM**: Large Language Model (Gemini 1.5 Pro or GPT-4o) used for fallback extraction and classification

---

## Requirements

### Requirement 1: File Upload and Validation

**User Story:** As an accountant, I want to upload a bank statement PDF, so that the system can process it into Tally-compatible data.

#### Acceptance Criteria

1. THE API SHALL expose a `/upload` endpoint that accepts PDF files via multipart form upload.
2. WHEN a file is uploaded, THE API SHALL validate that the file is a PDF by checking the MIME type and file header.
3. WHEN a non-PDF file is uploaded, THE API SHALL return an HTTP 422 response with a descriptive error message.
4. WHEN a PDF exceeding 50 MB is uploaded, THE API SHALL return an HTTP 413 response with a descriptive error message.
5. WHEN a valid PDF is uploaded, THE API SHALL return a unique `job_id` and an HTTP 202 response.

---

### Requirement 2: Bank Statement Parsing — Deterministic Path

**User Story:** As an accountant, I want the system to extract transactions from standard bank statement PDFs, so that I don't have to manually enter data.

#### Acceptance Criteria

1. WHEN a PDF is identified as an HDFC, ICICI, or SBI bank statement, THE Extractor SHALL use pdfplumber to extract tabular transaction data deterministically.
2. THE Extractor SHALL extract the following fields for each transaction row: Date, Narration, Reference_Number, Withdrawal, Deposit, Closing_Balance.
3. WHEN a date value is extracted, THE Extractor SHALL normalize it to the format `YYYYMMDD` as required by Tally.
4. WHEN a numeric field (Withdrawal, Deposit, Closing_Balance) contains commas or currency symbols, THE Extractor SHALL strip them and parse the value as a decimal number.
5. WHEN a transaction row has no Withdrawal value, THE Extractor SHALL set Withdrawal to `0.00`, and similarly for Deposit.
6. WHEN pdfplumber fails to extract any rows from a page, THE Extractor SHALL escalate that page to the LLM fallback path.

---

### Requirement 3: Bank Statement Parsing — LLM Fallback Path

**User Story:** As an accountant, I want scanned or non-standard PDFs to also be processed, so that I can handle all statement formats without manual intervention.

#### Acceptance Criteria

1. WHEN a PDF page cannot be parsed deterministically, THE Extractor SHALL invoke the LLM (Gemini 1.5 Pro or GPT-4o) via the LangGraph `fallback_llm_extract` node to extract transaction data.
2. WHEN the LLM returns extracted data, THE Extractor SHALL validate that each transaction contains at minimum a Date and one of Withdrawal or Deposit before accepting it.
3. IF the LLM returns a transaction with an unparseable date, THEN THE Extractor SHALL mark that transaction with a `parse_error` flag and include it in the response for user review.

---

### Requirement 4: LangGraph Extraction Pipeline

**User Story:** As a developer, I want the extraction logic to be structured as a LangGraph state machine, so that the pipeline is observable, testable, and extensible.

#### Acceptance Criteria

1. THE Extractor SHALL implement a LangGraph state machine with at minimum the following nodes: `classify_document`, `deterministic_extract`, `fallback_llm_extract`.
2. WHEN a document is processed, THE Extractor SHALL first pass it through `classify_document` to identify the bank and statement format before extraction.
3. WHEN `classify_document` identifies a supported bank format (HDFC, ICICI, SBI), THE Extractor SHALL route to `deterministic_extract`.
4. WHEN `classify_document` cannot identify a supported format, THE Extractor SHALL route to `fallback_llm_extract`.
5. THE Extractor SHALL expose the final list of extracted Transaction objects as the pipeline output state.

---

### Requirement 5: Data Models

**User Story:** As a developer, I want well-defined Pydantic data models, so that data flows through the system with type safety and validation.

#### Acceptance Criteria

1. THE System SHALL define a `Transaction` Pydantic model with fields: `date` (str, YYYYMMDD), `narration` (str), `reference_number` (str, optional), `withdrawal` (Decimal), `deposit` (Decimal), `closing_balance` (Decimal), `assigned_ledger` (str, optional), `parse_error` (bool, default False).
2. THE System SHALL define a `ProcessingJob` Pydantic model with fields: `job_id` (UUID), `status` (enum: pending, extracting, classifying, ready, failed), `transactions` (list of Transaction), `created_at` (datetime).
3. WHEN a `Transaction` is created with a negative Withdrawal or Deposit value, THE System SHALL raise a validation error.
4. THE System SHALL define a `TallyVoucher` Pydantic model representing a double-entry voucher with fields: `voucher_type` (enum: Receipt, Payment, Contra), `date` (str), `narration` (str), `debit_ledger` (str), `credit_ledger` (str), `amount` (Decimal).

---

### Requirement 6: Ledger Classification

**User Story:** As an accountant, I want bank narrations automatically mapped to Tally ledger accounts, so that I save time on manual categorization.

#### Acceptance Criteria

1. WHEN a Transaction has no `assigned_ledger`, THE Classifier SHALL use a LangChain pipeline with an LLM to suggest a Tally ledger name based on the Narration field.
2. THE Classifier SHALL provide the LLM with a predefined list of common Tally ledger names as context for classification.
3. THE System SHALL expose a `/process` endpoint that accepts a `job_id` and triggers the classification step, returning the updated list of Transactions with `assigned_ledger` populated.

---

### Requirement 7: User Review Before XML Generation

**User Story:** As an accountant, I want to review and correct AI-suggested ledger assignments before generating XML, so that the final output is accurate.

#### Acceptance Criteria

1. THE API SHALL expose a `/transactions/{job_id}` endpoint that returns all Transactions for a job, including `assigned_ledger` suggestions and `parse_error` flags.
2. THE API SHALL expose a `PATCH /transactions/{job_id}/{transaction_id}` endpoint that allows updating the `assigned_ledger` field for a specific Transaction.
3. WHEN a PATCH request is received with an empty or null `assigned_ledger`, THE API SHALL return an HTTP 422 response.
4. WHEN all Transactions for a job have a non-empty `assigned_ledger`, THE System SHALL mark the job status as `ready`.

---

### Requirement 8: Tally XML Generation

**User Story:** As an accountant, I want to export transactions as a Tally-compatible XML file, so that I can import them directly into Tally ERP 9 or Tally Prime.

#### Acceptance Criteria

1. THE XML_Generator SHALL produce XML conforming to the Tally TDL hierarchy: `ENVELOPE > HEADER > BODY > DATA > TALLYMESSAGE > VOUCHER`.
2. WHEN a Transaction has a non-zero Withdrawal, THE XML_Generator SHALL generate a Payment voucher debiting the `assigned_ledger` and crediting the bank ledger.
3. WHEN a Transaction has a non-zero Deposit, THE XML_Generator SHALL generate a Receipt voucher crediting the `assigned_ledger` and debiting the bank ledger.
4. WHEN a Transaction has both non-zero Withdrawal and Deposit (Contra), THE XML_Generator SHALL generate a Contra voucher.
5. THE XML_Generator SHALL include the `LEDGERENTRIES.LIST` element with `ISDEEMEDPOSITIVE` set correctly per Tally's double-entry rules.
6. THE API SHALL expose a `/export/{job_id}` endpoint that triggers XML generation and returns the XML file as a downloadable attachment.
7. WHEN `/export/{job_id}` is called for a job not in `ready` status, THE API SHALL return an HTTP 409 response with a message indicating the job is not ready for export.
8. FOR ALL valid Transaction lists, parsing the generated Tally XML back into voucher records and re-generating XML SHALL produce an identical XML document (round-trip property).

---

### Requirement 9: Multi-Bank Support

**User Story:** As an accountant, I want the system to support HDFC, ICICI, and SBI statement formats, so that I can process statements from the most common Indian banks.

#### Acceptance Criteria

1. THE Extractor SHALL correctly parse HDFC Bank statement PDFs using the HDFC-specific column layout (Date, Narration, Value Date, Reference Number/Cheque Number, Withdrawal, Deposit, Closing Balance).
2. THE Extractor SHALL correctly parse ICICI Bank statement PDFs using the ICICI-specific column layout.
3. THE Extractor SHALL correctly parse SBI Bank statement PDFs using the SBI-specific column layout.
4. WHEN a statement from an unsupported bank is uploaded, THE Extractor SHALL route to the LLM fallback path rather than failing.
5. THE System SHALL be extensible such that adding a new bank parser requires only adding a new node to the LangGraph pipeline and a corresponding layout configuration, without modifying existing nodes.

---

### Requirement 10: Configuration and Environment

**User Story:** As a developer, I want all secrets and configuration managed via environment variables, so that the application is secure and portable.

#### Acceptance Criteria

1. THE System SHALL read the `GROQ_API_KEY` exclusively from environment variables and SHALL NOT hardcode any credentials in source code.
2. THE System SHALL provide a `.env.example` file listing all required environment variables with placeholder values and descriptions.
3. THE System SHALL provide a `.gitignore` file that excludes `.env`, `__pycache__`, `*.pyc`, `.venv`, and generated output files.
4. WHEN a required environment variable is missing at startup, THE System SHALL raise a descriptive `ConfigurationError` and exit with a non-zero status code.

---

### Requirement 11: Testing

**User Story:** As a developer, I want comprehensive automated tests, so that I can confidently refactor and extend the system.

#### Acceptance Criteria

1. THE System SHALL include pytest unit tests for the XML_Generator covering all three voucher types (Receipt, Payment, Contra).
2. THE System SHALL include pytest unit tests validating that generated Tally XML conforms to the required `ENVELOPE > HEADER > BODY > DATA > TALLYMESSAGE > VOUCHER` hierarchy.
3. THE System SHALL include pytest unit tests for the deterministic parsers of each supported bank (HDFC, ICICI, SBI) using sample fixture files.
4. THE System SHALL include pytest unit tests for the `Transaction` Pydantic model validating field constraints (negative amounts, missing required fields).
5. FOR ALL valid Transaction inputs, THE XML_Generator round-trip test SHALL verify that `parse(generate(transactions)) == transactions` (round-trip property).
