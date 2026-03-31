"""
Ledger classifier using Groq LLM.

Maps bank transaction narrations to Tally ledger account names.
Uses meta-llama/llama-4-scout-17b-16e-instruct via the Groq SDK.
"""
import json
import os
from groq import Groq
from app.models import Transaction
from app.utils.tally_ledgers import TALLY_LEDGERS, LEDGER_LIST_STR


def classify_transactions(transactions: list[Transaction]) -> list[Transaction]:
    """
    Classify each transaction's narration to a Tally ledger name using Groq LLM.

    Processes transactions in batches of 20 to minimize API calls.
    Returns the same list with assigned_ledger populated on each transaction.
    """
    if not transactions:
        return transactions

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    # Process in batches of 20
    batch_size = 20
    results = list(transactions)

    for i in range(0, len(transactions), batch_size):
        batch = transactions[i:i + batch_size]

        # Build narration list for this batch
        narrations_json = json.dumps([
            {"index": j, "narration": t.narration}
            for j, t in enumerate(batch)
        ])

        prompt = f"""You are an accounting assistant. Map each bank transaction narration to the most appropriate Tally ledger account.

Available Tally ledgers:
{LEDGER_LIST_STR}

Transactions to classify:
{narrations_json}

Return a JSON array with the same number of items, each having:
- index: the original index number
- ledger: the most appropriate ledger name from the list above

If none of the ledgers fit, use "Miscellaneous Expenses".
Return ONLY the JSON array, no other text."""

        try:
            completion = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
            )

            response_text = completion.choices[0].message.content.strip()

            # Extract JSON from response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            classifications = json.loads(response_text)

            for item in classifications:
                idx = item.get("index", 0)
                ledger = item.get("ledger", "Miscellaneous Expenses").strip()
                if 0 <= idx < len(batch):
                    # Update the transaction in results
                    global_idx = i + idx
                    results[global_idx] = results[global_idx].model_copy(
                        update={"assigned_ledger": ledger or "Miscellaneous Expenses"}
                    )

        except Exception:
            # On failure, assign "Miscellaneous Expenses" to all in batch
            for j in range(len(batch)):
                global_idx = i + j
                if not results[global_idx].assigned_ledger:
                    results[global_idx] = results[global_idx].model_copy(
                        update={"assigned_ledger": "Miscellaneous Expenses"}
                    )

    # Ensure every transaction has an assigned_ledger
    for idx, t in enumerate(results):
        if not t.assigned_ledger:
            results[idx] = t.model_copy(update={"assigned_ledger": "Miscellaneous Expenses"})

    return results
