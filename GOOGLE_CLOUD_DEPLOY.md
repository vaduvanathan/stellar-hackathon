# Deploy on Google Cloud (connect repo manually)

## In Google Cloud Console

**After pushing code:** Trigger a new deployment (Cloud Run → service → Edit & deploy new revision, or push to the connected branch). The `/nominee` page is sent with `Cache-Control: no-cache` so users get the latest after you deploy. If you still see old behaviour, do a hard refresh (Ctrl+F5 / Cmd+Shift+R) on the nominee page.

1. **Cloud Run** → **Create Service**.
2. **Deploy from repository** → connect **GitHub** → select `vaduvanathan/stellar-hackathon`.
3. **Build**: Dockerfile path = `backend/Dockerfile`. Build context = `backend` (or root; ensure Dockerfile is in context).
4. **Service name**: e.g. `walletsurance`. **Region**: e.g. `us-central1`.
5. **Authentication**: Allow unauthenticated (so you can open the UI).

## Variables to set (Environment variables)

| Name | Value |
|------|--------|
| CONTRACT_ID | `CCOZSAWX2SEGGGXVRP2ZQFR7Y5GZIV64VBLJFUH2PHY4HG7KQDVOENMJ` |
| SOROBAN_RPC_URL | `https://soroban-testnet.stellar.org` |

Optional later: `ONMETA_BASE_URL`, `ONMETA_API_KEY` (for real Onmeta); store API keys in Secret Manager and reference them.

## What to save (keys / key pairs)

- **Stellar secret key (S…)** – used for deploy or agent; store in a password manager or Secret Manager, never in repo.
- **Onmeta API key** – when you go live; store in Secret Manager.
- **Cloud Run service URL** – e.g. `https://walletsurance-xxxxx.run.app` (for UI and agent/check).

No key pairs needed for basic deploy; CONTRACT_ID and SOROBAN_RPC_URL are enough.

---

# Summary of what we did

- **Contract**: Rust inheritance (deposit, ping, claim, can_claim, beneficiary) on Soroban Testnet; contract ID above.
- **Backend**: Flask + SQLite; UI at `/`, APIs: beneficiary, contract status, agent run/check, mock Onmeta create-order.
- **UI**: One page – contract status, inactivity period (7/30/90 days), register beneficiary (bank + IFSC), “How to get Stellar account”, Run agent.
- **Onmeta**: Mock API aligned with [Onmeta Off-Ramp](https://documenter.getpostman.com/view/20857383/UzXNTwpM); set env for real.
- **Deploy**: Dockerfile in `backend/`; deploy from GitHub to Cloud Run.

---

# Next steps

1. **Deploy**: Cloud Run → connect repo → set CONTRACT_ID + SOROBAN_RPC_URL → deploy.
2. **Agent schedule**: Cloud Scheduler → HTTP GET to `https://YOUR_SERVICE_URL/api/agent/check` (e.g. hourly).
3. **Real Onmeta**: Add ONMETA_BASE_URL + ONMETA_API_KEY (from dashboard) when ready.
4. **Real claim**: Implement on-chain `claim()` with agent secret key (optional).
