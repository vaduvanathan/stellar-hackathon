# Walletsurance – Stellar Build-A-Thon Chennai

**On-chain inheritance protocol (Dead Man's Switch)** for the [Stellar Build-A-Thon – Chennai Edition](https://stellar.org) (7–8 Feb 2026).

## Overview

- Users **lock funds** in a Soroban smart contract and set a **beneficiary** and **timeout**.
- If the user does **not** call **ping** within the timeout, a **Python agent** can **claim** the funds, (mock) convert them, and (mock) wire fiat to the beneficiary via **Onmeta Off-Ramp API**.

## Repo layout

| Path | Description |
|------|-------------|
| `walletsurance/` | Soroban workspace: Rust smart contracts (inheritance = dead man's switch) |
| `backend/` | Python Flask API + agent: SQLite, mock Onmeta, agent trigger |

### Contract (Rust / Soroban)

- **Target:** Stellar Soroban **Testnet**.
- **Contract:** `walletsurance/contracts/inheritance` – deposit, ping, claim, can_claim, beneficiary views.
- Build: from `walletsurance/` run `stellar contract build` (builds all contracts including `inheritance.wasm`).

### Backend (Python / Flask)

- **Database:** SQLite (mock beneficiary bank details).
- **Endpoints:** **`/`** minimal UI; health, register beneficiary, get beneficiary, **contract status** (reads `can_claim` / `beneficiary` from chain), mock agent run, list agent runs.
- **RPC:** Set `CONTRACT_ID` and `SOROBAN_RPC_URL` (default Testnet) to read contract state on-chain.
- **Mocking:** No real money; Onmeta Off-Ramp and OTP are mocked.

### Hosting

- Intended for **Google Cloud** (Cloud Run or Compute Engine); repo can be connected manually for deploy.

## Quick start

### Contract

```bash
cd stellar-hackthon/walletsurance
rustup target add wasm32v1-none   # if not already
stellar contract build
```

### Deploy contract to Testnet (Step 3)

1. Configure identity: `stellar keys add default` (then fund the account via [Stellar Laboratory](https://laboratory.stellar.org/#account-creator?network=test)).
2. Deploy:
   ```bash
   ./scripts/deploy_inheritance.sh
   ```
   Or manually:
   ```bash
   cd walletsurance && stellar contract deploy --wasm target/wasm32v1-none/release/inheritance.wasm --network testnet --source-account default
   ```
3. Set the returned contract ID in the backend: `export CONTRACT_ID=<id>` (or in `.env` / Cloud Run env).

### Backend

```bash
cd stellar-hackthon/backend
python3 -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
export CONTRACT_ID=<deployed-contract-id>   # optional, for /api/contract/status
python app.py
# API: http://localhost:8080/health
# Minimal UI: http://localhost:8080/
# Contract status: http://localhost:8080/api/contract/status
```

## Testnet account and keys

**Account:** One Stellar Testnet keypair (public `G...`, secret `S...`). Generate with `stellar keys add default` or [Stellar Laboratory](https://laboratory.stellar.org/#account-creator?network=test).  
**Fund:** [Friendbot](https://friendbot.stellar.org/?addr=YOUR_PUBLIC_KEY) or Lab “Fund account”.  
**API key:** Not required for Testnet RPC (`https://soroban-testnet.stellar.org`) or for the mocked Onmeta flow.

See **[SETUP.md](SETUP.md)** for a full step-by-step (account → fund → deploy → backend).

## References

- [Stellar Hacker Guide / Setup](https://developers.stellar.org/docs/build/smart-contracts/getting-started/setup)
- [JS Stellar SDK](https://stellar.github.io/js-stellar-sdk/)
- [Frontend guide for Stellar dApps](https://developers.stellar.org/docs/build/guides/dapps/frontend-guide)
- [Onmeta Off-Ramp API (Postman)](https://documenter.getpostman.com/view/20857383/UzXNTwpM)
