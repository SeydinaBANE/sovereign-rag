from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sovereign_rag.adapters.vault_crypto import TOKEN_RE, build_cipher, derive_token
from sovereign_rag.compliance import pii
from sovereign_rag.domain.models import PIIToken, TokenizationResult

if TYPE_CHECKING:
    from psycopg import Connection

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pii_vault (
    tenant_id TEXT NOT NULL,
    token TEXT NOT NULL,
    ciphertext BYTEA NOT NULL,
    PRIMARY KEY (tenant_id, token)
)
"""


class PostgresPIIVault:
    """Shared reversible PII vault backed by Postgres for multi-replica HA.

    Same deterministic tokens and Fernet-encrypted values as the in-memory vault,
    but persisted so tokens minted on one replica detokenize on any other. The SDK
    is imported lazily to keep the package importable without ``psycopg``.
    """

    def __init__(self, secret: str, dsn: str, salt: str = "sovereign-rag-pii-vault") -> None:
        self._secret = secret.encode("utf-8")
        self._cipher = build_cipher(self._secret, salt.encode("utf-8"))
        self._dsn = dsn
        with self._open() as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def _open(self) -> Connection:
        import psycopg

        return psycopg.connect(self._dsn)

    def tokenize(self, text: str, tenant_id: str) -> TokenizationResult:
        findings = pii.detect(text)
        if not findings:
            return TokenizationResult(text=text)
        tokens: list[PIIToken] = []
        tokenized = text
        with self._open() as conn:
            for finding in sorted(findings, key=lambda f: f.start, reverse=True):
                value = text[finding.start : finding.end]
                token = derive_token(self._secret, tenant_id, finding.entity_type.value, value)
                conn.execute(
                    "INSERT INTO pii_vault (tenant_id, token, ciphertext) VALUES (%s, %s, %s) "
                    "ON CONFLICT (tenant_id, token) DO UPDATE SET ciphertext = EXCLUDED.ciphertext",
                    (tenant_id, token, self._cipher.encrypt(value.encode("utf-8"))),
                )
                tokenized = tokenized[: finding.start] + token + tokenized[finding.end :]
                tokens.append(PIIToken(token=token, entity_type=finding.entity_type))
            conn.commit()
        tokens.reverse()
        return TokenizationResult(text=tokenized, tokens=tokens)

    def detokenize(self, text: str, tenant_id: str) -> str:
        def _replace(match: re.Match[str]) -> str:
            return self.resolve(match.group(0), tenant_id) or match.group(0)

        return TOKEN_RE.sub(_replace, text)

    def resolve(self, token: str, tenant_id: str) -> str | None:
        with self._open() as conn:
            row = conn.execute(
                "SELECT ciphertext FROM pii_vault WHERE tenant_id = %s AND token = %s",
                (tenant_id, token),
            ).fetchone()
        if row is None:
            return None
        return self._cipher.decrypt(bytes(row[0])).decode("utf-8")
