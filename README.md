# Bank Statement Tally Converter

Convert Indian bank statement PDFs into Tally ERP 9 / Tally Prime-compatible XML voucher files — automatically.

## What it does

Upload a PDF bank statement, review AI-suggested ledger assignments, and download a ready-to-import Tally XML file. The pipeline extracts transactions using deterministic parsers for known banks and falls back to an LLM for unrecognised formats.

**Supported banks (deterministic):** HDFC, ICICI, SBI
**Other banks:** handled via LLM fallback (Groq Llama 4 Scout)

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI |
| Extraction pipeline | LangGraph + pdfplumber |
| LLM | Groq (`meta-llama/llama-4-scout-17b-16e-instruct`) |
| Frontend | Streamlit |
| Data validation | Pydantic v2 |

## Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd bank-statement-tally-converter

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
# Edit .env and add your GROQ_API_KEY
```

Get your Groq API key at https://console.groq.com

## Running

Start the backend and frontend in separate terminals:

```bash
# Terminal 1 — FastAPI backend
uvicorn app.main:app --reload

# Terminal 2 — Streamlit frontend
streamlit run frontend/app.py
```

The API will be available at `http://localhost:8000` and the UI at `http://localhost:8501`.

## Usage flow

1. **Upload** — drag and drop a bank statement PDF in the Streamlit UI
2. **Review** — inspect extracted transactions and correct any ledger assignments in the editable table
3. **Download** — click "Export XML" to download the Tally-compatible XML file, then import it into Tally ERP 9 or Tally Prime

## Project structure

```
bank-statement-tally-converter/
├── app/
│   ├── __init__.py
│   ├── config.py           # Env var loading and ConfigurationError
│   ├── main.py             # FastAPI app and all endpoints
│   ├── models.py           # Pydantic data models
│   ├── classifier.py       # Groq ledger classifier
│   ├── xml_generator.py    # Tally XML builder
│   └── pipeline/
│       ├── __init__.py
│       ├── graph.py        # LangGraph state machine
│       └── parsers/
│           ├── __init__.py
│           ├── hdfc.py
│           ├── icici.py
│           └── sbi.py
├── frontend/
│   └── app.py              # Streamlit UI
├── tests/
│   ├── __init__.py
│   ├── fixtures/           # Sample PDF files for parser tests
│   ├── test_models.py
│   ├── test_xml_generator.py
│   ├── test_parsers.py
│   ├── test_api.py
│   └── test_properties.py  # Hypothesis property-based tests
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```
