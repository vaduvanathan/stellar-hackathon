# Design: Question–answer + SMS so only beneficiary can unlock the key (team never sees key)

**Goal:** When the user registers the recipient (beneficiary), they give:
- Recipient’s **phone number**
- A **question** only the beneficiary should know
- The **answer** (secret)

The **sweep/co-signer key** is **encrypted with the answer**. We only store the encrypted key. When the account is inactive for X period, we send an **SMS** to the recipient saying they’re a nominee and they must answer the question to get the funds. Only the correct answer can decrypt the key. **Walletsurance never sees the private key.**

---

## 1. Is it technically possible?

**Yes.** Summary:

- Encrypt the private key with a key derived from the answer (e.g. `K = KDF(answer)`), store only **ciphertext**.
- Send SMS with a **link** + the **question** (no key, no answer).
- On claim, beneficiary enters the **answer in the browser**; we derive K and **decrypt in the browser**, then **sign the sweep tx in the browser** and submit. The decrypted key **never** goes to our server.

So the team never has the private key; only the beneficiary (who knows the answer) can ever decrypt it.

---

## 2. Flow (high level)

**Registration (depositor)**

1. Depositor creates or already has a **sweep key** (key that can move funds from their account when they’re inactive).
2. Depositor provides: beneficiary **phone**, **question**, **answer**.
3. We derive **K = KDF(answer)** (e.g. SHA-256 or scrypt of answer).
4. We **encrypt the sweep private key** with K → get **ciphertext**.
5. We store: **ciphertext**, **question** (plaintext so we can show it), **phone**, beneficiary Stellar address, etc. We **do not** store the answer or the plaintext key.
6. Optionally we store a **hash of the question** so we can show “this is the question you set” without storing the answer.

**When account is inactive (agent)**

1. We detect inactivity (e.g. via Horizon) for X days.
2. We send **SMS** to the beneficiary’s phone, e.g.:
   - “You’ve been named as a nominee by [name/link]. To claim, open: [claim URL]. You’ll be asked a question; only your answer can unlock the claim.”
3. SMS can include the **question** in the text, or the claim page loads the question from our backend (we have the question, not the answer).

**Claim (beneficiary)**

1. Beneficiary opens the **claim URL** (from SMS).
2. We show the **question** (from DB). Beneficiary enters the **answer** in the browser.
3. **In the browser only:**  
   - Derive **K = KDF(answer)** (same KDF as at registration).  
   - Decrypt **ciphertext → private key**.  
   - Build the Stellar **sweep transaction** (send all balances to beneficiary).  
   - **Sign** with the private key in the browser (e.g. `stellar-sdk` in JS).  
   - **Submit** the signed transaction to the network (or post only the signed XDR to our backend, which forwards to Horizon).  
4. We **never** send the decrypted key or the answer to our server. At most we receive **signed XDR** to submit.

Result: only someone who knows the answer can decrypt the key; Walletsurance never sees the private key.

---

## 3. Technical pieces

| Piece | How |
|--------|-----|
| **Encrypt key at registration** | K = KDF(answer), e.g. `scrypt(answer)` or `SHA-256(answer)`; AES-GCM encrypt(sweep_private_key, K). Store ciphertext + nonce. |
| **Same KDF on claim** | Claim page (JS) uses same KDF so K is identical when they enter the right answer. |
| **SMS** | Use an SMS gateway (Twilio, AWS SNS, etc.): send link + question (or “you’ll see the question on the page”). |
| **Claim page** | Fetch question (and ciphertext + nonce) from backend; user enters answer; JS derives K, decrypts key, signs sweep tx, submits (or posts signed XDR to backend). Key never leaves the browser. |
| **Sweep key** | Either (a) depositor gives us a key they create for this purpose, or (b) we generate a key pair at registration and show the **public** key to the depositor so they add it as signer to their account; we encrypt and store only the **private** key (encrypted with K). |

---

## 4. Security notes

- **Question strength:** Weak questions (“Mother’s name?”) are guessable. Prefer a **passphrase** only the beneficiary knows (we can still call it “answer” or “secret” in the UI).
- **SMS:** Link and question could be seen by anyone with access to the phone. The real protection is that only the person who knows the **answer** can decrypt the key. So SMS is for **notification + delivery of the question**, not for sending the key.
- **We never see the key:** As long as decryption and signing happen **only in the browser** and we never log or send the decrypted key to the server, the Walletsurance team never has the private key.
- **Optional:** Don’t put the full question in SMS (to avoid shoulder surfing); send only “You’re a nominee. Claim at [link]” and show the question on the claim page after they open the link.

---

## 5. What we store (backend)

- Beneficiary: phone, Stellar address, bank details (for off-ramp).
- For this flow: **question** (text), **ciphertext** (encrypted sweep key), **nonce/iv**, **account_id** (whose funds to sweep), optional **inactivity_days**.
- We do **not** store: the answer, the plaintext private key, or any value that would let us derive K.

---

## 6. Summary

- **Yes, it’s technically possible.**
- User (depositor) gives recipient’s **phone**, a **question**, and the **answer**; we encrypt the sweep key with the answer and store only ciphertext.
- When inactive, we send an **SMS** to the recipient with a link (and optionally the question); they open the link, enter the **answer**; the key is **decrypted and used only in the browser** to sign the sweep; we never see the key.
- So the recipient gets the funds only if they know the answer, and the Walletsurance team never has the private key.

Next step can be to add this flow to the Horizon + inactivity design (when to send the SMS, how the claim URL is generated, and how it ties to “full wallet sweep” vs “contract claim”).
