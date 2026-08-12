"""Small, audited-boundary helpers for encryption at rest.

This protects database contents if a dump leaks. It is deliberately described
as encryption at rest, not end-to-end encryption: the server can decrypt data
to deliver messages to authenticated conversation members.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    configured = settings.FIELD_ENCRYPTION_KEY.strip()
    if configured:
        raw = configured.encode()
        try:
            return Fernet(raw)
        except ValueError:
            # Hosting providers commonly generate arbitrary secret strings,
            # while Fernet expects a 32-byte URL-safe base64 value.
            key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    else:
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_text(value: str) -> str:
    if not value:
        return ""
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_text(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""
