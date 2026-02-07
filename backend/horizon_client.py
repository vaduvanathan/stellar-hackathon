"""
Horizon client: last activity (for inactivity detection) and submit classic transaction.
"""
import requests
from config import HORIZON_URL


def get_account(account_id: str) -> dict | None:
    """
    Return full account from Horizon (balances, subentry_count, sequence, etc.)
    for building sweep transaction on claim page.
    """
    try:
        r = requests.get(f"{HORIZON_URL}/accounts/{account_id}", timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def get_last_activity(account_id: str) -> str | None:
    """
    Return last transaction created_at (ISO) for account, or None.
    GET /accounts/{id}/transactions?order=desc&limit=1
    """
    try:
        r = requests.get(
            f"{HORIZON_URL}/accounts/{account_id}/transactions",
            params={"order": "desc", "limit": 1},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        recs = data.get("_embedded", {}).get("records", [])
        if not recs:
            return None
        return recs[0].get("created_at")
    except Exception:
        return None


def submit_transaction(envelope_xdr: str) -> dict:
    """
    Submit a classic transaction envelope to Horizon. Returns Horizon response dict.
    """
    r = requests.post(
        f"{HORIZON_URL}/transactions",
        data=envelope_xdr,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    try:
        return r.json()
    except Exception:
        return {"error": r.text or str(r.status_code)}
