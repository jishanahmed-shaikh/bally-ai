# 🏦 Bank Statement → Tally XML Converter

> Convert Indian bank statement PDFs into Tally ERP 9 / Tally Prime-compatible XML voucher files — automatically.

**GitHub:** https://github.com/jishanahmed-shaikh/bally-ai

---

## What it does

Upload a PDF bank statement, review AI-suggested ledger assignments in an editable table, and download a ready-to-import Tally XML file.

The pipeline:
1. Detects the bank from the PDF and routes to a deterministic pdfplumber parser
2. Falls back to Groq LLM (Llama 4 Scout) for unrecognised or scanned formats
3. Classifies each transaction narration to a Tally ledger account using Groq
4. Generates standards-compliant Tally XML with double-entry bookkeeping vouchers

---

## Supported Banks

| Bank | Parser |
|---|---|
| HDFC Bank | Deterministic (pdfplumber) |
| ICICI Bank | Deterministic (pdfplumber) |
| State Bank of India (SBI) | Deterministic (pdfplumber) |
| Axis Bank | Deterministic (pdfplumber) |
| Kotak Mahindra Bank | Deterministic (pdfplumber) |
| Punjab National Bank (PNB) | Deterministic (pdfplumber) |
| Bank of Baroda (BOB) | Deterministic (pdfplumber) |
| Any other bank | LLM fallback (Groq Llama 4 Scout) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI 0.111 |
| Extraction pipeline | LangGraph + pdfplumber |
| LLM | Groq `meta-llama/llama-4-scout-17b-16e-instruct` |
| Frontend | Streamlit |
| Data validation | Pydantic v2 |
| XML generation | `xml.etree.ElementTree` |
| Testing | pytest + Hypothesis (property-based) |
| Containerisation | Docker + docker-compose |

---

## Setup

### Prerequisites

- Python 3.11+
- A Groq API key — get one free at https://console.groq.com

### Local setup

```bash
# 1. Clone the repo
git clone https://github.com/jishanahmed-shaikh/bally-ai.git
cd bally-ai

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Open .env and set your GROQ_API_KEY
```

---

## Running

### Local (two terminals)

```bash
# Terminal 1 — FastAPI backend
uvicorn app.main:app --reload
# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs

# Terminal 2 — Streamlit frontend
streamlit run frontend/app.py
# UI available at http://localhost:8501
```

### Docker

```bash
# Build and start both services
docker-compose up --build

# Stop
docker-compose down
```

---

## Usage

1. **Upload** — open `http://localhost:8501`, enter your bank ledger name (e.g. `HDFC Bank`), and upload a PDF bank statement
2. **Review** — inspect the extracted transactions table; correct any AI-suggested ledger assignments inline
3. **Download** — click "Generate & Download Tally XML" to get the import file, then import it into Tally ERP 9 or Tally Prime via `Gateway of Tally → Import Data → Vouchers`

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check — returns version and status |
| `GET` | `/banks` | List all supported bank parsers |
| `GET` | `/ledgers` | List all available Tally ledger names |
| `GET` | `/jobs` | List all in-memory processing jobs |
| `POST` | `/upload` | Upload and validate a PDF (returns `job_id`) |
| `POST` | `/process/{job_id}` | Run extraction + classification pipeline |
| `GET` | `/transactions/{job_id}` | Get transactions with ledger suggestions |
| `PATCH` | `/transactions/{job_id}/{tx_id}` | Update ledger assignment for a transaction |
| `GET` | `/export/{job_id}` | Generate and download Tally XML |
| `DELETE` | `/jobs/{job_id}` | Delete a job and free memory |

Interactive API docs: `http://localhost:8000/docs`

---

## Running Tests

```bash
# All tests
pytest --tb=short

# Unit tests only
pytest tests/test_models.py tests/test_xml_generator.py tests/test_parsers.py tests/test_api.py tests/test_xml_validator.py -v

# Property-based tests (Hypothesis)
pytest tests/test_properties.py -v
```

---

## Project Structure

```
bally-ai/
├── app/
│   ├── __init__.py
│   ├── config.py               # Env var loading, ConfigurationError
│   ├── main.py                 # FastAPI app — all 10 endpoints
│   ├── models.py               # Pydantic v2 models (Transaction, ProcessingJob, TallyVoucher)
│   ├── classifier.py           # Groq ledger classifier (batched, 38 ledger names)
│   ├── xml_generator.py        # Tally XML builder (Payment / Receipt / Contra)
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── graph.py            # LangGraph state machine (classify → extract / fallback)
│   │   └── parsers/
│   │       ├── __init__.py
│   │       ├── utils.py        # normalize_date(), clean_amount()
│   │       ├── hdfc.py         # HDFC Bank parser
│   │       ├── icici.py        # ICICI Bank parser
│   │       ├── sbi.py          # SBI parser
│   │       ├── axis.py         # Axis Bank parser
│   │       ├── kotak.py        # Kotak Mahindra Bank parser
│   │       ├── pnb.py          # Punjab National Bank parser
│   │       └── bob.py          # Bank of Baroda parser
│   └── utils/
│       ├── __init__.py
│       ├── tally_ledgers.py    # Canonical list of 38 Tally ledger names
│       └── xml_validator.py    # Structural validation of generated Tally XML
├── frontend/
│   └── app.py                  # Streamlit 3-step UI
├── tests/
│   ├── __init__.py
│   ├── fixtures/               # Sample PDF fixtures for parser tests
│   ├── test_models.py          # Pydantic model unit tests
│   ├── test_xml_generator.py   # XML generator unit tests
│   ├── test_xml_validator.py   # XML validator unit tests
│   ├── test_parsers.py         # Parser unit tests (mocked pdfplumber)
│   ├── test_api.py             # FastAPI endpoint tests
│   └── test_properties.py      # Hypothesis property-based tests (12 properties)
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI
├── .env.example                # Environment variable template
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Your Groq API key from https://console.groq.com |
| `FASTAPI_URL` | No | Backend URL for Streamlit (default: `http://localhost:8000`) |

Copy `.env.example` to `.env` and fill in your values.

---

## Adding a New Bank Parser

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. In short:

1. Create `app/pipeline/parsers/<bank>.py` with a `parse(pdf_path) -> list[Transaction]` function
2. Add detection keywords to `BANK_KEYWORDS` in `app/pipeline/graph.py`
3. Add a dispatch branch in `deterministic_extract()` in `app/pipeline/graph.py`
4. Add the bank to the `/banks` endpoint in `app/main.py`

---

## License

MIT
