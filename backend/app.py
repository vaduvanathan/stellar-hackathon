"""
Walletsurance Backend – Flask API and Agent entrypoint.
- REST API for user registration (mock bank details), ping, and status.
- Agent: checks contracts for claimable vaults, mocks claim + Onmeta off-ramp.
"""
import logging
import os
import secrets
import sqlite3
import sys
import traceback
from pathlib import Path

logger = logging.getLogger(__name__)
if not logging.root.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

# Ensure backend directory is on path (for key_encrypt, horizon_client, etc.) when run from project root or Cloud Run
_backend_dir = Path(__file__).resolve().parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Fail fast if critical modules are missing (e.g. Docker image built with wrong context)
try:
    import key_encrypt  # noqa: F401
except ImportError as e:
    raise RuntimeError(
        f"Missing key_encrypt module. Ensure backend/ is the Docker build context: "
        f"docker build -f backend/Dockerfile backend/  (error: {e})"
    ) from e

# Load .env so config (and Twilio, etc.) get env vars when running Flask
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from flask import Flask, g, jsonify, request, render_template

from config import CONTRACT_ID, DEFAULT_TOKEN_ADDRESS, NETWORK_PASSPHRASE, SOROBAN_RPC_URL

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["DATABASE"] = os.environ.get("DATABASE_PATH", "walletsurance.db")

# When set, 500 responses include "traceback" in JSON (for debugging). Always log full traceback server-side.
SHOW_TRACEBACK_IN_RESPONSE = os.environ.get("FLASK_DEBUG", "0") == "1" or os.environ.get("ERROR_DETAIL", "0") == "1"


@app.errorhandler(500)
def handle_500(err):
    """Ensure every 500 returns JSON and we log the exact failure location."""
    tb = "".join(traceback.format_exception(type(err), err, getattr(err, "__traceback__", None)))
    if not tb:
        tb = traceback.format_exc()
    logger.error("500 Internal Server Error: %s\n%s", err, tb)
    payload = {"error": str(err), "ok": False}
    if SHOW_TRACEBACK_IN_RESPONSE:
        payload["traceback"] = tb
    return jsonify(payload), 500


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
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS nominees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                depositor_account_id TEXT NOT NULL,
                sweep_public_key TEXT NOT NULL,
                ciphertext_b64 TEXT NOT NULL,
                nonce_b64 TEXT NOT NULL,
                salt_b64 TEXT NOT NULL,
                question TEXT NOT NULL,
                beneficiary_phone TEXT NOT NULL,
                beneficiary_stellar_address TEXT,
                inactivity_days INTEGER NOT NULL DEFAULT 30,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(depositor_account_id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS nominee_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_token TEXT NOT NULL UNIQUE,
                nominee_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (nominee_id) REFERENCES nominees(id)
            )
            """
        )
        db.commit()
        db.close()


@app.route("/")
def index():
    """Minimal UI: contract status, register beneficiary, mock agent."""
    return render_template("index.html")


@app.route("/nominee")
def nominee_page():
    """Page where user creates / gets the secondary (sweep) key and registers nominee."""
    return render_template("nominee.html")


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


# --- Nominee flow: co-sign key encrypted with question/answer, SMS when inactive ---

@app.route("/api/nominee/register", methods=["POST"])
def nominee_register():
    """
    Register a nominee: generate sweep keypair, encrypt private key with answer, store.
    Body: depositor_account_id, beneficiary_phone, beneficiary_stellar_address (optional),
          question, answer, inactivity_days (optional, default 30).
    Returns: sweep_public_key (user must add this as co-signer to their account).
    """
    try:
        from stellar_sdk import Keypair
        from key_encrypt import encrypt_secret_with_answer
    except ImportError as e:
        return jsonify({"error": f"Missing dependency: {e}"}), 503

    data = request.get_json() or {}
    depositor = (data.get("depositor_account_id") or "").strip()
    phone = (data.get("beneficiary_phone") or "").strip()
    beneficiary_address = (data.get("beneficiary_stellar_address") or "").strip()
    question = (data.get("question") or "").strip()
    answer = (data.get("answer") or "").strip()
    inactivity_days = data.get("inactivity_days", 30)
    if isinstance(inactivity_days, str) and inactivity_days.isdigit():
        inactivity_days = int(inactivity_days)
    else:
        inactivity_days = int(inactivity_days) if inactivity_days else 30

    if not depositor or not phone or not question or not answer:
        return jsonify({"error": "depositor_account_id, beneficiary_phone, question, and answer required"}), 400
    if len(depositor) != 56 or not depositor.startswith("G"):
        return jsonify({"error": "depositor_account_id must be a Stellar public key (G..., 56 chars)"}), 400

    try:
        kp = Keypair.random()
        secret = kp.secret
        public = kp.public_key
    except Exception as e:
        logger.exception("nominee_register: Keypair generation failed")
        return jsonify({"error": f"Keypair generation failed: {e}", "where": "keypair"}), 500

    try:
        ciphertext_b64, nonce_b64, salt_b64 = encrypt_secret_with_answer(secret, answer)
    except Exception as e:
        logger.exception("nominee_register: Encryption failed")
        return jsonify({"error": f"Encryption failed: {e}", "where": "encrypt"}), 500

    db = get_db()
    try:
        db.execute(
            """
            INSERT OR REPLACE INTO nominees
            (depositor_account_id, sweep_public_key, ciphertext_b64, nonce_b64, salt_b64, question, beneficiary_phone, beneficiary_stellar_address, inactivity_days)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (depositor, public, ciphertext_b64, nonce_b64, salt_b64, question, phone, beneficiary_address or None, inactivity_days),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Registration failed (duplicate depositor?)"}), 400
    except sqlite3.Error as e:
        logger.exception("nominee_register: Database error")
        return jsonify({"error": f"Database error: {e}", "where": "database"}), 500

    return jsonify({
        "message": "Nominee registered. You must add the sweep key as a co-signer to your account.",
        "sweep_public_key": public,
        "instruction": "Add this public key as a signer to your Stellar account (e.g. Stellar Laboratory or Freighter). When your account is inactive for the set period, your nominee will receive an SMS and can claim by answering the question.",
    })


