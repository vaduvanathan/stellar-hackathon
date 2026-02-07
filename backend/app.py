"""
Walletsurance Backend – Flask API and Agent entrypoint.
- REST API for user registration (mock bank details), ping, and status.
- Agent: checks contracts for claimable vaults, mocks claim + Onmeta off-ramp.
"""
import os
import sqlite3
from pathlib import Path

from flask import Flask, g, jsonify, request, render_template

from config import CONTRACT_ID, DEFAULT_TOKEN_ADDRESS, NETWORK_PASSPHRASE, SOROBAN_RPC_URL

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["DATABASE"] = os.environ.get("DATABASE_PATH", "walletsurance.db")


def get_db():
    """Per-request DB connection (thread-safe)."""
    if "db" not in g:
        db_path = app.config["DATABASE"]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db_path = app.config["DATABASE"]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(db_path)
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS beneficiaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stellar_address TEXT NOT NULL UNIQUE,
                contract_id TEXT,
                bank_account_holder TEXT,
                bank_account_number TEXT,
                bank_ifsc TEXT,
                bank_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id TEXT,
                beneficiary_address TEXT,
                amount_mocked TEXT,
                offramp_mock_status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.commit()
        try:
            db.execute("ALTER TABLE beneficiaries ADD COLUMN timeout_days INTEGER")
            db.commit()
        except sqlite3.OperationalError:
            pass
        db.close()


@app.route("/")
def index():
    """Minimal UI: contract status, register beneficiary, mock agent."""
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "walletsurance"})


@app.route("/api/lock-config", methods=["GET"])
def lock_config():
    """Public config for Lock funds: contract ID, RPC URL, network, default token (if set)."""
    return jsonify({
        "contract_id": CONTRACT_ID,
        "rpc_url": SOROBAN_RPC_URL,
        "network_passphrase": NETWORK_PASSPHRASE,
        "default_token_address": DEFAULT_TOKEN_ADDRESS or None,
    })


@app.route("/api/build-deposit", methods=["POST"])
def build_deposit():
    """
    Build an unsigned deposit() transaction. Returns transaction_xdr for the client to sign (e.g. Freighter).
    Body: depositor_public_key, beneficiary_address, amount, timeout_ledgers, token_address (optional).
    """
    try:
        from build_deposit import build_deposit_xdr
    except ImportError:
        return jsonify({"error": "build_deposit not available"}), 503

    data = request.get_json() or {}
    depositor = (data.get("depositor_public_key") or "").strip()
    beneficiary = (data.get("beneficiary_address") or "").strip()
    amount = data.get("amount")
    timeout_ledgers = data.get("timeout_ledgers")
    token_address = (data.get("token_address") or "").strip() or None

    if not depositor or not beneficiary:
        return jsonify({"error": "depositor_public_key and beneficiary_address required"}), 400
    if amount is None:
        return jsonify({"error": "amount required"}), 400
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return jsonify({"error": "amount must be an integer"}), 400
    if timeout_ledgers is None:
        return jsonify({"error": "timeout_ledgers required"}), 400
    try:
        timeout_ledgers = int(timeout_ledgers)
    except (TypeError, ValueError):
        return jsonify({"error": "timeout_ledgers must be an integer"}), 400

    xdr, err = build_deposit_xdr(depositor, beneficiary, amount, timeout_ledgers, token_address)
    if err:
        return jsonify({"error": err}), 400
    return jsonify({"transaction_xdr": xdr})


@app.route("/api/submit", methods=["POST"])
def submit_transaction():
    """Submit a signed transaction envelope (XDR base64). Body: signed_envelope_xdr."""
    try:
        from build_deposit import submit_signed_envelope
    except ImportError:
        return jsonify({"error": "submit not available"}), 503

    data = request.get_json() or {}
    xdr = (data.get("signed_envelope_xdr") or "").strip()
    if not xdr:
        return jsonify({"error": "signed_envelope_xdr required"}), 400

    result, err = submit_signed_envelope(xdr)
    if err:
        return jsonify({"error": err}), 400
    return jsonify(result)


