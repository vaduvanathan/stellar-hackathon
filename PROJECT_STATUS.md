# Walletsurance – What’s Done & What’s Next

## Backend is running

- **UI:** http://localhost:8080/
- **Health:** http://localhost:8080/health

If the port isn’t running, start it:

```bash
cd stellar-hackthon/backend
source .venv/bin/activate
python app.py
```

---

## What’s done so far

### 1. Project setup
- Folder `stellar-hackthon` with contract workspace + backend.
- Pushed to GitHub: https://github.com/vaduvanathan/stellar-hackathon

### 2. Smart contract (Rust / Soroban)
- **Inheritance contract** in `walletsurance/contracts/inheritance/`:
  - `deposit(depositor, token, amount, beneficiary, timeout_ledgers)` – lock tokens
  - `ping()` – reset deadline (depositor only)
  - `claim()` – send funds to beneficiary if timeout passed
  - `can_claim()`, `beneficiary()` – view functions
- Built and **deployed on Soroban Testnet**.  
- **Contract ID:** `CCOZSAWX2SEGGGXVRP2ZQFR7Y5GZIV64VBLJFUH2PHY4HG7KQDVOENMJ`

### 3. Backend (Python / Flask)
- **SQLite** for beneficiaries (mock bank details) and agent runs.
- **Endpoints:** `/` (UI), `/health`, `/api/contract/status`, `/api/beneficiary` (POST/GET), `/api/agent/run`, `/api/agent/runs`.
- **RPC:** Reads contract state from chain when `CONTRACT_ID` and `SOROBAN_RPC_URL` are set (in `.env`).
- **Python deploy script** `backend/deploy_contract.py` – deploy from `.env` (no typing secret in terminal).
- **Thread-safe DB** – per-request connections so no SQLite thread errors.
- **Validation** – Stellar address must be G… and 56 chars.

### 4. Minimal UI
- Single page at http://localhost:8080/:
  - **Contract status** – can_claim, beneficiary, contract ID from chain.
  - **Register beneficiary** – Stellar address, contract ID, account holder, account number, IFSC, bank name.
  - **Agent (mock)** – button to trigger mock claim + off-ramp.
- Dark theme, simple form, error/success messages.

### 5. Docs & references
- `README.md` – overview, quick start, deploy.
- `SETUP.md` – Testnet account, Friendbot, keys, no API key needed.
- `DEPLOY_NOW.md` – deploy via `.env` (no typing secret).
- `INPUTS_AND_OUTPUTS.md` – what to send and expected responses.
- `.env.example` – template; real `.env` (with secret) is gitignored.

---

## Next steps (optional)

| Step | What | Why |
|------|------|-----|
| **1. Real deposit/ping from UI** | Add “Deposit” and “Ping” flows that build and submit Soroban transactions (e.g. with Freighter or server-signed tx). | So users can lock funds and reset the switch from the app. |
| **2. Agent logic (real check)** | Backend job or cron that calls `can_claim()` for known contracts; if true, submit `claim()` then call mock Onmeta. | Completes the “dead man’s switch” automation. |
| **3. Deploy to Google Cloud** | Connect repo to Cloud Run (or Compute Engine), set env vars (`CONTRACT_ID`, `SOROBAN_RPC_URL`, etc.), deploy. | Public URL and always-on backend. |
| **4. Real Onmeta integration** | Replace mock with real Onmeta Off-Ramp API + OTP when ready. | Real fiat payout to beneficiary. |
| **5. Frontend polish** | Loading states, better errors, wallet connect (e.g. Stellar Freighter). | Better UX. |

---

## Quick commands

```bash
# Start backend (from repo root or backend/)
cd stellar-hackthon/backend && source .venv/bin/activate && python app.py

# Build contract
cd stellar-hackthon/walletsurance && stellar contract build

# Deploy contract again (if needed)
cd stellar-hackthon/backend && python deploy_contract.py
```
