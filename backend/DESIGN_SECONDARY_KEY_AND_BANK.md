# Design: Secondary key (co-signer) logic + Bank account option

## Part 1: How the secondary key / co-signer works

### 1.1 One key per account (normal Stellar)

When you create a Stellar wallet you get **one keypair**:
- **Public key** (G...) — your account address; you share it to receive funds.
- **Secret key** (S...) — only you have it; you use it to sign transactions. Anyone with this key can move funds.

So by default, **only that one secret key** can sign for your account.

### 1.2 Adding a second key as “co-signer”

On Stellar, an account can have **multiple signers**. Each signer is a **public key + weight** (1–255). The account has thresholds (e.g. low=1, medium=1, high=1). A transaction is valid if the **sum of weights** of the keys that signed meets the threshold.

- **Default:** Your account has one signer: your main public key, weight 1. So only your main key can sign.
- **After adding a co-signer:** You send a **SetOptions** transaction that says: “Add this other public key as a signer with weight 1.” You sign that transaction with your **main** key. After it’s applied, your account has **two** signers (main + secondary), each weight 1. For normal operations, only **one** of them needs to sign. So:
  - **You** can still sign with your main key and move funds.
  - **The holder of the secondary secret key** can also sign and move funds (e.g. sweep the account).

So “co-signer” here means: a **second key that is allowed to sign** for the same account. You don’t give your main key to anyone; you only add the **public** key of the second keypair as a signer.

### 1.3 Who creates and holds the secondary key?

**Creation (on our app):**
1. User goes to **Create secondary key** (/nominee) and fills: their Stellar account (G...), nominee phone, question, answer, nominee address (optional), inactivity days.
2. **Backend** generates a **new keypair** with `Keypair.random()`:
   - **Public key** → we return it to the user (show on page).
   - **Secret key** → we **never** store in plain form. We **encrypt** it with a key derived from the **answer** (KDF + AES-GCM) and store only **ciphertext + nonce + salt**. We also store the **question** (plaintext). We do **not** store the answer.
3. So the **server never has the secondary secret key in the clear**. Only someone who knows the answer can derive the same key and decrypt the secret (we do that **in the browser** on the claim page).

**Making it a co-signer:**
4. User **adds the secondary public key as a signer** to their Stellar account. They do this by signing a **SetOptions** transaction with their **main** key (e.g. via “Add as co-signer with Freighter” on our site or via Stellar Laboratory).
5. After that, the account has two signers: **main key** (user) and **secondary key** (our generated key). Funds stay in the user’s account; nothing is locked in a contract.

**Who can use the secondary key?**
- Only someone who knows the **answer** can recover the secondary **secret** key (decrypt in browser).
- We send the **nominee** an SMS with a **claim link**. When they open it, they see the **question** and enter the **answer**. The browser derives the key from the answer, decrypts the secret, and uses it to **sign the sweep transaction** (move all balances to the nominee’s address). So effectively the **nominee** “holds” the ability to use the secondary key only if they know the answer.

**Summary:**
- **Secondary key** = new keypair we generate; we only show the **public** key; we store the **secret** encrypted with the answer.
- **Co-signer** = that public key is added to the user’s account as a second signer (via SetOptions), so either the user’s main key or the secondary key can sign.
- **Nominee** gets the secret only at claim time, in the browser, by entering the answer; we never see the answer or the decrypted secret.

---

## Part 2: Bank account feature (nominee can receive in bank)

### 2.1 Goal

- When the nominee claims, they can choose: **receive in Stellar wallet** (current sweep) **or receive in bank account**.
- If they choose bank, we use the **Onmeta Off-Ramp API** (the one you used earlier) to send the amount to their bank account (e.g. INR).

### 2.2 Where we get bank details

- **Option A:** When the **depositor** registers the nominee, they can optionally enter the **nominee’s bank details** (account holder name, account number, IFSC, bank name). We store them with the nominee record.
- **Option B:** When the **nominee** opens the claim page, they can choose “Send to bank” and enter (or confirm) bank details there.
- We can support both: depositor can pre-fill bank details; nominee can override or fill at claim time.

