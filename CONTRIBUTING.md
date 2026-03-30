# Contributing

Thanks for your interest in contributing to the Bank Statement Tally Converter.

## Getting started

```bash
git clone <repo-url>
cd bank-statement-tally-converter
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add your GROQ_API_KEY to .env
```

## Running tests

```bash
pytest --tb=short
```

For property-based tests only:
```bash
pytest tests/test_properties.py -v
```

## Adding a new bank parser

1. Create `app/pipeline/parsers/<bank_name>.py`
2. Define column layout constants and a `parse(pdf_path: str) -> list[Transaction]` function
3. Add detection keywords to `BANK_KEYWORDS` in `app/pipeline/graph.py`
4. Add a dispatch branch in `deterministic_extract()` in `app/pipeline/graph.py`
5. Add unit tests in `tests/test_parsers.py` using a mocked pdfplumber table

See `app/pipeline/parsers/hdfc.py` as a reference implementation.

## Code style

- Python 3.11+
- Type hints on all function signatures
- Pydantic v2 for data models
- No hardcoded credentials — use environment variables only

## Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add PNB bank parser
fix: handle empty narration in SBI parser
refactor: extract shared column-finder into utils
docs: update README setup instructions
test: add property test for date normalization edge cases
chore: bump groq SDK to 0.10.0
```

## Pull requests

- Keep PRs focused on a single change
- Include tests for new parsers or bug fixes
- Update `README.md` if you add a new supported bank
