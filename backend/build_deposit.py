"""
Build an unsigned Soroban transaction for the inheritance contract's deposit().
Used by the Lock funds flow: backend builds + prepares, returns XDR for Freighter to sign.
"""
from typing import Any

from config import CONTRACT_ID, DEFAULT_TOKEN_ADDRESS, NETWORK_PASSPHRASE, SOROBAN_RPC_URL


def build_deposit_xdr(
    depositor_public_key: str,
    beneficiary_address: str,
    amount: int,
    timeout_ledgers: int,
    token_address: str | None = None,
) -> tuple[str | None, str | None]:
    """
    Build and prepare (simulate) a deposit() invoke transaction. Do not sign.
    Returns (transaction_xdr_base64, error_message). On success error_message is None.
    """
    token = (token_address or DEFAULT_TOKEN_ADDRESS or "").strip()
    if not CONTRACT_ID:
        return None, "CONTRACT_ID not configured"
    if not token:
        return None, "Token address required (set DEFAULT_TOKEN_ADDRESS or pass token_address)"
    if amount <= 0:
        return None, "Amount must be positive"
    if timeout_ledgers <= 0:
        return None, "timeout_ledgers must be positive"

    try:
        from stellar_sdk import Address, Network, SorobanServer, TransactionBuilder, scval
    except ImportError as e:
        return None, f"stellar_sdk not available: {e}"

    try:
        server = SorobanServer(SOROBAN_RPC_URL)
        source = server.load_account(depositor_public_key)
    except Exception as e:
        return None, f"Failed to load account: {e}"

    try:
        depositor_addr = Address.from_public_key(depositor_public_key)
        beneficiary_addr = Address.from_public_key(beneficiary_address)
        if token.startswith("C") and len(token) == 56:
            token_addr = Address.from_contract_id(token)
        else:
            token_addr = Address.from_public_key(token)
    except Exception as e:
        return None, f"Invalid address: {e}"

    try:
        params = [
            scval.to_address(depositor_addr),
            scval.to_address(token_addr),
            scval.to_int128(amount),
            scval.to_address(beneficiary_addr),
            scval.to_uint32(timeout_ledgers),
        ]
    except Exception as e:
        return None, f"Failed to build params: {e}"

    try:
        tx = (
            TransactionBuilder(source, NETWORK_PASSPHRASE, base_fee=100)
            .set_timeout(300)
            .append_invoke_contract_function_op(
                contract_id=CONTRACT_ID,
                function_name="deposit",
                parameters=params,
            )
            .build()
        )
        tx = server.prepare_transaction(tx)
        return tx.to_xdr(), None
    except Exception as e:
        return None, str(e)


def submit_signed_envelope(signed_envelope_xdr: str) -> tuple[dict[str, Any] | None, str | None]:
    """
    Submit a signed transaction envelope (base64 XDR) to the network.
    Returns (result_dict, error_message). result_dict has hash, status, etc.
    """
    try:
        from stellar_sdk import SorobanServer, TransactionEnvelope
    except ImportError as e:
        return None, f"stellar_sdk not available: {e}"

    try:
        envelope = TransactionEnvelope.from_xdr(signed_envelope_xdr, NETWORK_PASSPHRASE)
    except Exception as e:
        return None, f"Invalid envelope XDR: {e}"

    try:
        server = SorobanServer(SOROBAN_RPC_URL)
        resp = server.send_transaction(envelope)
        return {"hash": resp.hash, "status": resp.status, "result": getattr(resp, "result", None)}, None
    except Exception as e:
        return None, str(e)
