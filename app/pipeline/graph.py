"""
LangGraph extraction pipeline for bank statement PDFs.

State machine:
  classify_document → deterministic_extract (known bank)
                    → fallback_llm_extract (unknown bank)
"""
import json
import os
import pdfplumber
from typing import TypedDict, Optional, Literal
from langgraph.graph import StateGraph, END
from groq import Groq
from app.models import Transaction
from app.pipeline.parsers.utils import normalize_date, clean_amount
from app.pipeline.parsers import hdfc, icici, sbi, axis, kotak, pnb, bob


class PipelineState(TypedDict):
    pdf_path: str
    bank_type: Optional[str]  # "hdfc", "icici", "sbi", "axis", "kotak", "pnb", "bob", or None
    transactions: list[Transaction]
    error: Optional[str]


# Bank detection keywords
BANK_KEYWORDS = {
    "hdfc": ["hdfc bank", "hdfc", "withdrawal amt.", "deposit amt."],
    "icici": ["icici bank", "icici", "transaction remarks", "withdrawal amount (inr)"],
    "sbi": ["state bank of india", "sbi", "txn date"],
    "axis": ["axis bank", "axis", "transaction details", "chq/ref number"],
    "kotak": ["kotak mahindra bank", "kotak bank", "kotak", "811"],
    "pnb": ["punjab national bank", "pnb"],
    "bob": ["bank of baroda", "bob", "baroda"],
}


def _extract_pdf_text(pdf_path: str) -> str:
    """Extract all text from a PDF for bank classification."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:3]:  # Check first 3 pages
                page_text = page.extract_text() or ""
                text += page_text.lower()
    except Exception:
        pass
    return text


def classify_document(state: PipelineState) -> PipelineState:
    """Classify the PDF to identify the bank type."""
    text = _extract_pdf_text(state["pdf_path"])
    bank_type = None

    for bank, keywords in BANK_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            bank_type = bank
            break

    return {**state, "bank_type": bank_type}


def deterministic_extract(state: PipelineState) -> PipelineState:
    """Extract transactions using the bank-specific deterministic parser."""
    bank_type = state["bank_type"]
    pdf_path = state["pdf_path"]

    try:
        if bank_type == "hdfc":
            transactions = hdfc.parse(pdf_path)
        elif bank_type == "icici":
            transactions = icici.parse(pdf_path)
        elif bank_type == "sbi":
            transactions = sbi.parse(pdf_path)
        elif bank_type == "axis":
            transactions = axis.parse(pdf_path)
        elif bank_type == "kotak":
            transactions = kotak.parse(pdf_path)
        elif bank_type == "pnb":
            transactions = pnb.parse(pdf_path)
        elif bank_type == "bob":
            transactions = bob.parse(pdf_path)
        else:
            transactions = []

        if not transactions:
            # No rows extracted, fall through to LLM
            return {**state, "bank_type": None, "transactions": []}

        return {**state, "transactions": transactions}
    except Exception as e:
        return {**state, "error": str(e), "transactions": []}


def fallback_llm_extract(state: PipelineState) -> PipelineState:
    """Extract transactions using Groq LLM for unstructured/unknown PDFs."""
    pdf_path = state["pdf_path"]
    transactions = []

    try:
        # Extract raw text from PDF
        pages_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(text)

        if not pages_text:
            return {**state, "error": "No text could be extracted from PDF", "transactions": []}

        full_text = "\n\n".join(pages_text)

        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

        prompt = f"""You are a bank statement parser. Extract all transactions from the following bank statement text.

Return a JSON array where each transaction has these exact fields:
- date: string in DD/MM/YYYY format
- narration: string (transaction description)
- reference_number: string or null
- withdrawal: number (0 if not a debit)
- deposit: number (0 if not a credit)
- closing_balance: number

Return ONLY the JSON array, no other text.

Bank statement text:
{full_text[:8000]}"""

        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4096,
            top_p=1,
            stream=False,
        )

        response_text = completion.choices[0].message.content.strip()

        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        raw_transactions = json.loads(response_text)

        for raw in raw_transactions:
            date_str = str(raw.get("date", "")).strip()
            narration = str(raw.get("narration", "")).strip()

            if not narration:
                continue

            normalized_date = normalize_date(date_str)
            parse_error = normalized_date is None

            if parse_error:
                normalized_date = "00000000"  # placeholder

            try:
                t = Transaction(
                    date=normalized_date,
                    narration=narration,
                    reference_number=str(raw.get("reference_number") or "").strip() or None,
                    withdrawal=clean_amount(str(raw.get("withdrawal", 0))),
                    deposit=clean_amount(str(raw.get("deposit", 0))),
                    closing_balance=clean_amount(str(raw.get("closing_balance", 0))),
                    parse_error=parse_error,
                )
                transactions.append(t)
            except Exception:
                continue

    except Exception as e:
        return {**state, "error": f"LLM extraction failed: {str(e)}", "transactions": []}

    return {**state, "transactions": transactions}


def _route_after_classify(state: PipelineState) -> Literal["deterministic_extract", "fallback_llm_extract"]:
    """Route to deterministic or LLM extraction based on bank_type."""
    if state.get("bank_type") in ("hdfc", "icici", "sbi"):
        return "deterministic_extract"
    return "fallback_llm_extract"


def _route_after_deterministic(state: PipelineState) -> Literal["fallback_llm_extract", "__end__"]:
    """If deterministic extraction returned no transactions, fall back to LLM."""
    if not state.get("transactions") and not state.get("error"):
        return "fallback_llm_extract"
    return "__end__"


# Build the LangGraph state machine
_builder = StateGraph(PipelineState)
_builder.add_node("classify_document", classify_document)
_builder.add_node("deterministic_extract", deterministic_extract)
_builder.add_node("fallback_llm_extract", fallback_llm_extract)

_builder.set_entry_point("classify_document")
_builder.add_conditional_edges("classify_document", _route_after_classify)
_builder.add_conditional_edges("deterministic_extract", _route_after_deterministic, {
    "fallback_llm_extract": "fallback_llm_extract",
    "__end__": END,
})
_builder.add_edge("fallback_llm_extract", END)

pipeline = _builder.compile()


def run_pipeline(pdf_path: str) -> PipelineState:
    """Run the extraction pipeline on a PDF file."""
    initial_state: PipelineState = {
        "pdf_path": pdf_path,
        "bank_type": None,
        "transactions": [],
        "error": None,
    }
    return pipeline.invoke(initial_state)
