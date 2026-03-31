# Contributing to Bally AI

Thanks for your interest. Here's everything you need to get started.

---

## Local Setup

```bash
git clone https://github.com/jishanahmed-shaikh/bally-ai.git
cd bally-ai

python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt

cp .env.example .env
# Add your GROQ_API_KEY to .env
```

---

## Running Tests

```bash
# All tests
pytest --tb=short

# Property-based tests only
pytest tests/test_properties.py -v

# Specific test file
pytest tests/test_xml_generator.py -v
```

---

## Adding a New Bank Parser

This is the most common contribution. Takes about 10 minutes.

### 1. Create the parser file

```bash
# e.g. for Yes Bank
touch app/pipeline/parsers/yesbank.py
```

Use `app/pipeline/parsers/hdfc.py` as a reference. Every parser exposes one function:

```python
def parse(pdf_path: str) -> list[Transaction]:
    ...
```

Define your column layout constants at the top:

```python
YESBANK_COLUMNS = {
    "date": ["date", "txn date"],
    "narration": ["description", "narration", "particulars"],
    "ref_no": ["ref no", "cheque no"],
    "withdrawal": ["debit", "withdrawal", "dr"],
    "deposit": ["credit", "deposit", "cr"],
    "balance": ["balance"],
}
```

Use the shared utilities — don't reimplement them:

```python
from app.pipeline.parsers.utils import normalize_date, clean_amount
```

### 2. Register in the pipeline

In `app/pipeline/graph.py`:

```python
# Add import
from app.pipeline.parsers import hdfc, icici, sbi, axis, kotak, pnb, bob, yesbank

# Add detection keywords
BANK_KEYWORDS = {
    ...
    "yesbank": ["yes bank", "yes bank limited"],
}

# Add dispatch in deterministic_extract()
elif bank_type == "yesbank":
    transactions = yesbank.parse(pdf_path)
```

### 3. Register in the API

In `app/main.py`, add to the `/banks` endpoint:

```python
{"id": "yesbank", "name": "Yes Bank"},
```

### 4. Add tests

In `tests/test_parsers.py`, add a test using a mocked pdfplumber table:

```python
class TestYesBankParser:
    def test_parse_standard_yesbank_table(self):
        table = [
            ["Date", "Description", "Ref No", "Debit", "Credit", "Balance"],
            ["01/01/2024", "UPI/Zomato", "REF001", "500.00", "", "9500.00"],
        ]
        mock_pdf = _make_mock_pdf([table])
        with patch("pdfplumber.open", return_value=mock_pdf):
            transactions = yesbank.parse("dummy.pdf")
        assert len(transactions) == 1
        assert transactions[0].withdrawal == Decimal("500.00")
```

---

## Adding New Tally Ledgers

The canonical ledger list lives in `app/utils/tally_ledgers.py`. Just add to the `TALLY_LEDGERS` list — the classifier and `/ledgers` endpoint pick it up automatically.

---

## Building the Windows Installer

See [BUILD.md](BUILD.md) for the full pipeline.

**Quick version:**
```bash
# Automatic — just tag a release
git tag v1.2.0
git push origin v1.2.0
# GitHub Actions builds BallyAI-Setup.exe and attaches it to the release
```

---

## Project Structure

```
app/
├── main.py              # FastAPI endpoints
├── models.py            # Pydantic models — Transaction, ProcessingJob, TallyVoucher
├── classifier.py        # Groq ledger classifier
├── xml_generator.py     # Tally XML builder
├── pipeline/
│   ├── graph.py         # LangGraph state machine
│   └── parsers/         # One file per bank + shared utils.py
└── utils/
    ├── tally_ledgers.py # Canonical ledger list
    └── xml_validator.py # XML structural validation

frontend/app.py          # Streamlit UI
launcher.py              # Windows .exe launcher with tray icon
build.spec               # PyInstaller config
installer.iss            # Inno Setup installer script
tests/                   # pytest + Hypothesis property-based tests
```

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | When to use |
|---|---|
| `feat:` | New feature or parser |
| `fix:` | Bug fix |
| `refactor:` | Code change with no behaviour change |
| `test:` | Adding or updating tests |
| `docs:` | README, CONTRIBUTING, comments |
| `chore:` | Dependencies, build config, CI |

Examples:
```
feat: add Yes Bank statement parser
fix: handle empty narration in SBI parser
test: add property test for date normalization edge cases
chore: bump groq SDK to 0.10.0
```

---

## Pull Requests

- Keep PRs focused on one thing
- Include tests for new parsers or bug fixes
- Update `README.md` supported banks table if you add a new parser
- Update `CHANGELOG.md` under `[Unreleased]`