@app.route("/claim/<token>")
def claim_page(token):
    """Render claim page for nominee (question + answer form; decrypt and sign in browser)."""
    return render_template("claim.html", claim_token=token)


@app.route("/api/claim/data/<token>", methods=["GET"])
def claim_data(token):
    """Return question, ciphertext, nonce, salt, KDF params, network info, account, and optional platform_sweep_address for bank payout."""
    from config import HORIZON_URL, NETWORK_PASSPHRASE, PLATFORM_SWEEP_PUBLIC_KEY
    from key_encrypt import get_kdf_params
    from horizon_client import get_account

    db = get_db()
    row = db.execute(
        "SELECT n.id, n.question, n.ciphertext_b64, n.nonce_b64, n.salt_b64, n.depositor_account_id, n.beneficiary_stellar_address FROM nominee_claims c JOIN nominees n ON c.nominee_id = n.id WHERE c.claim_token = ?",
        (token.strip(),),
    ).fetchone()
    if not row:
        return jsonify({"error": "Invalid or expired claim link"}), 404

    depositor = row["depositor_account_id"]
    account = get_account(depositor)

    out = {
        "question": row["question"],
        "ciphertext_b64": row["ciphertext_b64"],
        "nonce_b64": row["nonce_b64"],
        "salt_b64": row["salt_b64"],
        "kdf": get_kdf_params(),
        "network_passphrase": NETWORK_PASSPHRASE,
        "horizon_url": HORIZON_URL,
        "depositor_account_id": depositor,
        "beneficiary_stellar_address": (row["beneficiary_stellar_address"] or "").strip(),
        "account": account,
    }
    if PLATFORM_SWEEP_PUBLIC_KEY:
        out["platform_sweep_address"] = PLATFORM_SWEEP_PUBLIC_KEY
    return jsonify(out)


