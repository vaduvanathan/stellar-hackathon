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
# Token contract address for "Lock funds" (e.g. native XLM on testnet). Required for deposit.
DEFAULT_TOKEN_ADDRESS = os.environ.get("DEFAULT_TOKEN_ADDRESS", "").strip()

# Onmeta Off-Ramp (https://documenter.getpostman.com/view/20857383/UzXNTwpM)
# Leave empty to use built-in mock. Set to https://api.onmeta.in (or staging) for real.
ONMETA_BASE_URL = os.environ.get("ONMETA_BASE_URL", "").strip()
ONMETA_API_KEY = os.environ.get("ONMETA_API_KEY", "").strip()