### 2.3 Flow when nominee chooses “Send to bank”

1. Nominee opens claim link, enters answer, chooses **“Send to my bank account”**.
2. We still need to **sweep** the depositor’s account (move XLM/crypto). Two options:
   - **2a) Sweep to platform wallet:** We build the sweep transaction so that funds go to a **Stellar address we control** (e.g. a hot wallet configured via env). Then our backend calls **Onmeta Off-Ramp API** with the amount and the nominee’s bank details; Onmeta converts crypto to fiat and sends to the bank. So: sweep → our wallet; then off-ramp → bank.
   - **2b) Sweep to nominee’s Stellar address, then off-ramp:** We sweep to the nominee’s G... address. Then we’d need the nominee (or us with their auth) to trigger the off-ramp. More complex; 2a is simpler if we have a platform wallet.
3. For **2a** we need:
   - Config: **Platform sweep address** (G...) and optionally a **secret key** for that wallet (if we need to sign from it for Onmeta; Onmeta may require sending from a specific address). Actually for off-ramp, typically you tell Onmeta “I have X LM to sell, send INR to this bank.” So we need to have received the XLM first (sweep to our address), then call Onmeta with amount and bank details. So: **sweep destination** = our platform wallet; then **Onmeta create order** with that amount and nominee’s bank details.

### 2.4 “Nominee sends a text to the number”

- **Meaning:** When the nominee sends an SMS to **our Twilio number** (e.g. reply “BANK” or “CLAIM”), we want to trigger or help the bank flow.
- **How:** Use **Twilio inbound SMS webhook**. Configure Twilio so that when someone sends an SMS to our number, Twilio calls our backend (e.g. `POST /webhook/twilio/sms`). We receive sender phone number and message body.
- **Logic:**
  - If body is “BANK” (or similar), look up whether this phone number is a **beneficiary_phone** for any nominee (and optionally whether they have an active claim).
  - We can **reply via Twilio** with: “Open your claim link and choose ‘Send to bank account’” or resend the claim link with a hint: `?mode=bank`.
- So the “text to number” is used to **request the bank option** or to **get the claim link again** with a nudge to use bank. The actual claim (answer + sweep + bank) still happens on the **claim page** when they open the link and choose “Send to bank”.

### 2.5 Implementation outline

1. **DB:** Add to `nominees` (or a linked table): `bank_account_holder`, `bank_account_number`, `bank_ifsc`, `bank_name` (optional).
2. **API:**  
   - Nominee registration: accept optional bank fields; store them.  
   - Claim data: return whether bank details exist and (if we want) a `mode=bank` hint from query param.  
   - Claim submit: accept an option like `destination: "bank"` and (if so) sweep to **platform wallet** and then call **Onmeta** with stored or provided bank details.
3. **Config:**  
   - **PLATFORM_SWEEP_PUBLIC_KEY** (G...): address that receives the swept funds when nominee chooses bank.  
   - Optionally **PLATFORM_SWEEP_SECRET_KEY** if we need to sign from it for Onmeta (depends on Onmeta’s flow).  
   - **ONMETA_BASE_URL**, **ONMETA_API_KEY** (you already have these).
4. **Claim page:**  
   - If bank details exist (or we allow nominee to enter them): show “Receive in Stellar wallet” vs “Receive in bank account”.  
   - If “Receive in bank account”: build sweep tx to platform address (not nominee’s G...), submit; then backend (or a follow-up request) calls Onmeta with amount and bank details.
5. **Inbound SMS (Twilio webhook):**  
   - `POST /webhook/twilio/sms`: parse From + Body; if Body is “BANK” (or “CLAIM”), find nominee by phone; reply with claim link and “Choose Send to bank when you open the link.”

This keeps the **secondary key / co-signer logic** unchanged and adds the **bank option** and **“text to number”** behaviour on top.
