import base64
import hmac
import json
import re
import secrets
import time
from io import BytesIO

import pyotp
import qrcode
from cryptography.fernet import Fernet
from flask import current_app
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)


def _fernet() -> Fernet:
    """Return the configured Fernet encryption instance."""
    key = current_app.config.get("MFA_ENCRYPTION_KEY")

    if not key:
        raise RuntimeError(
            "MFA_ENCRYPTION_KEY is not configured"
        )

    if isinstance(key, str):
        key = key.encode("ascii")

    return Fernet(key)


def encrypt_totp_secret(secret: str) -> str:
    """Encrypt a TOTP seed before storing it in the database."""
    encrypted = _fernet().encrypt(secret.encode("utf-8"))
    return encrypted.decode("ascii")


def decrypt_totp_secret(encrypted_secret: str) -> str:
    """Decrypt a saved TOTP seed for verification."""
    decrypted = _fernet().decrypt(
        encrypted_secret.encode("ascii")
    )
    return decrypted.decode("utf-8")


def make_qr_data_uri(provisioning_uri: str) -> str:
    """Generate a QR code locally rather than sending the secret
    to a third-party QR code service.
    """
    image = qrcode.make(provisioning_uri)

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    encoded = base64.b64encode(
        buffer.getvalue()
    ).decode("ascii")

    return f"data:image/png;base64,{encoded}"


def generate_recovery_codes(
    count: int = 10,
) -> tuple[list[str], str]:
    """Generate one-time recovery codes and password hashes."""
    codes = [
        secrets.token_hex(8).upper()
        for _ in range(count)
    ]

    hashes = [
        generate_password_hash(code)
        for code in codes
    ]

    return codes, json.dumps(hashes)


def matching_totp_step(
    secret: str,
    submitted_code: str,
    last_used_step: int | None = None,
) -> int | None:
    """Return the matching TOTP time step, if valid and unused."""
    code = (submitted_code or "").strip()

    if not re.fullmatch(r"\d{6}", code):
        return None

    totp = pyotp.TOTP(secret)
    current_step = int(time.time()) // totp.interval

    # Allow the current time step and one step on either side
    # to accommodate small clock differences.
    for step in range(
        current_step - 1,
        current_step + 2,
    ):
        if (
            last_used_step is not None
            and step <= last_used_step
        ):
            continue

        expected = totp.at(step * totp.interval)

        if hmac.compare_digest(expected, code):
            return step

    return None


def verify_totp_or_recovery_code(
    admin,
    submitted_code: str,
) -> bool:
    """Verify a TOTP code or consume one recovery code."""
    if not admin.totp_enabled:
        return False

    code = (submitted_code or "").strip().upper()

    # Try an authenticator-app code first.
    if (
        admin.totp_secret
        and re.fullmatch(r"\d{6}", code)
    ):
        secret = decrypt_totp_secret(
            admin.totp_secret
        )

        step = matching_totp_step(
            secret,
            code,
            admin.totp_last_used_step,
        )

        if step is not None:
            admin.totp_last_used_step = step
            return True

    # Otherwise, try the one-time recovery codes.
    try:
        hashes = json.loads(
            admin.totp_recovery_codes or "[]"
        )
    except (TypeError, ValueError):
        return False

    for index, stored_hash in enumerate(hashes):
        if check_password_hash(stored_hash, code):
            # Remove the code immediately from the in-memory list.
            # The caller must commit this change to the database.
            del hashes[index]

            admin.totp_recovery_codes = json.dumps(
                hashes
            )

            return True

    return False