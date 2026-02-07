# Current errors and gaps (nominee / add-signer flow)

## 1. **Open Stellar Lab link is wrong on click**
- **What:** The "Open Stellar Lab → Build transaction" link has `href="https://lab.stellar.org/transaction/build"` in the HTML (correct – new Stellar Lab, transaction build).
- **Bug:** The click handler overwrites it with `https://laboratory.stellar.org/#account-viewer?network=test` (old lab, account viewer). So after one click the link points to the old lab; and that old URL can land on the lab home page depending on hash routing.
- **Fix:** Remove the click handler so the link always goes to `lab.stellar.org/transaction/build`, or change the handler to only set `lab.stellar.org/transaction/build` (and optional account param if the new lab supports it).

## 2. **"Build & sign here (Freighter)" button does nothing**
- **What:** The button exists in the UI but has **no click handler**.
- **Expected:** On click: build a Set Options transaction (add signer = sweep public key, weight 1) with Stellar JS SDK, send to Freighter for signing, then POST signed XDR to `/api/claim/submit`.
- **Fix:** Add JavaScript: wait for StellarSdk (and Freighter), load account from Horizon, `TransactionBuilder` + `Operation.setOptions({ signer: { ed25519PublicKey, weight: 1 } })`, `build()` → `toEnvelope().toXDR('base64')`, Freighter sign, then `fetch('/api/claim/submit', { body: { signed_envelope_xdr } })`.

## 3. **Already fixed (for reference)**
- Backend `/api/build-add-signer` was returning 500 (Python SDK version/serialization). We now return a "refresh the page" message and build the tx in the frontend instead.
- "Stellar SDK not loaded" with different wallet: we had added wait + dynamic load; that code was removed when we went manual-only. It will be needed again if we re-enable "Build & sign here (Freighter)".
- Nominee page cache: `/nominee` sends `Cache-Control: no-cache` so new deploys are visible after refresh.

---

**Next:** Fix (1) Open Lab link and (2) add click handler for "Build & sign here (Freighter)" with SDK build + Freighter sign + submit.
