# Did the build align with the original pitch?

## Yes — core idea is there

| Slide | Pitch | What we built |
|-------|--------|----------------|
| **1** | Walletsurance · On-chain inheritance, pays in cash | ✓ Same branding; contract + mock off-ramp to “bank” (mock) |
| **2** | Lost crypto; family needs cash, not keys | ✓ Dead man’s switch; beneficiary gets bank details, not keys |
| **3** | Automated, Crypto→USDC→Fiat, direct to bank, zero friction | ✓ Soroban vault, agent, mock Onmeta (USDC→fiat), beneficiary registration |
| **4** | User pings → Vault + time lock → Timer expires → Agent → Bank | ✓ `ping()` on-chain; vault + timeout; agent checks `can_claim`, calls off-ramp; mock IMPS/NEFT |
| **5** | Why Stellar: TTL, low fees, trustlines | ✓ Soroban contract on Testnet |
| **6** | OTP bypass / pre-signed session keys | ⚠ Simplified: agent executes off-ramp via API (no user OTP). No full KYC/“standing instruction” flow yet |
| **7** | Freemium, 1% fee, wallet partnerships | ○ Not in MVP (future) |
| **9** | Testnet MVP → Onmeta → Multi-chain | ✓ Testnet MVP; Onmeta-ready (mock + env for real); multi-chain not built |

## Gaps (small)

1. **Ping** = on-chain only. User must call `ping()` from a Stellar wallet (Freighter, Lab). Visiting the website does **not** ping. (We added this clarification in the UI.)
2. **Contract status** stuck on “Loading…” or “cc”: usually means the Cloud Run service can’t reach Soroban RPC or env vars are missing. We improved the UI (short contract ID, timeout, clearer error).
3. **Slide 6 (OTP)**: We have “agent does off-ramp without user” but not the full account-abstraction / standing-instruction story.

## Summary

The build matches the original idea: **on-chain inheritance vault + timer + agent that off-ramps to cash (mock bank)**. Ping is on-chain; contract status display and errors are improved; alignment with the deck is strong for an MVP.
