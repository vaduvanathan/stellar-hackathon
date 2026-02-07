# Deploy without typing your secret key in the terminal

Use the **Python deploy script** and put your secret key in a `.env` file. You never type it in the terminal.

## 1. Create `.env` in the backend folder

From the `stellar-hackthon` directory:

```bash
cd backend
cp .env.example .env
```

Open `.env` in your editor and set your secret key on the line that says `STELLAR_SECRET_KEY=...`:

```
STELLAR_SECRET_KEY=SDZ6S2SU4CIGX3F35MIKISYY7DEGA3Y5UA6GRCNKC76VNLQJXDA33P54
```

Save the file. (`.env` is in `.gitignore` and will not be committed.)

## 2. Build the contract (if you haven’t already)

From `stellar-hackthon`:

```bash
cd walletsurance
stellar contract build
cd ..
```

## 3. Deploy

From `stellar-hackthon`:

```bash
cd backend
source .venv/bin/activate
python deploy_contract.py
```

The script reads the key from `.env`, uploads the WASM, creates the contract, and prints the **contract ID** (`C...`).

## 4. Use the contract ID

Add the printed contract ID to `.env`:

```
CONTRACT_ID=C...
```

Then run the backend:

```bash
python app.py
```

Open `http://localhost:8080/api/contract/status` to see contract state from chain.

---

**Optional (CLI method):** If you prefer the Stellar CLI, run `stellar keys add default --secret-key` and paste the key when prompted, then run `./scripts/deploy_inheritance.sh`.
