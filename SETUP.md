# Walletsurance – Testnet setup guide

This guide tells you **what account to get**, **what API/key you need**, and **what to do next** to use Stellar Soroban Testnet with Walletsurance.

---

## 1. What account do I need?

You need **one Stellar Testnet account** (a keypair). There is no “sign up” — you **generate** the keys yourself.

- **Public key** (starts with `G...`) – like an address; safe to share.
- **Secret key** (starts with `S...`) – like a password; **never share or commit**.

You use this account to:
- Pay for deploying the contract (one-time).
- Optionally pay for transactions (e.g. deposit, ping) when testing.

---

## 2. Do I need an API key?

**For Testnet with this project: usually no.**

- **RPC (reading chain / simulating):**  
  Public Testnet RPC is free: `https://soroban-testnet.stellar.org`  
  No API key required for normal use.

- **Optional:**  
  If you use another RPC provider (e.g. for higher rate limits), they may give you an API key and a different URL. You would then set `SOROBAN_RPC_URL` (and any headers they require) in your backend. For the hackathon, the default URL is enough.

- **Onmeta (off-ramp):**  
  We **mock** the Onmeta API in this project, so you don’t need a real Onmeta API key for the demo.

---

## 3. Step-by-step: get an account and use Testnet

### Step A – Create a keypair (account)

**Option 1 – Stellar CLI (recommended for deploy)**

```bash
# Create a new keypair and save it as identity "default"
stellar keys add default
```

You’ll see:
- **Public key:** `G...` (this is your “account”)
- **Secret key:** `S...` (store it safely; the CLI can save it for you)

**Option 2 – Stellar Laboratory (browser)**

1. Open: [Stellar Laboratory – Account Creator](https://laboratory.stellar.org/#account-creator?network=test)
2. Choose **Network: Test**
3. Click **Generate keypair**
4. Copy and store:
   - **Public key** (`G...`)
   - **Secret key** (`S...`)

---

### Step B – Fund the account (get test XLM)

Testnet uses fake XLM. You get it from **Friendbot** (free faucet).

**If you used the CLI (Step A, Option 1):**

```bash
# Replace G... with the public key from "stellar keys add default"
curl "https://friendbot.stellar.org/?addr=YOUR_PUBLIC_KEY"
```

Example:

```bash
curl "https://friendbot.stellar.org/?addr=GABCD1234..."
```

**If you used the Laboratory (Step A, Option 2):**

1. Stay on [Account Creator](https://laboratory.stellar.org/#account-creator?network=test)
2. Paste your **public key** (`G...`)
3. Click **Fund account** (or “Get lumens”) to use Friendbot.

You should see a success message and a balance (e.g. 10,000 XLM on Testnet).

---

### Step C – Add the key to Stellar CLI (if you used Laboratory)

If you created the keypair in the browser, add it to the CLI so you can deploy:

```bash
stellar keys add default --secret-key "S..."
```

Use the secret key you copied from the Laboratory.

---

### Step D – Deploy the contract

From the repo root:

```bash
./scripts/deploy_inheritance.sh
```

Or manually:

```bash
cd stellar-hackthon/walletsurance
stellar contract deploy \
  --wasm target/wasm32v1-none/release/inheritance.wasm \
  --network testnet \
  --source-account default
```

Copy the **contract ID** that is printed (starts with `C...`).

---

### Step E – Configure the backend

Set the deployed contract ID so the backend can read contract status:

```bash
cd stellar-hackthon/backend
export CONTRACT_ID=C...   # paste the contract ID from Step D
# Optional: already set by default
# export SOROBAN_RPC_URL=https://soroban-testnet.stellar.org
source .venv/bin/activate
python app.py
```

Then open: `http://localhost:8080/api/contract/status`  
You should see something like `can_claim`, `beneficiary_address`, `contract_id` (or a clear error if something is wrong).

---

## 4. Quick reference

| What            | Value / where |
|-----------------|----------------|
| **Account**     | One keypair: public `G...` + secret `S...` (you generate it). |
| **Fund account** | Friendbot: `https://friendbot.stellar.org/?addr=G...` or Lab “Fund account”. |
| **RPC (Testnet)**| `https://soroban-testnet.stellar.org` (no API key needed). |
| **API key**      | Not required for Testnet RPC or for the mocked Onmeta flow in this repo. |
| **Contract ID**  | Printed when you run `./scripts/deploy_inheritance.sh`; set as `CONTRACT_ID` in the backend. |

---

## 5. Next steps after setup

1. **Backend:** Run the Flask app with `CONTRACT_ID` set and call `GET /api/contract/status`.
2. **Frontend / flows:** Build a small UI or Postman/curl flows to:  
   - Register a beneficiary (mock bank details),  
   - Deposit (invoke contract from a funded account),  
   - Ping (invoke contract),  
   - Trigger the mock agent (claim + mock off-ramp).
3. **Agent (optional):** Implement a periodic job that checks `can_claim`, then submits `claim` and calls the mock Onmeta off-ramp.
4. **Hosting:** Connect the repo to Google Cloud (Cloud Run or Compute Engine) and set env vars (`CONTRACT_ID`, `SOROBAN_RPC_URL`, etc.) there.

For more links (Stellar docs, SDK, Onmeta API), see the main [README](README.md).
