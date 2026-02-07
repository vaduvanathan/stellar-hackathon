# How to view the Walletsurance codebase

## On GitHub (browser)

- **Repo:** https://github.com/vaduvanathan/stellar-hackathon  
- Open the link to see files, folders, and history in the browser.
- **Main folders:**
  - **`walletsurance/`** – Rust Soroban contract (e.g. `contracts/inheritance/src/lib.rs`)
  - **`backend/`** – Python Flask app (`app.py`), templates (`templates/index.html`), config, deploy script
  - **`scripts/`** – Shell deploy script

## Locally in Cursor / VS Code

1. **If the project is already open**  
   - You’re in the codebase. Use the file explorer (left sidebar) or **Ctrl+P** / **Cmd+P** to open files.

2. **If you need to open it again**
   - **File → Open Folder** (or **File → Open** on Mac).
   - Choose the folder that contains the repo, e.g. `stellar-hackthon` or the path where you cloned it.

3. **If you’re on a different machine and want a fresh copy**
   ```bash
   git clone https://github.com/vaduvanathan/stellar-hackathon.git
   cd stellar-hackathon
   ```
   Then in Cursor: **File → Open Folder** → select the `stellar-hackathon` folder.

## Quick file map

| What you want to see        | File or folder |
|-----------------------------|----------------|
| Smart contract (Rust)       | `walletsurance/contracts/inheritance/src/lib.rs` |
| Flask API + routes         | `backend/app.py` |
| UI (single page)           | `backend/templates/index.html` |
| Contract status from chain | `backend/soroban_client.py` |
| Deploy contract (Python)    | `backend/deploy_contract.py` |
| Config (RPC, contract ID) | `backend/config.py` |
