from __future__ import annotations

import base64
import hashlib
import hmac
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cryptography.fernet import Fernet

_KDF_ITERATIONS = 200_000

TOKEN_RE = re.compile(r"\[\[PII:[A-Z_]+:[0-9a-f]+\]\]")


def derive_token(secret: bytes, tenant_id: str, entity_type: str, value: str) -> str:
    digest = hmac.new(
        secret, f"{tenant_id}:{entity_type}:{value}".encode(), hashlib.sha256
    ).hexdigest()[:16]
    return f"[[PII:{entity_type}:{digest}]]"


def build_cipher(secret: bytes, salt: bytes) -> Fernet:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.hashes import SHA256
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    kdf = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=_KDF_ITERATIONS)
    return Fernet(base64.urlsafe_b64encode(kdf.derive(secret)))