@app.route("/api/claim/submit", methods=["POST"])
def claim_submit():
    """Submit signed classic transaction (sweep or add-signer). Body: signed_envelope_xdr."""
    from horizon_client import submit_transaction

    data = request.get_json() or {}
    xdr = (data.get("signed_envelope_xdr") or "").strip()
    if not xdr:
        return jsonify({"error": "signed_envelope_xdr required"}), 400

    result = submit_transaction(xdr)
    if "hash" in result:
        return jsonify({"hash": result["hash"], "status": "success"})
    return jsonify({"error": result.get("detail", result.get("error", "Submit failed"))}), 400


@app.route("/api/claim/offramp", methods=["POST"])
def claim_offramp():
    """
    Mock bank payout: accept claim_token, bank details, amount_xlm.
    Mimics the step where crypto would be converted to INR and sent to bank (no real API yet).
    """
    data = request.get_json() or {}
    token = (data.get("claim_token") or "").strip()
    account_holder = (data.get("bank_account_holder") or "").strip()
    account_number = (data.get("bank_account_number") or "").strip()
    ifsc = (data.get("bank_ifsc") or "").strip()
    bank_name = (data.get("bank_name") or "").strip()
    amount_xlm = data.get("amount_xlm", "0")
    try:
        amount_xlm = str(amount_xlm).strip() or "0"
    except Exception:
        amount_xlm = "0"

    if not token:
        return jsonify({"error": "claim_token required"}), 400
    if not account_holder or not account_number or not ifsc:
        return jsonify({"error": "bank_account_holder, bank_account_number, and bank_ifsc required"}), 400

    db = get_db()
    row = db.execute(
        "SELECT 1 FROM nominee_claims c JOIN nominees n ON c.nominee_id = n.id WHERE c.claim_token = ?",
        (token,),
    ).fetchone()
    if not row:
        return jsonify({"error": "Invalid or expired claim token"}), 404

    # Mock: no real Onmeta/crypto-to-INR API yet
    from config import RATE_XLM_TO_INR
    try:
        amount_fiat = float(amount_xlm) * RATE_XLM_TO_INR
    except Exception:
        amount_fiat = 0.0
    mask = account_number[-4:] if len(account_number) >= 4 else "****"
    return jsonify({
        "status": "success",
        "mock": True,
        "message": "Bank payout requested (mock). In production, crypto would be converted to INR and sent to your bank.",
        "order_id": f"mock-offramp-{secrets.token_hex(6)}",
        "bank_account_holder": account_holder,
        "bank_account_masked": f"****{mask}",
        "bank_ifsc": ifsc,
        "bank_name": bank_name or None,
        "amount_xlm": amount_xlm,
        "amount_inr_mock": round(amount_fiat, 2),
    })


def _envelope_to_xdr_base64(envelope):
    """Get base64 XDR string from TransactionEnvelope (works across stellar_sdk versions)."""
    if hasattr(envelope, "to_xdr") and callable(getattr(envelope, "to_xdr")):
        return envelope.to_xdr()
    import base64
    xdr_obj = envelope.to_xdr_object()
    try:
        from xdrlib3 import Packer
    except ImportError:
        from xdrlib import Packer
    p = Packer()
    xdr_obj.pack(p)
    return base64.b64encode(p.get_buffer()).decode("ascii")


