# Deploy Walletsurance to Google Cloud Run + run the agent

## Onmeta Off-Ramp (mock now, real later)

- **Mock API** (same shape as [Onmeta Off-Ramp API](https://documenter.getpostman.com/view/20857383/UzXNTwpM)):
  - **POST /api/mock-onmeta/create-order** – body: `sellTokenSymbol`, `chainId`, `fiatCurrency`, `fiatAmount`, `paymentMode`, `bankDetails` (accountNumber, accountName, ifsc). Returns mock `orderId` and `status`.
- **Client:** `onmeta_client.create_offramp_order()` – if `ONMETA_BASE_URL` and `ONMETA_API_KEY` are set, calls real Onmeta; otherwise returns mock. Agent uses this when running off-ramp after a claim.
- **Real Onmeta:** Set env vars `ONMETA_BASE_URL` (e.g. `https://api.onmeta.in`) and `ONMETA_API_KEY` in Cloud Run when ready.

---

## 1. Deploy the backend to Cloud Run

You can connect your GitHub repo to Cloud Run and deploy from the **backend** folder (Dockerfile is there).

### Option A: Deploy from your machine (gcloud CLI)

1. **Install Google Cloud SDK** and log in:
   ```bash
   # Install: https://cloud.google.com/sdk/docs/install
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Build and deploy** (from repo root; run from your machine where `gcloud auth login` was done):
   ```bash
   cd stellar-hackthon/backend
   gcloud run deploy walletsurance \
     --source . \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars "CONTRACT_ID=CCOZSAWX2SEGGGXVRP2ZQFR7Y5GZIV64VBLJFUH2PHY4HG7KQDVOENMJ,SOROBAN_RPC_URL=https://soroban-testnet.stellar.org"
   ```
   For **real Onmeta** later, add: `ONMETA_BASE_URL=https://api.onmeta.in,ONMETA_API_KEY=your_key`
   Replace project/region if needed. You’ll get a URL like `https://walletsurance-xxxxx.run.app`.

3. **Optional env vars** (in Cloud Run → Edit & deploy new revision → Variables):
   - `CONTRACT_ID` – your deployed contract ID
   - `SOROBAN_RPC_URL` – default Testnet
   - `DATABASE_PATH` – leave default (ephemeral) or use a volume for persistence
   - `PORT` – Cloud Run sets this to 8080

### Option B: Deploy from GitHub (Cloud Build + Cloud Run)

1. In **Google Cloud Console**: **Cloud Run** → **Create Service** → **Continuously deploy from a repository**.
2. Connect **GitHub** and select `vaduvanathan/stellar-hackathon`.
3. Set **Build type** to **Dockerfile** and **Dockerfile path** to `backend/Dockerfile` (or build context `backend`).
4. Set **Service name** (e.g. `walletsurance`) and **Region**.
5. Under **Variables**, add:
   - `CONTRACT_ID` = `CCOZSAWX2SEGGGXVRP2ZQFR7Y5GZIV64VBLJFUH2PHY4HG7KQDVOENMJ`
   - `SOROBAN_RPC_URL` = `https://soroban-testnet.stellar.org`
6. Deploy. Note the **Service URL**.

---

## 2. Run the agent on a schedule

The agent **checks the contract** and, if `can_claim` is true, runs the **mock** claim + off-ramp and logs it. You trigger it by calling the deployed service.

### Call the agent manually

- **Check and run (recommended):**  
  `GET` or `POST` your Cloud Run URL + `/api/agent/check`  
  Example: `https://walletsurance-xxxxx.run.app/api/agent/check`  
  This uses `CONTRACT_ID` from env, reads chain status, and if claimable runs the mock flow.

- **Run mock without check:**  
  `POST` URL + `/api/agent/run` with body `{"contract_id":"...", "beneficiary_address":"..."}` (optional).

### Run the agent on a schedule (Cloud Scheduler)

1. In **Google Cloud Console**: **Cloud Scheduler** → **Create job**.
2. **Name:** e.g. `walletsurance-agent`.
3. **Frequency:** e.g. `0 * * * *` (every hour) or `0 */6 * * *` (every 6 hours).
4. **Target type:** **HTTP**.
5. **URL:** `https://YOUR_CLOUD_RUN_URL/api/agent/check`
6. **HTTP method:** GET (or POST).
7. **Auth:** If the Cloud Run service allows unauthenticated invocations, no auth. Otherwise use **OIDC** with the same project’s service account.

After creation, you can **Run now** to test. The agent will:
- Read contract status from chain.
- If `can_claim` is false → return “Contract not claimable”.
- If `can_claim` is true → run mock claim + off-ramp, log to `agent_runs`, return success.

---

## 3. Real claim (later)

To perform a **real** on-chain `claim()` from the agent, you would:

1. Set **AGENT_SECRET_KEY** in Cloud Run (a funded Stellar key that can submit the transaction).
2. In the backend, when `can_claim` is true, build and sign a Soroban transaction that calls `claim()` on the contract, then submit it via RPC.
3. After a successful claim, call the real Onmeta Off-Ramp API (or keep mock for demo).

The current `/api/agent/check` only runs the **mock** flow; it does not submit a real transaction.
