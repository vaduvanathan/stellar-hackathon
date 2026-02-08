"""
Send SMS (Twilio). If Twilio not configured, log only (mock).
"""
import logging
import secrets
from config import CLAIM_BASE_URL, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER

LOG = logging.getLogger(__name__)


def send_nominee_claim_sms(phone: str, claim_token: str, question_preview: str = "") -> bool:
    """
    Send SMS to beneficiary with claim link. Returns True if sent (or mocked).
    """
    base = (CLAIM_BASE_URL or "https://stellar-hackathon-242775953468.asia-south1.run.app").rstrip("/")
    link = f"{base}/claim/{claim_token}"
    body = (
        f"You've been named as a nominee on SUPERNOVA. "
        f"To claim, open: {link} You'll be asked a question; your answer unlocks the claim."
    )
    if question_preview:
        body = body + f" Question: {question_preview[:80]}..."

    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_FROM_NUMBER:
        LOG.warning("SMS mock (Twilio not configured): to=%s body=%s", phone, body[:100])
        return True

    try:
        import requests
        r = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json",
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            data={"To": phone, "From": TWILIO_FROM_NUMBER, "Body": body},
            timeout=10,
        )
        if r.status_code in (200, 201):
            return True
        LOG.error("Twilio error: %s %s", r.status_code, r.text)
        return False
    except Exception as e:
        LOG.exception("SMS send failed: %s", e)
        return False


