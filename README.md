# 🏦 Bally AI — Bank Statement → Tally XML Converter

> Convert Indian bank statement PDFs into Tally ERP 9 / Tally Prime-compatible XML voucher files — automatically.

**GitHub:** https://github.com/jishanahmed-shaikh/bally-ai

---

## Download (Windows)

> The easiest way to use Bally AI — no Python, no terminal, no setup.

1. Go to [Releases](https://github.com/jishanahmed-shaikh/bally-ai/releases/latest)
2. Download `BallyAI-Setup.exe`
3. Run the installer → Next → Next → Finish
4. On first launch, enter your free [Groq API key](https://console.groq.com)
5. Your browser opens automatically — start converting

The installer is self-contained (~150-250MB). No Python or dependencies needed.

---

## What it does

Upload a PDF bank statement → AI extracts all transactions → suggests Tally ledger accounts → you review and correct in an editable table → download a ready-to-import Tally XML file.

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
| Windows installer | PyInstaller + Inno Setup |

---

## Running Locally (Developers)

### Prerequisites

- Python 3.11+
- A free Groq API key from https://console.groq.com

### Setup

```bash
# Clone
git clone https://github.com/jishanahmed-shaikh/bally-ai.git
cd bally-ai

# Virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your_key_here
```

### Run

```bash
# Terminal 1 — FastAPI backend
uvicorn app.main:app --reload
# API at http://localhost:8000
# Docs at http://localhost:8000/docs

# Terminal 2 — Streamlit frontend
streamlit run frontend/app.py
# UI at http://localhost:8501
```

### Docker

```bash
# Copy and fill in your API key first
cp .env.example .env

docker-compose up --build
# API at http://localhost:8000
# UI  at http://localhost:8501
```

---

## Building the Windows Installer

### Automatic (recommended) — GitHub Release

Push a version tag and the installer is built and published automatically:

```bash
git tag v1.1.0
git push origin v1.1.0
```

GitHub Actions (`.github/workflows/release.yml`) will:
- Build the PyInstaller bundle on `windows-latest`
- Download and bundle Poppler binaries automatically
- Compile the Inno Setup installer
- Attach `BallyAI-Setup.exe` to the GitHub Release

The release will appear at:
`https://github.com/jishanahmed-shaikh/bally-ai/releases`

### Manual (local build)

```bash
# Install build tools
pip install pyinstaller pystray pillow

# Download Poppler for Windows from:
# https://github.com/oschwartz10612/poppler-windows/releases
# Then set the path:
$env:POPPLER_PATH = "C:\tools\poppler\bin"   # PowerShell
# or
set POPPLER_PATH=C:\tools\poppler\bin         # CMD

# Build PyInstaller bundle
pyinstaller build.spec --noconfirm

# Install Inno Setup 6 from https://jrsoftware.org/isinfo.php
# Then compile the installer:
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

# Output: Output/BallyAI-Setup.exe
```

See [BUILD.md](BUILD.md) for full details.

---

## How the API Key Works (End Users)

- First launch shows a dialog asking for the Groq API key
- Key is saved to `%APPDATA%\bally-ai\config.json` on their machine
- Never shared — goes directly to Groq's API only
- To change: right-click the system tray icon → **Change API Key**
- To reset: delete `%APPDATA%\bally-ai\config.json` and relaunch

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/banks` | List supported bank parsers |
| `GET` | `/ledgers` | List available Tally ledger names |
| `GET` | `/jobs` | List all processing jobs |
| `POST` | `/upload` | Upload and validate a PDF |
| `POST` | `/process/{job_id}` | Run extraction + classification |
| `GET` | `/transactions/{job_id}` | Get transactions with ledger suggestions |
| `PATCH` | `/transactions/{job_id}/{tx_id}` | Update a ledger assignment |
| `GET` | `/export/{job_id}` | Download Tally XML |
| `DELETE` | `/jobs/{job_id}` | Delete a job |

Interactive docs: `http://localhost:8000/docs`

---

## Running Tests

```bash
pytest --tb=short
```

---

## Project Structure

```
bally-ai/
├── app/
│   ├── config.py               # Env var loading, ConfigurationError
│   ├── main.py                 # FastAPI app — all 10 endpoints
│   ├── models.py               # Pydantic v2 models
│   ├── classifier.py           # Groq ledger classifier
│   ├── xml_generator.py        # Tally XML builder
│   ├── pipeline/
│   │   ├── graph.py            # LangGraph state machine
│   │   └── parsers/
│   │       ├── utils.py        # normalize_date(), clean_amount()
│   │       ├── hdfc.py
│   │       ├── icici.py
│   │       ├── sbi.py
│   │       ├── axis.py
│   │       ├── kotak.py
│   │       ├── pnb.py
│   │       └── bob.py
│   └── utils/
│       ├── tally_ledgers.py    # 38 canonical Tally ledger names
│       └── xml_validator.py    # Structural XML validation
├── frontend/
│   └── app.py                  # Streamlit 3-step UI
├── tests/                      # pytest + Hypothesis tests
├── .github/
│   └── workflows/
│       ├── ci.yml              # Run tests on every push
│       └── release.yml         # Build installer on version tags
├── launcher.py                 # Windows app launcher (tray icon)
├── build.spec                  # PyInstaller config
├── installer.iss               # Inno Setup installer script
├── Dockerfile
├── Dockerfile.frontend
├── docker-compose.yml
├── BUILD.md                    # Full build instructions
├── CONTRIBUTING.md
├── CHANGELOG.md
└── requirements.txt
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Free key from https://console.groq.com |
| `FASTAPI_URL` | No | Backend URL for Streamlit (default: `http://localhost:8000`) |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — adding a new bank parser takes about 10 minutes.

---

## License

MIT
