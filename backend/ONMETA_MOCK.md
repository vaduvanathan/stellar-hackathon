# Onmeta Off-Ramp mock API

Matches [Onmeta Off-Ramp API](https://documenter.getpostman.com/view/20857383/UzXNTwpM) for easy swap to real Onmeta later.

## Mock endpoint (this app)

**POST /api/mock-onmeta/create-order**

**Headers:** optional `x-api-key`, `Authorization` (ignored in mock).

**Body (JSON):**
```json
{
  "sellTokenSymbol": "XLM",
  "chainId": 1,
  "fiatCurrency": "inr",
  "fiatAmount": 1000,
  "paymentMode": "INR_IMPS",
  "bankDetails": {
    "accountNumber": "1234567890",
    "accountName": "Jane Doe",
    "ifsc": "SBIN0001234"
  },
  "metaData": {}
}
```

**Response (200):**
```json
{
  "orderId": "mock-order-abc123def456",
  "status": "created",
  "fiatAmount": 1000,
  "fiatCurrency": "inr",
  "paymentMode": "INR_IMPS",
  "message": "Mock Onmeta Off-Ramp order (set ONMETA_BASE_URL and ONMETA_API_KEY for real)."
}
```

Use the same body in Postman against your deployed URL: `https://YOUR_CLOUD_RUN_URL/api/mock-onmeta/create-order`.

## Real Onmeta

Set in Cloud Run (or .env):

- `ONMETA_BASE_URL` = e.g. `https://api.onmeta.in`
- `ONMETA_API_KEY` = your API key from Onmeta dashboard

Then `onmeta_client.create_offramp_order()` will POST to the real API instead of returning mock.
