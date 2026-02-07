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

# Horizon (for inactivity detection)
HORIZON_URL = os.environ.get(
    "HORIZON_URL",
    "https://horizon-testnet.stellar.org",
).rstrip("/")

# Nominee flow: SMS (Twilio). Leave empty to mock SMS (log only).
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "").strip()

# Base URL for claim links in SMS (e.g. https://your-app.run.app)
CLAIM_BASE_URL = os.environ.get("CLAIM_BASE_URL", "").strip()

# When nominee chooses "Send to bank", swept funds go to this address; then we call Onmeta to send fiat to their bank.
PLATFORM_SWEEP_PUBLIC_KEY = os.environ.get("PLATFORM_SWEEP_PUBLIC_KEY", "").strip()
# Rough XLM → INR for off-ramp (e.g. 10); used when creating Onmeta order from amount_xlm.
RATE_XLM_TO_INR = float(os.environ.get("RATE_XLM_TO_INR", "10").strip() or "10")
