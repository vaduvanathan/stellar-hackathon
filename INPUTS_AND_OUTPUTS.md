# Walletsurance – Inputs & Expected Outputs

Use this as a cheat sheet when testing the UI or API.

---

## 1. Contract status

**How:** Open **http://localhost:8080/** or **GET http://localhost:8080/api/contract/status**

**Input:** None.

**Expected output (no deposit yet):**
```json
{
  "can_claim": false,
  "beneficiary_address": null,
  "contract_id": "CCOZSAWX2SEGGGXVRP2ZQFR7Y5GZIV64VBLJFUH2PHY4HG7KQDVOENMJ"
}
```
- **UI:** Shows "Not claimable", "Beneficiary: —", and the contract ID.

**If CONTRACT_ID not set:** 503 with `"error": "Contract status unavailable"` and a hint.

---

## 2. Register beneficiary

**How:** UI form at http://localhost:8080/ or **POST http://localhost:8080/api/beneficiary** with JSON body.

### Inputs

| Field | Required | Example | Notes |
|-------|----------|---------|--------|
| Stellar address | Yes | `GAGONWXAMFADQZUYYVTRS6W32HIJTMAHLDIM5RFMLDWILCQJXDA33P54` | Must start with `G`, 56 characters |
| Contract ID | No | `CCOZSAWX2SEGGGXVRP2ZQFR7Y5GZIV64VBLJFUH2PHY4HG7KQDVOENMJ` | Your deployed contract |
| Account holder name | No | `John Doe` | Mock |
| Account number | No | `1234567890` | Mock |
| IFSC code | No | `SBIN0001234` | Mock |
| Bank name | No | `State Bank` | Mock |

### Example JSON (POST /api/beneficiary)

```json
{
  "stellar_address": "GAGONWXAMFADQZUYYVTRS6W32HIJTMAHLDIM5RFMLDWILCQJXDA33P54",
  "contract_id": "CCOZSAWX2SEGGGXVRP2ZQFR7Y5GZIV64VBLJFUH2PHY4HG7KQDVOENMJ",
  "bank_account_holder": "John Doe",
  "bank_account_number": "1234567890",
  "bank_ifsc": "SBIN0001234",
  "bank_name": "State Bank"
}
```

### Expected output (success)

**Status:** 200  
**Body:**
```json
{
  "stellar_address": "GAGONWXAMFADQZUYYVTRS6W32HIJTMAHLDIM5RFMLDWILCQJXDA33P54",
  "contract_id": "CCOZSAWX2SEGGGXVRP2ZQFR7Y5GZIV64VBLJFUH2PHY4HG7KQDVOENMJ",
  "message": "Beneficiary registered (mock bank details stored)"
}
```
- **UI:** Green message: "Registered."

### Expected output (validation error)

**Invalid address (e.g. `giiuiuiu`):**  
**Status:** 400  
**Body:** `{"error": "Stellar address must start with G and be 56 characters (e.g. GAGONWX...)")`

**Missing address:**  
**Status:** 400  
**Body:** `{"error": "stellar_address required"}`

---

## 3. Get beneficiary

**How:** **GET http://localhost:8080/api/beneficiary/<stellar_address>**

**Input:** Stellar address in URL, e.g.  
`/api/beneficiary/GAGONWXAMFADQZUYYVTRS6W32HIJTMAHLDIM5RFMLDWILCQJXDA33P54`

**Expected output (found):**
```json
{
  "stellar_address": "GAGONWXAMFADQZUYYVTRS6W32HIJTMAHLDIM5RFMLDWILCQJXDA33P54",
  "contract_id": "CCOZSAWX2SEGGGXVRP2ZQFR7Y5GZIV64VBLJFUH2PHY4HG7KQDVOENMJ",
  "bank_account_holder": "John Doe",
  "bank_name": "State Bank"
}
```

**Expected output (not found):** 404, `{"error": "Not found"}`

---

## 4. Health

**How:** **GET http://localhost:8080/health**

**Input:** None.

**Expected output:**
```json
{
  "status": "ok",
  "service": "walletsurance"
}
```

---

## 5. Agent run (mock)

**How:** UI "Run agent" button or **POST http://localhost:8080/api/agent/run** with body `{}` or `{"contract_id":"...", "beneficiary_address":"...", "amount_mocked":"0"}`.

**Input:** Optional JSON body; can be empty `{}`.

**Expected output:**
```json
{
  "message": "Agent run completed (mocked)",
  "claim_mock": "success",
  "offramp_mock": "Onmeta Off-Ramp API mocked – fiat wire simulated"
}
```
- **UI:** Green message with the same text.

---

## 6. Agent runs list

**How:** **GET http://localhost:8080/api/agent/runs**

**Input:** None.

**Expected output:** Array of recent mock runs, e.g.:
```json
[
  {
    "contract_id": null,
    "beneficiary_address": null,
    "amount_mocked": "0",
    "offramp_mock_status": "mocked_success",
    "created_at": "2026-02-07 12:00:00"
  }
]
```

---

## Quick test sequence

1. **Health:** `curl http://localhost:8080/health` → `{"status":"ok","service":"walletsurance"}`  
2. **Contract status:** Open http://localhost:8080/ → see "Not claimable", "Beneficiary: —".  
3. **Register beneficiary:** Fill form with a valid `G...` address (e.g. your public key) + optional bank fields → click Register → see "Registered."  
4. **Agent:** Click "Run agent" → see "Agent run completed (mocked)".
