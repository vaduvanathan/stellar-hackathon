# Walletsurance flow – who does what

## 1. Why does the recipient have a Stellar address (G…) if they get fiat?

On Stellar, the contract can only send **tokens** to a **Stellar address**. It cannot send INR directly to a bank account. So the chain always has a “beneficiary address” (G…).

Two ways to still give them **fiat only** (no keys for family):

- **A) Platform holds the receiving address**  
  We set the on-chain beneficiary to an address we control. When the agent claims, tokens go to that address. We then off-ramp (e.g. Onmeta) and send INR to the **bank account** the user registered. The family never needs a wallet; they only need to give bank details.

- **B) Their address**  
  If we send tokens to the family’s own G…, they would receive crypto and would need to cash out themselves (so they’d need a wallet). That’s not “cash in bank, no keys.”

So: **for “recipient gets fiat only,” the recipient does not need a Stellar wallet.** We only need their **bank details**. The G… can be ours; we use the bank details in our backend to send the money. The current form asks for a Stellar address too – we could change it to “only bank details” and use one platform address for all payouts.

---

## 2. Can the user (depositor) lock funds from our website?

**Today:** Locking = calling the contract’s `deposit()` from a **Stellar wallet** (e.g. Freighter). The wallet must sign the transaction. So the “lock” step is not fully on the website yet.

**What we can add:** A “Lock funds” section on the website where the user:

1. Clicks **Connect wallet** (e.g. Freighter popup).
2. Chooses **amount** (e.g. 100 USDC) and **inactivity period** (e.g. 30 days).
3. Clicks **Lock** → the site builds the `deposit(...)` transaction and the wallet pops up to sign it.

So: **yes, the user should select the amount and the inactive period.** Right now they do that inside the wallet when calling `deposit()`. We can move that choice onto the website and only use the wallet to sign.

---

## 3. What are “tokens”?

**Tokens** = the asset you lock in the contract. On Stellar that can be:

- **XLM** (native), or  
- A **Stellar asset** (e.g. **USDC**).

The contract’s `deposit(depositor, token, amount, beneficiary, timeout_ledgers)` takes a `token` (contract address of the asset) and an `amount`. So “100” = 100 units of that token (e.g. 100 USDC). The depositor must hold that token and approve the contract to transfer it before calling `deposit()`.

---

## 4. Whose address is what?

| Address | Who | Where it’s used |
|--------|-----|------------------|
| **Depositor** | You (person locking 100) | Your wallet that calls `deposit()` and `ping()`. Not typed into the “Register beneficiary” form. |
| **Beneficiary (G…)** | Person who should get the payout | On-chain: contract sends tokens here on `claim()`. For “fiat only” we can use our address and send INR to their bank. |
| **Bank details** | Same person (beneficiary) | In “Register beneficiary”: account holder, account number, IFSC, bank. This is where we send the **fiat** (mock today). |

So: the **Stellar address (G…) you enter in “Register beneficiary”** is the **recipient’s** identity on-chain (or ours if we use a custodial flow). It is **not** “my account from which the amount should go.” The amount goes **from your wallet** when you call `deposit()`; the **beneficiary** is who receives (tokens first, then we convert to fiat for them).

---

## 5. Summary: what the depositor should do

1. **On the website:** Register the **beneficiary** (their bank details; Stellar address can be optional if we use a platform address).
2. **Lock funds:** Choose **amount** (e.g. 100 USDC) and **inactive period** (e.g. 30 days). Today: do this by calling `deposit()` from your wallet. Later: do it from the website with “Connect wallet” and “Lock.”
3. **Stay “alive”:** Before the period ends, call `ping()` from **your** wallet. That resets the timer.
4. If you **don’t** ping in time, the agent can `claim()` and we send fiat to the registered bank account (recipient doesn’t need a wallet).

So: **you (depositor) select amount and inactive period; the recipient only needs to receive fiat (bank details), not a Stellar wallet.**
