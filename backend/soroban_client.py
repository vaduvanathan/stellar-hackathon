"""
Soroban RPC client for Walletsurance inheritance contract.
Uses stellar_sdk ContractClient to simulate view calls (can_claim, beneficiary).
"""
import os
from typing import Any

from stellar_sdk import Network, scval
from stellar_sdk.contract import ContractClient
from stellar_sdk.exceptions import BadResponseError, SorobanRpcErrorResponse

from config import CONTRACT_ID, NETWORK_PASSPHRASE, SOROBAN_RPC_URL


def _client() -> ContractClient | None:
    if not CONTRACT_ID:
        return None
    return ContractClient(
        contract_id=CONTRACT_ID,
        rpc_url=SOROBAN_RPC_URL,
        network_passphrase=NETWORK_PASSPHRASE,
    )


def get_contract_status() -> dict[str, Any] | None:
    """
    Call contract views can_claim and beneficiary via simulation.
    Returns None if CONTRACT_ID or RPC is not configured or on RPC error.
    """
    client = _client()
    if not client:
        return None

    try:
        # can_claim() -> bool
        can_claim_tx = client.invoke(
            "can_claim",
            parameters=None,
            simulate=True,
        )
        can_claim_val = can_claim_tx.result()
        can_claim = bool(scval.to_native(can_claim_val)) if can_claim_val else False

        # beneficiary() -> Address (may error if vault empty)
        beneficiary_address: str | None = None
        try:
            ben_tx = client.invoke("beneficiary", parameters=None, simulate=True)
            ben_val = ben_tx.result()
            if ben_val:
                addr = scval.from_address(ben_val)
                beneficiary_address = addr.address if addr else None
        except Exception:
            pass

        return {
            "can_claim": can_claim,
            "beneficiary_address": beneficiary_address,
            "contract_id": CONTRACT_ID,
        }
    except (SorobanRpcErrorResponse, BadResponseError, Exception):
        return None


def get_network_info() -> dict[str, Any]:
    """Return RPC and network config (no secrets)."""
    return {
        "rpc_configured": bool(SOROBAN_RPC_URL),
        "contract_id_configured": bool(CONTRACT_ID),
        "network_passphrase": NETWORK_PASSPHRASE[:20] + "..." if NETWORK_PASSPHRASE else None,
    }
