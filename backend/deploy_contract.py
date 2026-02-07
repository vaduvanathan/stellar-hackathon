#!/usr/bin/env python3
"""
Deploy the inheritance contract to Soroban Testnet using the Python SDK.
Reads the secret key from .env (STELLAR_SECRET_KEY) so you never type it in the terminal.

Usage:
  1. Copy .env.example to .env in this directory.
  2. Add one line to .env:  STELLAR_SECRET_KEY=SDZ...your_secret_key
  3. Build the contract first:  cd ../walletsurance && stellar contract build
  4. Run:  python deploy_contract.py

The script prints the new CONTRACT_ID to set in your backend.
"""
import os
import sys
from pathlib import Path

# Load .env before importing config (so STELLAR_SECRET_KEY is set)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from stellar_sdk import Keypair, Network
from stellar_sdk.contract import ContractClient
from stellar_sdk.soroban_server import SorobanServer

# Path to built WASM (from backend dir)
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
WASM_PATH = REPO_ROOT / "walletsurance" / "target" / "wasm32v1-none" / "release" / "inheritance.wasm"

RPC_URL = os.environ.get("SOROBAN_RPC_URL", "https://soroban-testnet.stellar.org")
NETWORK_PASSPHRASE = os.environ.get("NETWORK_PASSPHRASE", Network.TESTNET_NETWORK_PASSPHRASE)


def main() -> None:
    secret = os.environ.get("STELLAR_SECRET_KEY", "").strip()
    if not secret:
        print("ERROR: Set STELLAR_SECRET_KEY in .env (copy from .env.example and add your secret key).", file=sys.stderr)
        sys.exit(1)

    if not WASM_PATH.exists():
        print(f"ERROR: WASM not found at {WASM_PATH}", file=sys.stderr)
        print("Run: cd walletsurance && stellar contract build", file=sys.stderr)
        sys.exit(1)

    try:
        keypair = Keypair.from_secret(secret)
    except Exception as e:
        print(f"ERROR: Invalid secret key: {e}", file=sys.stderr)
        sys.exit(1)

    server = SorobanServer(RPC_URL)
    print("Uploading WASM...")
    wasm_id = ContractClient.upload_contract_wasm(
        contract=str(WASM_PATH),
        source=keypair.public_key,
        signer=keypair,
        soroban_server=server,
        network_passphrase=NETWORK_PASSPHRASE,
        submit_timeout=60,
    )
    print("Creating contract instance...")
    contract_id = ContractClient.create_contract(
        wasm_id=wasm_id,
        source=keypair.public_key,
        signer=keypair,
        soroban_server=server,
        network_passphrase=NETWORK_PASSPHRASE,
        constructor_args=None,
        submit_timeout=60,
    )
    print("")
    print("Deployed contract ID:")
    print(contract_id)
    print("")
    print("Set in your environment or .env:")
    print(f"  CONTRACT_ID={contract_id}")


if __name__ == "__main__":
    main()
