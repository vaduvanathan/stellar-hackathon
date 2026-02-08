# SUPERNOVA

**On-chain crypto inheritance protocol** built for the [Stellar Build-A-Thon – Chennai Edition](https://stellar.org) (7–8 Feb 2026).

> *Death is inevitable. Lost crypto is not.*
> Don't leave your family with private keys they can't use. We bridge the gap between your crypto wallet and their bank account, automatically.

---

## Project Description

SUPERNOVA is a **dead man's switch for Stellar wallets**. When a wallet holder becomes inactive (passes away, loses access, or simply stops transacting), their nominated beneficiary automatically receives an SMS with a secure claim link. The nominee answers a secret question to unlock and sweep the entire wallet balance to their own Stellar address — or to their bank account via off-ramp.

**No custody. No intermediaries. No lost crypto.**

The private key is encrypted with the nominee's secret answer using PBKDF2 + AES-256-GCM. Decryption happens entirely in the browser — SUPERNOVA never sees the private key.

---

## Contract Address

| Item | Value |
|------|-------|
| **Network** | Stellar Testnet |
| **Soroban Contract (Inheritance)** | Set via `CONTRACT_ID` environment variable after deployment |
| **Horizon API** | `https://horizon-testnet.stellar.org` |
| **Soroban RPC** | `https://soroban-testnet.stellar.org` |
| **Network Passphrase** | `Test SDF Network ; September 2015` |

> The primary nominee flow uses Stellar **classic transactions** (co-signer keys + Set Options), not the Soroban contract. The Soroban contract (`walletsurance/contracts/inheritance/`) is a secondary lock-and-claim flow.

---

## Problem Statement

### The Problem

An estimated **$20+ billion in crypto** is lost forever because wallet holders pass away or lose access without sharing private keys. Families are left with no way to recover these assets. Unlike traditional bank accounts, there is no "next of kin" process for crypto.

### How SUPERNOVA Solves It

1. **No custody risk** — Funds stay in the user's own Stellar account. Nothing is locked in a contract or held by us.
2. **Automatic detection** — A background agent monitors the Stellar Horizon API for wallet inactivity every minute.
3. **SMS notification** — When inactivity exceeds the threshold, the nominee gets an SMS with a secure claim link.
4. **Zero-knowledge encryption** — The sweep key is encrypted with the nominee's answer. Only the correct answer can decrypt it, and decryption happens in the browser. We never see the key.
5. **Full sweep** — The nominee can claim the entire wallet balance (XLM + all tokens) in one transaction.
6. **Bank payout option** — Mock off-ramp integration (Onmeta API) to convert crypto to fiat.

---

## Features

- **Nominee Registration** — Register a nominee with phone number, secret question, and inactivity period (2 minutes for demo, 7/30/90 days for production)
- **Co-signer Key Generation** — Automatically generates a secondary Stellar keypair, encrypts the secret with the answer, and returns the public key to add as a co-signer
- **Freighter Wallet Integration** — Sign add-signer transactions directly in the browser using the Freighter extension
- **Automatic Inactivity Detection** — Background agent checks Horizon API every minute for wallet activity
- **SMS Claim Notifications** — Twilio-powered SMS with unique claim tokens
- **Browser-Side Decryption** — Web Crypto API (PBKDF2 + AES-256-GCM) decrypts the sweep key entirely client-side
- **Full Balance Sweep** — Calculates spendable balance accounting for reserves, fees, and all token types
- **Bank Off-Ramp (Mock)** — Simulated crypto-to-INR bank payout via Onmeta API
- **Soroban Smart Contract** — Secondary flow: Rust contract with deposit, ping, claim, and view functions
- **Cosmic UI/UX** — Animated canvas starfield, black hole vortex, scroll animations, mouse particle trail, and more
- **Mobile Responsive** — Optimized for all screen sizes with 3 breakpoints

---

## Architecture Overview

```
+------------------+       +-------------------+       +------------------+
|                  |       |                   |       |                  |
|   Frontend       |  API  |   Flask Backend   | HTTP  |  Stellar Testnet |
|   (HTML/JS)      +------>+   (Python)        +------>+  (Horizon API)   |
|                  |       |                   |       |                  |
|  - Freighter     |       |  - SQLite DB      |       |  - Accounts      |
|  - Web Crypto    |       |  - Background     |       |  - Transactions  |
|  - Canvas Stars  |       |    Agent (1 min)  |       |  - Soroban RPC   |
|                  |       |  - Twilio SMS     |       |                  |
+------------------+       +-------------------+       +------------------+
                                    |
                                    v
                           +-------------------+
                           |   Twilio SMS API  |
                           |   (claim links)   |
                           +-------------------+
```

### Flow

```
1. REGISTER        User fills form → Backend generates keypair →
                   Encrypts secret with answer → Stores ciphertext →
                   Returns public key → User adds as co-signer via Freighter

2. MONITOR         Background agent (every 1 min) → Calls Horizon API →
                   Checks last transaction timestamp → If inactive > threshold →
                   Generates claim token → Sends SMS via Twilio

3. CLAIM           Nominee opens SMS link → Enters answer →
                   Browser decrypts key (Web Crypto) → Builds sweep tx →
                   Signs with sweep key → Submits to Horizon → Funds transferred
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Smart Contract | Rust + Soroban SDK |
| Backend | Python 3.12 + Flask |
| Database | SQLite |
| Frontend | Vanilla HTML/CSS/JS + Canvas API |
| SMS | Twilio API |
| Blockchain | Stellar Testnet (Horizon REST + Soroban RPC) |
| Wallet | Freighter browser extension |
| Encryption | PBKDF2 + AES-256-GCM (Python + Web Crypto API) |
| Deployment | Docker + Google Cloud Run + Gunicorn |
| Testing | Pytest + unittest.mock |

### APIs Used

| API | Purpose |
|-----|---------|
| **Stellar Horizon** | Account data, transaction history, submit transactions |
| **Stellar Soroban RPC** | Smart contract interactions (deposit, claim, status) |
| **Twilio SMS** | Send claim notification SMS to nominees |
| **Onmeta Off-Ramp** | Crypto-to-fiat bank payout (mock) |
| **Freighter** | Browser wallet for signing transactions |

---

## Screenshots

### Homepage — Cosmic Theme with 3D Stellar Logo
The landing page features an animated canvas starfield with 280 twinkling stars, a black hole vortex around the spinning 3D Stellar logo, and a cosmic marquee strip.

### Nominee Registration — Create Secondary Key
The nominee page with glassmorphism cards, nebula gradient backgrounds, custom styled dropdowns, and Freighter wallet integration.

### Claim Page — Unlock & Sweep
The claim page where nominees answer the secret question to decrypt the sweep key and transfer the full wallet balance.

---

## Deployed Link

**Live on Google Cloud Run:**
`https://stellar-hackathon-242775953468.asia-south1.run.app`

---

## Repo Layout

| Path | Description |
|------|-------------|
| `walletsurance/` | Soroban workspace: Rust smart contracts (inheritance = dead man's switch) |
| `walletsurance/contracts/inheritance/` | Main Soroban contract: deposit, ping, claim, can_claim, beneficiary |
| `backend/` | Python Flask API + background agent + SQLite |
| `backend/templates/` | Frontend HTML pages (index, nominee, claim) |
| `backend/tests/` | Pytest test suite for inactivity detection & SMS |
| `scripts/` | Deployment scripts |

### Key Backend Files

| File | Purpose |
|------|---------|
| `app.py` | Flask app with 20 API routes + background scheduler |
| `config.py` | Environment-based configuration |
| `horizon_client.py` | Stellar Horizon API client (accounts, activity, submit) |
| `key_encrypt.py` | PBKDF2 + AES-GCM encryption for sweep keys |
| `sms_client.py` | Twilio SMS sending (or mock logging) |
| `soroban_client.py` | Soroban RPC client for contract interactions |
| `onmeta_client.py` | Off-ramp API client (real or mock) |
| `build_deposit.py` | Build unsigned Soroban deposit transactions |

---

## Quick Start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
# http://localhost:8080
```

### Smart Contract

```bash
cd walletsurance
rustup target add wasm32v1-none
stellar contract build
./scripts/deploy_inheritance.sh
```

### Environment Variables

Copy `backend/.env.example` to `backend/.env` and configure:

```bash
# Required for SMS (leave empty for mock logging)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=+1234567890

# Claim link base URL
CLAIM_BASE_URL=https://your-deployed-url.run.app

# Agent checks every N minutes (default: 1)
INACTIVITY_CHECK_INTERVAL_MINUTES=1
```

---

## Future Scope and Plans

1. **Multi-chain support** — Extend to Ethereum, Solana, and other chains so users can protect all their crypto assets from one dashboard
2. **Real off-ramp integration** — Connect to Onmeta or similar APIs for actual crypto-to-bank payouts in production
3. **Multi-nominee support** — Allow splitting funds between multiple nominees with configurable percentages
4. **Hardware wallet signing** — Support Ledger/Trezor for the add-signer step
5. **Mainnet deployment** — Move from Testnet to Stellar Mainnet with proper security audit
6. **Mobile app** — Native iOS/Android app for nominee management and push notifications
7. **Proof-of-life alternatives** — Instead of just transaction inactivity, support biometric check-ins, email confirmations, or trusted third-party verification
8. **Legal document generation** — Auto-generate inheritance documents linking on-chain setup to legal frameworks
9. **DAO governance** — Community-governed parameters for timeout thresholds and dispute resolution
10. **Insurance pool** — Optional insurance layer where users contribute to a pool that covers edge cases (e.g., early death before timeout)

---

## References

- [Stellar Developer Docs](https://developers.stellar.org/)
- [Soroban Smart Contracts Guide](https://developers.stellar.org/docs/build/smart-contracts/getting-started/setup)
- [Stellar Horizon API](https://developers.stellar.org/api)
- [Freighter Wallet](https://www.freighter.app/)
- [Twilio SMS API](https://www.twilio.com/docs/sms)
- [Onmeta Off-Ramp API](https://documenter.getpostman.com/view/20857383/UzXNTwpM)
- [Web Crypto API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Crypto_API)

---

## Team

Built at the **Stellar Build-A-Thon Chennai** (7–8 Feb 2026).

---

*SUPERNOVA — Because your crypto should outlive you.*
