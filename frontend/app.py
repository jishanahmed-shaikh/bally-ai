"""
Streamlit frontend for the Bank Statement Tally Converter.

Three-step workflow:
  1. Upload PDF → extract transactions with AI ledger suggestions
  2. Review and correct ledger assignments in an editable table
  3. Download Tally XML
"""
import os
import requests
import pandas as pd
import streamlit as st

API_BASE = os.getenv("FASTAPI_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Bank Statement → Tally XML",
    page_icon="🏦",
    layout="wide",
)

st.title("🏦 Bank Statement → Tally XML Converter")
st.caption("Upload your HDFC, ICICI, or SBI bank statement PDF and get a Tally-compatible XML file.")


@st.cache_data(ttl=300)
def fetch_ledgers() -> list[str]:
    """Fetch the canonical ledger list from the API (cached for 5 minutes)."""
    try:
        resp = requests.get(f"{API_BASE}/ledgers", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("ledgers", [])
    except Exception:
        pass
    return []


@st.cache_data(ttl=300)
def fetch_supported_banks() -> list[dict]:
    """Fetch supported banks from the API (cached for 5 minutes)."""
    try:
        resp = requests.get(f"{API_BASE}/banks", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("deterministic", [])
    except Exception:
        pass
    return []

# --- Session state initialization ---
if "job_id" not in st.session_state:
    st.session_state.job_id = None
if "transactions" not in st.session_state:
    st.session_state.transactions = []
if "job_status" not in st.session_state:
    st.session_state.job_status = None
if "processing_done" not in st.session_state:
    st.session_state.processing_done = False


# --- Step 1: Upload ---
st.subheader("Step 1: Upload Bank Statement PDF")

bank_ledger_name = st.text_input(
    "Bank Ledger Name in Tally",
    value="Bank Account",
    help="Enter the exact ledger name for your bank account as it appears in Tally (e.g., 'HDFC Bank', 'SBI Current Account')"
)

uploaded_file = st.file_uploader(
    "Choose a bank statement PDF",
    type=["pdf"],
    help="Supported banks: HDFC, ICICI, SBI, Axis, Kotak, PNB, BOB. Other formats will be processed using AI."
)

if uploaded_file and not st.session_state.processing_done:
    if st.button("Extract Transactions", type="primary"):
        with st.spinner("Uploading PDF..."):
            try:
                upload_resp = requests.post(
                    f"{API_BASE}/upload",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                    timeout=30,
                )
                if upload_resp.status_code != 202:
                    st.error(f"Upload failed: {upload_resp.json().get('detail', 'Unknown error')}")
                    st.stop()

                job_id = upload_resp.json()["job_id"]
                st.session_state.job_id = job_id

            except requests.RequestException as e:
                st.error(f"Could not connect to backend at {API_BASE}. Is the FastAPI server running?\n\nError: {e}")
                st.stop()

        with st.spinner("Extracting transactions and classifying ledgers (this may take a moment)..."):
            try:
                process_resp = requests.post(
                    f"{API_BASE}/process/{job_id}",
                    params={"bank_ledger_name": bank_ledger_name},
                    timeout=120,
                )
                if process_resp.status_code != 200:
                    st.error(f"Processing failed: {process_resp.json().get('detail', 'Unknown error')}")
                    st.stop()

                result = process_resp.json()
                st.success(f"✅ Extracted {result['transaction_count']} transactions!")

            except requests.RequestException as e:
                st.error(f"Processing request failed: {e}")
                st.stop()

        # Fetch transactions
        tx_resp = requests.get(f"{API_BASE}/transactions/{job_id}", timeout=30)
        if tx_resp.status_code == 200:
            data = tx_resp.json()
            st.session_state.transactions = data["transactions"]
            st.session_state.job_status = data["status"]
            st.session_state.processing_done = True
            st.rerun()
        else:
            st.error("Failed to fetch transactions.")


# --- Step 2: Review & Edit ---
if st.session_state.processing_done and st.session_state.transactions:
    st.divider()
    st.subheader("Step 2: Review & Correct Ledger Assignments")

    transactions = st.session_state.transactions

    # Flag parse errors
    parse_errors = [t for t in transactions if t.get("parse_error")]
    if parse_errors:
        st.warning(f"⚠️ {len(parse_errors)} transaction(s) had date parsing issues. Please review them below.")

    # Build DataFrame for editing
    df = pd.DataFrame([
        {
            "id": t["id"],
            "Date": t["date"],
            "Narration": t["narration"],
            "Withdrawal": float(t["withdrawal"]),
            "Deposit": float(t["deposit"]),
            "Balance": float(t["closing_balance"]),
            "Ledger": t.get("assigned_ledger") or "",
            "⚠️": "❌" if t.get("parse_error") else "",
        }
        for t in transactions
    ])

    edited_df = st.data_editor(
        df.drop(columns=["id"]),
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Date": st.column_config.TextColumn("Date", disabled=True),
            "Narration": st.column_config.TextColumn("Narration", disabled=True, width="large"),
            "Withdrawal": st.column_config.NumberColumn("Withdrawal (₹)", disabled=True, format="%.2f"),
            "Deposit": st.column_config.NumberColumn("Deposit (₹)", disabled=True, format="%.2f"),
            "Balance": st.column_config.NumberColumn("Balance (₹)", disabled=True, format="%.2f"),
            "Ledger": st.column_config.TextColumn("Ledger Account", width="medium"),
            "⚠️": st.column_config.TextColumn("", disabled=True, width="small"),
        },
        key="ledger_editor",
    )

    # Detect changes and PATCH
    if st.button("Save Ledger Changes"):
        job_id = st.session_state.job_id
        errors = []
        for i, row in edited_df.iterrows():
            tx_id = df.iloc[i]["id"]
            new_ledger = str(row["Ledger"]).strip()
            old_ledger = str(df.iloc[i]["Ledger"]).strip()

            if new_ledger != old_ledger and new_ledger:
                patch_resp = requests.patch(
                    f"{API_BASE}/transactions/{job_id}/{tx_id}",
                    json={"assigned_ledger": new_ledger},
                    timeout=10,
                )
                if patch_resp.status_code != 200:
                    errors.append(f"Row {i+1}: {patch_resp.json().get('detail', 'error')}")

        if errors:
            st.error("Some updates failed:\n" + "\n".join(errors))
        else:
            st.success("✅ Ledger assignments saved!")
            # Refresh transactions
            tx_resp = requests.get(f"{API_BASE}/transactions/{job_id}", timeout=30)
            if tx_resp.status_code == 200:
                data = tx_resp.json()
                st.session_state.transactions = data["transactions"]
                st.session_state.job_status = data["status"]
                st.rerun()


# --- Step 3: Download XML ---
if st.session_state.job_status == "ready":
    st.divider()
    st.subheader("Step 3: Download Tally XML")
    st.success("✅ All ledger assignments are complete. Your Tally XML is ready!")

    job_id = st.session_state.job_id

    if st.button("Generate & Download Tally XML", type="primary"):
        with st.spinner("Generating XML..."):
            export_resp = requests.get(f"{API_BASE}/export/{job_id}", timeout=30)
            if export_resp.status_code == 200:
                st.download_button(
                    label="⬇️ Download tally_import.xml",
                    data=export_resp.content,
                    file_name=f"tally_import_{job_id[:8]}.xml",
                    mime="application/xml",
                )
            else:
                st.error(f"Export failed: {export_resp.json().get('detail', 'Unknown error')}")

# --- Reset button ---
if st.session_state.processing_done:
    st.divider()
    if st.button("🔄 Start Over (Upload New Statement)"):
        for key in ["job_id", "transactions", "job_status", "processing_done"]:
            st.session_state[key] = None if key != "transactions" else []
        st.session_state.processing_done = False
        st.rerun()