@app.route("/api/build-add-signer", methods=["POST"])
def build_add_signer():
    """
    Build an unsigned 'add signer' (SetOptions) transaction for classic Stellar.
    Body: account_public_key (your main account G...), signer_public_key (the secondary key to add).
    Returns transaction_xdr for the user to sign with their wallet (e.g. Freighter) and submit via /api/claim/submit.
    """
    try:
        from config import HORIZON_URL, NETWORK_PASSPHRASE
        from stellar_sdk import Server, Signer, TransactionBuilder
        from stellar_sdk.transaction_envelope import TransactionEnvelope
    except ImportError as e:
        return jsonify({"error": f"Missing dependency: {e}"}), 503

    data = request.get_json() or {}
    account_public_key = (data.get("account_public_key") or "").strip()
    signer_public_key = (data.get("signer_public_key") or "").strip()
    if not account_public_key or not signer_public_key:
        return jsonify({"error": "account_public_key and signer_public_key required"}), 400
    if len(account_public_key) != 56 or not account_public_key.startswith("G"):
        return jsonify({"error": "account_public_key must be a Stellar public key (G..., 56 chars)"}), 400
    if len(signer_public_key) != 56 or not signer_public_key.startswith("G"):
        return jsonify({"error": "signer_public_key must be a Stellar public key (G..., 56 chars)"}), 400

    try:
        server = Server(HORIZON_URL)
        source = server.load_account(account_public_key)
    except Exception as e:
        logger.exception("build_add_signer: load_account failed for %s", account_public_key[:8])
        payload = {"error": f"Account not found or load failed: {e}", "where": "load_account"}
        if SHOW_TRACEBACK_IN_RESPONSE:
            payload["traceback"] = traceback.format_exc()
        return jsonify(payload), 404

    try:
        secondary_signer = Signer.ed25519_public_key(signer_public_key, 1)
        tx = (
            TransactionBuilder(
                source_account=source,
                network_passphrase=NETWORK_PASSPHRASE,
                base_fee=100,
            )
            .append_set_options_op(signer=secondary_signer)
            .set_timeout(180)
            .build()
        )
        envelope = TransactionEnvelope(transaction=tx, network_passphrase=NETWORK_PASSPHRASE)
        xdr_b64 = _envelope_to_xdr_base64(envelope)
        return jsonify({"transaction_xdr": xdr_b64})
    except Exception as e:
        logger.exception("build_add_signer: build/serialize failed")
        payload = {"error": f"Build failed: {e}", "where": "build_or_serialize"}
        if SHOW_TRACEBACK_IN_RESPONSE:
            payload["traceback"] = traceback.format_exc()
        return jsonify(payload), 500


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


@app.route("/api/agent/check-nominees", methods=["GET", "POST"])
def agent_check_nominees():
    """
    Check Horizon for nominee inactivity. If depositor has had no activity for inactivity_days,
    create a claim token and send SMS to beneficiary. Call from Cloud Scheduler.
    """
    from datetime import datetime, timezone, timedelta
    from horizon_client import get_last_activity
    from sms_client import send_nominee_claim_sms

    db = get_db()
    nominees = db.execute(
        "SELECT id, depositor_account_id, question, beneficiary_phone, inactivity_days FROM nominees"
    ).fetchall()
    if not nominees:
        return jsonify({"message": "No nominees registered.", "sms_sent": 0}), 200

    now = datetime.now(timezone.utc)
    sent = 0
    for n in nominees:
        last = get_last_activity(n["depositor_account_id"])
        if not last:
            continue
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        except Exception:
            continue
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        threshold = now - timedelta(days=int(n["inactivity_days"] or 30))
        if last_dt > threshold:
            continue
        existing = db.execute(
            "SELECT 1 FROM nominee_claims WHERE nominee_id = ?", (n["id"],)
        ).fetchone()
        if existing:
            continue
        token = secrets.token_urlsafe(24)
        db.execute(
            "INSERT INTO nominee_claims (claim_token, nominee_id) VALUES (?, ?)",
            (token, n["id"]),
        )
        db.commit()
        if send_nominee_claim_sms(n["beneficiary_phone"], token, n["question"]):
            sent += 1

    return jsonify({"message": f"Checked {len(nominees)} nominees.", "sms_sent": sent}), 200


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


# Ensure DB tables exist when app is loaded (e.g. by gunicorn on Cloud Run); otherwise nominee/register returns 500
with app.app_context():
    init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
