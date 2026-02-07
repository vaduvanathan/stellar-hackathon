"""Walletsurance backend config from environment."""
import os

SOROBAN_RPC_URL = os.environ.get(
    "SOROBAN_RPC_URL",
    "https://soroban-testnet.stellar.org",
)
NETWORK_PASSPHRASE = os.environ.get(
    "NETWORK_PASSPHRASE",
    "Test SDF Network ; September 2015",
)
# Deployed inheritance contract ID (set after deploy)
CONTRACT_ID = os.environ.get("CONTRACT_ID", "").strip()
