"""
Onmeta Off-Ramp API client.
Uses mock (built-in or same-app /api/mock-onmeta) when ONMETA_BASE_URL/ONMETA_API_KEY not set.
API ref: https://documenter.getpostman.com/view/20857383/UzXNTwpM
"""
import os
import uuid
import requests
from config import ONMETA_BASE_URL, ONMETA_API_KEY


def create_offramp_order(
    *,
    sell_token_symbol: str = "XLM",
    chain_id: int = 1,
    fiat_currency: str = "inr",
    fiat_amount: float,
    payment_mode: str = "INR_IMPS",
    account_number: str,
    account_name: str,
    ifsc: str,
    metadata: dict | None = None,
) -> dict:
    """
    Create an off-ramp order (crypto → INR bank payout).
    If ONMETA_BASE_URL and ONMETA_API_KEY are set, calls real Onmeta; else returns mock.
    """
    body = {
        "sellTokenSymbol": sell_token_symbol,
        "chainId": chain_id,
        "fiatCurrency": fiat_currency,
        "fiatAmount": fiat_amount,
        "paymentMode": payment_mode,
        "bankDetails": {
            "accountNumber": account_number,
            "accountName": account_name,
            "ifsc": ifsc,
        },
    }
    if metadata:
        body["metaData"] = metadata

    if ONMETA_BASE_URL and ONMETA_API_KEY:
        # Real Onmeta API
        url = f"{ONMETA_BASE_URL.rstrip('/')}/v1/offramp/order"
        resp = requests.post(
            url,
            json=body,
            headers={
                "x-api-key": ONMETA_API_KEY,
                "Authorization": f"Bearer {ONMETA_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # Mock response (same shape as Onmeta for swap-in later)
    return {
        "orderId": f"mock-order-{uuid.uuid4().hex[:12]}",
        "status": "created",
        "fiatAmount": fiat_amount,
        "fiatCurrency": fiat_currency,
        "paymentMode": payment_mode,
        "message": "Mock Onmeta Off-Ramp order (set ONMETA_BASE_URL and ONMETA_API_KEY for real).",
    }