@app.route("/api/contract/status", methods=["GET"])
def contract_status():
    """
    Read contract state from chain (can_claim, beneficiary).
    Requires CONTRACT_ID and SOROBAN_RPC_URL. Returns 503 if not configured or RPC fails.
    """
    try:
        from soroban_client import get_contract_status, get_network_info
    except ImportError:
        return jsonify({"error": "Soroban client not available"}), 503

    status = get_contract_status()
    if status is None:
        info = get_network_info()
        return (
            jsonify(
                {
                    "error": "Contract status unavailable",
                    "hint": "Set CONTRACT_ID and SOROBAN_RPC_URL (e.g. Testnet)",
                    **info,
                }
            ),
            503,
        )
    return jsonify(status)


@app.route("/api/beneficiary", methods=["POST"])
def register_beneficiary():
    """Register or update mock bank details for a Stellar address (beneficiary)."""
    data = request.get_json() or {}
    stellar_address = (data.get("stellar_address") or "").strip()
    contract_id = (data.get("contract_id") or "").strip()
    bank_account_holder = (data.get("bank_account_holder") or "").strip()
    bank_account_number = (data.get("bank_account_number") or "").strip()
    bank_ifsc = (data.get("bank_ifsc") or "").strip()
    bank_name = (data.get("bank_name") or "").strip()
    timeout_days = data.get("timeout_days")
    if timeout_days is not None:
        try:
            timeout_days = int(timeout_days) if timeout_days != "" else None
        except (TypeError, ValueError):
            timeout_days = None

    if not stellar_address:
        return jsonify({"error": "stellar_address required"}), 400
    if not stellar_address.startswith("G") or len(stellar_address) < 55:
        return jsonify({"error": "Stellar address must start with G and be 56 characters (e.g. GAGONWX...)"}), 400

    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO beneficiaries (
                stellar_address, contract_id, bank_account_holder,
                bank_account_number, bank_ifsc, bank_name, timeout_days
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stellar_address) DO UPDATE SET
                contract_id=excluded.contract_id,
                bank_account_holder=excluded.bank_account_holder,
                bank_account_number=excluded.bank_account_number,
                bank_ifsc=excluded.bank_ifsc,
                bank_name=excluded.bank_name,
                timeout_days=excluded.timeout_days
            """,
            (
                stellar_address,
                contract_id or None,
                bank_account_holder or None,
                bank_account_number or None,
                bank_ifsc or None,
                bank_name or None,
                timeout_days,
            ),
        )
        db.commit()
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(
        {
            "stellar_address": stellar_address,
            "contract_id": contract_id or None,
            "message": "Beneficiary registered (mock bank details stored)",
        }
    )


@app.route("/api/beneficiary/<stellar_address>", methods=["GET"])
def get_beneficiary(stellar_address):
    """Get mock bank details for a beneficiary (masked)."""
    db = get_db()
    row = db.execute(
        "SELECT stellar_address, contract_id, bank_account_holder, bank_name FROM beneficiaries WHERE stellar_address = ?",
        (stellar_address.strip(),),
    ).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(
        {
            "stellar_address": row["stellar_address"],
            "contract_id": row["contract_id"],
            "bank_account_holder": row["bank_account_holder"],
            "bank_name": row["bank_name"],
        }
    )


@app.route("/api/agent/check", methods=["GET", "POST"])
def agent_check():
    """
    Agent step 1: Check chain for claimable vault; if so, run mock claim + off-ramp.
    Call this from Cloud Scheduler (e.g. every hour). Uses CONTRACT_ID from env.
    """
    try:
        from soroban_client import get_contract_status
        from config import CONTRACT_ID
    except ImportError:
        return jsonify({"error": "Soroban client not available"}), 503

    if not CONTRACT_ID:
        return jsonify({"message": "No CONTRACT_ID set; nothing to check.", "claim_mock": "skipped"}), 200

    status = get_contract_status()
    if not status or not status.get("can_claim"):
        return jsonify({
            "message": "Contract not claimable (no deposit or timeout not reached).",
            "can_claim": status.get("can_claim") if status else None,
            "claim_mock": "skipped",
        }), 200

    beneficiary_address = (status.get("beneficiary_address") or "").strip()
    db = get_db()
    bank_info = None
    onmeta_order = None
    if beneficiary_address:
        row = db.execute(
            "SELECT stellar_address, bank_account_holder, bank_name, bank_account_number, bank_ifsc FROM beneficiaries WHERE stellar_address = ?",
            (beneficiary_address,),
        ).fetchone()
        if row:
            bank_info = dict(row)
            try:
                from onmeta_client import create_offramp_order
                onmeta_order = create_offramp_order(
                    fiat_amount=0.0,
                    account_number=row["bank_account_number"] or "MOCK_ACC",
                    account_name=row["bank_account_holder"] or "Beneficiary",
                    ifsc=row["bank_ifsc"] or "MOCK0001",
                )
            except Exception:
                onmeta_order = {"status": "mock_error"}

    try:
        db.execute(
            """
            INSERT INTO agent_runs (contract_id, beneficiary_address, amount_mocked, offramp_mock_status)
            VALUES (?, ?, ?, ?)
            """,
            (CONTRACT_ID, beneficiary_address or None, "0", "mocked_success"),
        )
        db.commit()
    except sqlite3.Error:
        pass

    return jsonify({
        "message": "Claimable: ran mock claim + off-ramp (real claim would need AGENT_SECRET_KEY).",
        "can_claim": True,
        "beneficiary_address": beneficiary_address or None,
        "bank_info_stored": bank_info is not None,
        "claim_mock": "success",
        "offramp_mock": "Onmeta Off-Ramp API mocked – fiat wire simulated",
        "onmeta_order": onmeta_order,
    }), 200


@app.route("/api/agent/run", methods=["POST"])
def agent_run():
    """
    Mock agent run: check claimable vaults, mock claim and mock Onmeta off-ramp.
    In production this would:
    - Query Soroban for contracts where can_claim() is true
    - Submit claim() as the agent
    - Call Onmeta Off-Ramp API (here: mocked)
    """
    # Mock: simulate one claim and one off-ramp
    db = get_db()
    contract_id = (request.get_json() or {}).get("contract_id", "").strip()
    beneficiary_address = (request.get_json() or {}).get("beneficiary_address", "").strip()
    amount_mocked = (request.get_json() or {}).get("amount_mocked", "0")

    if not contract_id and not beneficiary_address:
        return jsonify(
            {
                "message": "Agent run completed (mocked). No contract_id/beneficiary in request; nothing to claim.",
                "claim_mock": "skipped",
                "offramp_mock": "Onmeta Off-Ramp API mocked – fiat wire simulated",
            }
        )

    try:
        db.execute(
            """
            INSERT INTO agent_runs (contract_id, beneficiary_address, amount_mocked, offramp_mock_status)
            VALUES (?, ?, ?, ?)
            """,
            (contract_id or None, beneficiary_address or None, amount_mocked, "mocked_success"),
        )
        db.commit()
    except sqlite3.Error:
        pass

    return jsonify(
        {
            "message": "Agent run completed (mocked)",
            "claim_mock": "success",
            "offramp_mock": "Onmeta Off-Ramp API mocked – fiat wire simulated",
        }
    )


@app.route("/api/mock-onmeta/create-order", methods=["POST"])
def mock_onmeta_create_order():
    """
    Mock Onmeta Off-Ramp create order. Same request body as Onmeta API
    (https://documenter.getpostman.com/view/20857383/UzXNTwpM).
    Use for testing; set ONMETA_BASE_URL + ONMETA_API_KEY for real.
    """
    data = request.get_json() or {}
    bank = data.get("bankDetails") or {}
    try:
        from onmeta_client import create_offramp_order
        order = create_offramp_order(
            sell_token_symbol=data.get("sellTokenSymbol", "XLM"),
            chain_id=int(data.get("chainId", 1)),
            fiat_currency=(data.get("fiatCurrency") or "inr").lower(),
            fiat_amount=float(data.get("fiatAmount", 0)),
            payment_mode=data.get("paymentMode", "INR_IMPS"),
            account_number=bank.get("accountNumber", "MOCK"),
            account_name=bank.get("accountName", "Mock Holder"),
            ifsc=bank.get("ifsc", "MOCK0001"),
            metadata=data.get("metaData"),
        )
        return jsonify(order), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/agent/runs", methods=["GET"])
def agent_runs_list():
    """List recent mock agent runs."""
    db = get_db()
    rows = db.execute(
        "SELECT contract_id, beneficiary_address, amount_mocked, offramp_mock_status, created_at FROM agent_runs ORDER BY id DESC LIMIT 20"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
