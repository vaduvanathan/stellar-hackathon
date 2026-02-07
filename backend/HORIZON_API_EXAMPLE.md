# Using the Horizon API (backend only, no frontend SDK)

Horizon is the HTTP API for the Stellar network. Your backend already uses it via `horizon_client.py`. The frontend does **not** load the Stellar SDK; the backend builds transactions and uses Horizon.

## 1. Direct Horizon REST (backend)

```python
# horizon_client.py already does this:
import requests
HORIZON_URL = "https://horizon-testnet.stellar.org"  # or from config

# Get account
r = requests.get(f"{HORIZON_URL}/accounts/{public_key}", timeout=10)
account = r.json()  # sequence, balances, signers, etc.

# Get last transaction (for inactivity)
r = requests.get(
    f"{HORIZON_URL}/accounts/{account_id}/transactions",
    params={"order": "desc", "limit": 1},
    timeout=10,
)

# Submit a signed transaction (XDR base64)
r = requests.post(
    f"{HORIZON_URL}/transactions",
    data=signed_envelope_xdr,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    timeout=30,
)
```

## 2. Our API that uses Horizon (no SDK in frontend)

**Get account (Horizon under the hood):**

```http
GET /api/horizon/account/GYOUR_PUBLIC_KEY
```

Returns the raw Horizon account JSON (sequence, balances, signers, etc.).

**Build add-signer transaction (backend uses Horizon + Python SDK):**

```http
POST /api/build-add-signer
Content-Type: application/json

{"account_public_key": "G...", "signer_public_key": "G..."}
```

Returns `{"transaction_xdr": "base64..."}`. Frontend sends this to Freighter to sign, then POSTs the signed XDR to `/api/claim/submit`.

## 3. Adding a secondary signer (backend code)

The backend uses Horizon to load the account, then the Python Stellar SDK to build the Set Options transaction:

```python
from horizon_client import get_account
from stellar_sdk import Account, Signer, TransactionBuilder

acc = get_account(account_public_key)  # Horizon REST
sequence = int(acc["sequence"])
source = Account(account_public_key, sequence)
signer = Signer.ed25519_public_key(secondary_public_key, 1)

envelope = (
    TransactionBuilder(source, network_passphrase=NETWORK_PASSPHRASE, base_fee=100)
    .append_set_options_op(signer=signer)
    .set_timeout(180)
    .build()
)
xdr_b64 = envelope_to_xdr_base64(envelope)  # return to frontend
```

Frontend only needs to call this API, pass the XDR to Freighter to sign, then submit.
