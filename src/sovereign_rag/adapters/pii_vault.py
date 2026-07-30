from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sovereign_rag.adapters.vault_crypto import TOKEN_RE, build_cipher, derive_token
from sovereign_rag.compliance import pii
from sovereign_rag.domain.models import PIIToken, TokenizationResult

if TYPE_CHECKING:
    from cryptography.fernet import Fernet


class InMemoryPIIVault:
    """Reversible PII vault: deterministic tokens, encrypted values, tenant-scoped.

    The same value within a tenant always maps to the same token (referential
    integrity); values are stored Fernet-encrypted at rest and can only be resolved
    for the owning tenant. Defaults are sovereign and dependency-light.
    """

    def __init__(self, secret: str, salt: str = "sovereign-rag-pii-vault") -> None:
        self._secret = secret.encode("utf-8")
        self._salt = salt.encode("utf-8")
        self._store: dict[tuple[str, str], bytes] = {}
        self._cipher: Fernet | None = None

    def tokenize(self, text: str, tenant_id: str) -> TokenizationResult:
        findings = pii.detect(text)
        if not findings:
            return TokenizationResult(text=text)
        tokens: list[PIIToken] = []
        tokenized = text
        for finding in sorted(findings, key=lambda f: f.start, reverse=True):
            value = text[finding.start : finding.end]
            token = self._token(tenant_id, finding.entity_type.value, value)
            self._store[tenant_id, token] = self._encrypt(value)
            tokenized = tokenized[: finding.start] + token + tokenized[finding.end :]
            tokens.append(PIIToken(token=token, entity_type=finding.entity_type))
        tokens.reverse()
        return TokenizationResult(text=tokenized, tokens=tokens)

    def detokenize(self, text: str, tenant_id: str) -> str:
        def _replace(match: re.Match[str]) -> str:
            return self.resolve(match.group(0), tenant_id) or match.group(0)

        return TOKEN_RE.sub(_replace, text)

    def resolve(self, token: str, tenant_id: str) -> str | None:
        ciphertext = self._store.get((tenant_id, token))
        if ciphertext is None:
            return None
        return self._decrypt(ciphertext)

    def _token(self, tenant_id: str, entity_type: str, value: str) -> str:
        return derive_token(self._secret, tenant_id, entity_type, value)

    def _fernet(self) -> Fernet:
        if self._cipher is None:
            self._cipher = build_cipher(self._secret, self._salt)
        return self._cipher

    def _encrypt(self, value: str) -> bytes:
        return self._fernet().encrypt(value.encode("utf-8"))

    def _decrypt(self, ciphertext: bytes) -> str:
        return self._fernet().decrypt(ciphertext).decode("utf-8")
