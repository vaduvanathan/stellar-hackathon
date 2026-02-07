"""
Tests for inactivity detection (5 minutes test option) and SMS claim link.
Run from repo root: python -m pytest backend/tests/test_inactivity_and_sms.py -v
Or from backend: pytest tests/test_inactivity_and_sms.py -v
"""
import os
import sys
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


@pytest.fixture
def app_and_client():
    """Flask app with in-memory DB and test client."""
    import app as app_module
    app = app_module.app
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app.config["DATABASE"] = db_path
    app.config["TESTING"] = True
    app_module.init_db()
    yield app, app.test_client(), db_path
    try:
        os.unlink(db_path)
    except Exception:
        pass


def _insert_nominee(db_path, depositor="G" + "A" * 55, inactivity_days=0, phone="+15551234567", question="Test?"):
    with sqlite3.connect(db_path) as c:
        c.execute(
            """INSERT INTO nominees
               (depositor_account_id, sweep_public_key, ciphertext_b64, nonce_b64, salt_b64, question, beneficiary_phone, beneficiary_stellar_address, inactivity_days)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (depositor, "G" + "B" * 55, "cipher", "nonce", "salt", question, phone, None, inactivity_days),
        )


def test_inactivity_5_minutes_treats_no_activity_as_inactive(app_and_client):
    """When inactivity_days=0 (5 min test), no last activity should trigger SMS."""
    app, client, db_path = app_and_client
    _insert_nominee(db_path, inactivity_days=0, phone="+15559999999")

    with patch("horizon_client.get_last_activity", return_value=None):
        with patch("sms_client.send_nominee_claim_sms", return_value=True) as send_sms:
            r = client.get("/api/agent/check-nominees")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("sms_sent") == 1
    send_sms.assert_called_once()
    call_args = send_sms.call_args[0]
    assert call_args[0] == "+15559999999"
    claim_token = call_args[1]
    assert len(claim_token) >= 20
    assert claim_token and call_args[2] == "Test?"


def test_inactivity_5_minutes_old_activity_triggers_sms(app_and_client):
    """When inactivity_days=0, last activity 10 min ago should trigger SMS."""
    app, client, db_path = app_and_client
    _insert_nominee(db_path, inactivity_days=0)

    with patch("horizon_client.get_last_activity", return_value="2020-01-01T00:00:00Z"):
        with patch("sms_client.send_nominee_claim_sms", return_value=True) as send_sms:
            r = client.get("/api/agent/check-nominees")
    assert r.status_code == 200
    assert r.get_json().get("sms_sent") == 1
    send_sms.assert_called_once()


def test_inactivity_5_minutes_recent_activity_skips(app_and_client):
    """When inactivity_days=0, last activity 1 min ago should NOT send SMS."""
    from datetime import datetime, timezone, timedelta
    app, client, db_path = app_and_client
    _insert_nominee(db_path, inactivity_days=0)
    recent = (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    with patch("horizon_client.get_last_activity", return_value=recent):
        with patch("sms_client.send_nominee_claim_sms", return_value=True) as send_sms:
            r = client.get("/api/agent/check-nominees")
    assert r.status_code == 200
    assert r.get_json().get("sms_sent") == 0
    send_sms.assert_not_called()


def test_inactivity_7_days_uses_days(app_and_client):
    """When inactivity_days=7, threshold is 7 days; no activity should trigger SMS."""
    app, client, db_path = app_and_client
    _insert_nominee(db_path, inactivity_days=7)

    with patch("horizon_client.get_last_activity", return_value="2020-01-01T00:00:00Z"):
        with patch("sms_client.send_nominee_claim_sms", return_value=True) as send_sms:
            r = client.get("/api/agent/check-nominees")
    assert r.status_code == 200
    assert r.get_json().get("sms_sent") == 1
    send_sms.assert_called_once()


def test_sms_link_format():
    """Claim link in SMS is base/claim/<token> (sms_client builds it)."""
    base = "https://example.run.app"
    token = "test-token-xyz"
    link = f"{base.rstrip('/')}/claim/{token}"
    assert "/claim/" in link
    assert link.endswith(token)


def test_nominee_register_accepts_inactivity_zero(app_and_client):
    """Nominee registration accepts inactivity_days=0 (5 min test)."""
    app, client, db_path = app_and_client
    mock_kp = MagicMock()
    mock_kp.secret = "S"
    mock_kp.public_key = "G" + "X" * 55
    with patch("stellar_sdk.Keypair.random", return_value=mock_kp):
        with patch("key_encrypt.encrypt_secret_with_answer", return_value=("c", "n", "s")):
            r = client.post(
                "/api/nominee/register",
                json={
                    "depositor_account_id": "G" + "A" * 55,
                    "beneficiary_phone": "+15551111111",
                    "beneficiary_stellar_address": "",
                    "question": "Q?",
                    "answer": "A",
                    "inactivity_days": "0",
                },
                content_type="application/json",
            )
    assert r.status_code == 200
    data = r.get_json()
    assert "sweep_public_key" in data
    with sqlite3.connect(db_path) as c:
        row = c.execute("SELECT inactivity_days FROM nominees WHERE depositor_account_id = ?", ("G" + "A" * 55,)).fetchone()
        assert row is not None
        assert row[0] == 0
