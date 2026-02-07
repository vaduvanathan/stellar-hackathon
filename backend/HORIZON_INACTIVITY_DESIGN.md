# Design: Horizon-based inactivity detection + full wallet balance

**Goal:** Use Stellar Horizon to detect when a wallet has been **inactive** for a period. If inactive, trigger sending the **entire wallet balance** (e.g. to a beneficiary or into the existing inheritance/claim flow).

---

## 1. What “activity” means

We need a clear rule so the agent can say “this wallet is inactive.”

**Option A – Last transaction time**  
- Use Horizon to fetch the account’s **last transaction** (or last N).  
- “Inactive” = no transaction for the last X days (e.g. 30, 90).  
- Horizon: `GET /accounts/{account}/transactions?order=desc&limit=1` (or `payments`, `operations`).

**Option B – Last “ping” only**  
- Activity = only when the user explicitly pings (e.g. our contract’s `ping()` or a dedicated “I’m alive” tx).  
- Then we already have “last ping” on-chain (current design). Horizon would only be used to list/verify those pings if needed.

**Option C – Any payment or transfer**  
- “Active” = any payment to/from the account in the last X days.  
- Horizon: `GET /accounts/{account}/payments?order=desc&limit=1` and check `created_at`.

**Recommendation for “entire wallet” use case:**  
Use **Option A or C** (Horizon-based “last activity” by time). So: **inactive = no relevant Horizon activity for X days.**

---

## 2. What Horizon gives us

- **Account:** `GET https://horizon-testnet.stellar.org/accounts/{address}`  
  - Balances (XLM + assets), thresholds, signers.  
- **Transactions:** `GET /accounts/{account}/transactions?order=desc&limit=1`  
  - Last tx and its `created_at` (or `ledger_close_time`).  
- **Payments / Operations:**  
  - `GET /accounts/{account}/payments?order=desc&limit=1`  
  - Or operations if we want “any operation” as activity.

We can define:  
**last_activity_at** = max of (last transaction time, or last payment time) for that account.  
**Inactive** = `now - last_activity_at > inactivity_days` (e.g. 30 days).

---

## 3. “Send entire wallet balance”

On Stellar, an account can hold:

- **Native XLM** (balance minus reserves).  
- **Other assets** (via trustlines): e.g. USDC, custom tokens.

So “entire wallet balance” can mean:

- Send **all spendable XLM** to a destination.  
- Optionally also **all other assets** (each trustline balance) to the same or different destinations.

**Important:** Moving funds **requires a signature** from the account (or from something the account has authorized).

So we have two high-level designs:

**Design A – Custodial / pre-authorized key**  
- User gives us (or a dedicated “executor” service) a **secret key** or a **signing key** that can move funds.  
- When Horizon says “inactive for X days”, our agent uses that key to send all balances to the beneficiary.  
- Security/trust: the executor must be highly trusted and secured (vault, HSM, etc.).

**Design B – Smart contract / pre-signed instructions**  
- User locks funds **in a contract** while active (e.g. our current inheritance contract).  
- “Inactivity” is defined by the contract (e.g. no `ping()` for X ledgers).  
- When inactive, the **contract** (or an authorized claimer) moves the funds. No need to hold the user’s main wallet key.  
- This is our **current Walletsurance model**: funds are already in the contract; we don’t need to “send entire wallet” from the user’s account—we only need to **claim()** from the contract.

**Design C – Hybrid: Horizon detects inactivity, then trigger contract or custodial**  
- Use **Horizon only to detect** “this G... account has had no activity for X days.”  
- Then either:  
  - **If user has a contract (e.g. Walletsurance):** trigger existing `claim()` flow (contract holds the funds; no “entire wallet” from G...).  
  - **If we want “entire wallet”:** we must have a pre-authorized way to move from that G... (Design A), or we first need the user to move funds into a contract that can be claimed when inactive (Design B).

So:

- **“Use Horizon to find activity and if inactive send entire wallet”** is straightforward **only if** we have a way to sign for that wallet (Design A).  
- If we **don’t** want to hold the user’s key, we need the funds to already be in a contract and use Horizon only as an **extra signal** (e.g. “mark as inactive” or “trigger claim”), not as the mover of the “entire wallet” from a plain G... account.

---

## 4. Proposed flow (for later implementation)

**Phase 1 – Horizon inactivity check (read-only)**  
1. User registers a **Stellar address (G...)** and an **inactivity threshold** (e.g. 30 days).  
2. Agent (cron/Cloud Scheduler) runs periodically.  
3. For each registered account, call Horizon:  
   - `GET /accounts/{account}/transactions?order=desc&limit=1`  
   - Compute `last_activity_at` from the last tx (or last payment).  
   - If `now - last_activity_at > inactivity_days` → mark account as **inactive**.

**Phase 2 – What to do when inactive**  
- **Option 2a – Contract-first (current Walletsurance):**  
  - User has already moved “inheritance” funds into our contract (deposit + beneficiary).  
  - Horizon is only an **optional extra**: e.g. “if G... has been inactive for 30 days and this contract exists, run claim().”  
  - We do **not** send “entire wallet” from G...; we only claim from the contract.  

- **Option 2b – Full wallet sweep (needs custodial key):**  
  - When Horizon says “inactive”, agent uses a **pre-authorized key** for that G... to send:  
    - All spendable XLM (minus reserve) to beneficiary.  
    - Optionally, all trustline balances to beneficiary (separate payments per asset).  
  - Requires: secure storage of keys, KYC/compliance, and user consent.

**Phase 3 – Optional: combine both**  
- Users who only want “inheritance vault” use the contract (no key handover).  
- Users who want “entire wallet if I’m inactive” opt in to Design A (key handover or multisig with us as co-signer) and we use Horizon for inactivity + full sweep.

---

## 5. Technical pieces to add (when we implement)

1. **Horizon client (backend)**  
   - Config: `HORIZON_URL` (e.g. `https://horizon-testnet.stellar.org`).  
   - Function: `get_last_activity(account_id: str) -> datetime | None`  
     - From `GET /accounts/{account}/transactions?order=desc&limit=1` (or payments).  
   - Function: `is_inactive(account_id: str, inactivity_days: int) -> bool`.

2. **DB / config**  
   - Store per user: `stellar_address`, `inactivity_days`, optional `beneficiary_address`, optional `contract_id` (if they use Walletsurance contract).  
   - Optional: flag for “full wallet sweep” vs “contract claim only.”

3. **Agent loop**  
   - For each registered account:  
     - If “contract only”: check contract’s `can_claim` (current flow) and/or optionally check Horizon inactivity.  
     - If “full wallet”: check Horizon inactivity; if inactive, run sweep (if we have key for that account).

4. **Sweep logic (only if Design A)**  
   - Load account from Horizon → get balances.  
   - For native XLM: create payment (amount = balance - reserve).  
   - For each asset: create payment for full balance.  
   - Sign and submit with the pre-authorized key.

---

## 6. Summary

| Item | Description |
|------|-------------|
| **Horizon** | Use `GET /accounts/{id}/transactions` (or `/payments`) to get last activity time. |
| **Inactive** | No activity for X days (configurable). |
| **“Send entire wallet”** | Requires either (A) custodial/pre-authorized key to move from G..., or (B) funds already in a contract and we only claim from contract. |
| **Next steps** | Implement Phase 1 (Horizon + inactivity check); then decide whether to add Phase 2b (full sweep with key) or only use Horizon to reinforce contract-claim flow. |

We can implement Phase 1 (Horizon client + inactivity check) in code next, and leave Phase 2 (what to do when inactive) as configurable so we can plug in “contract claim” or “full sweep” later.
