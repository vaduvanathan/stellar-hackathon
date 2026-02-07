"""
Nominee flow: derive key from answer (KDF), encrypt sweep secret key.
Decryption happens in the browser; we only encrypt and store ciphertext here.
KDF + AES-GCM so the same can be done in JS (Web Crypto API).
"""
import base64
import hashlib
import os
import secrets
from typing import Tuple

# PBKDF2 params (must match claim page JS)
KDF_ITERATIONS = 100_000
KDF_KEY_LENGTH = 32  # AES-256
SALT_LENGTH = 16
NONCE_LENGTH = 12


def _derive_key(answer: str, salt: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256. Same logic must run in browser."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        answer.encode("utf-8"),
        salt,
        KDF_ITERATIONS,
        dklen=KDF_KEY_LENGTH,
    )


def encrypt_secret_with_answer(secret_key: str, answer: str) -> Tuple[str, str, str]:
    """
    Encrypt a Stellar secret key (S...) with the answer.
    Returns (ciphertext_b64, nonce_b64, salt_b64) for storage.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise RuntimeError("cryptography package required: pip install cryptography")

    salt = secrets.token_bytes(SALT_LENGTH)
    nonce = secrets.token_bytes(NONCE_LENGTH)
    key = _derive_key(answer, salt)
    aes = AESGCM(key)
    plaintext = secret_key.encode("utf-8")
    ciphertext = aes.encrypt(nonce, plaintext, None)
    return (
        base64.standard_b64encode(ciphertext).decode("ascii"),
        base64.standard_b64encode(nonce).decode("ascii"),
        base64.standard_b64encode(salt).decode("ascii"),
    )


def get_kdf_params() -> dict:
    """Return KDF params for the claim page so JS can derive the same key."""
    return {
        "iterations": KDF_ITERATIONS,
        "keyLength": KDF_KEY_LENGTH,
        "saltLength": SALT_LENGTH,
        "nonceLength": NONCE_LENGTH,
    }
