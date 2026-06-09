from sovereign_rag.adapters.pii_vault import InMemoryPIIVault
from sovereign_rag.domain.models import PIIEntityType

_TEXT = "Contact alice@acme.eu or bob@acme.eu for details."


def _vault() -> InMemoryPIIVault:
    return InMemoryPIIVault(secret="unit-vault-secret")


def test_tokenize_replaces_pii_and_roundtrips() -> None:
    vault = _vault()
    result = vault.tokenize(_TEXT, "acme")
    assert "alice@acme.eu" not in result.text
    assert "bob@acme.eu" not in result.text
    assert all(tok.entity_type is PIIEntityType.EMAIL for tok in result.tokens)
    assert vault.detokenize(result.text, "acme") == _TEXT


def test_tokens_are_deterministic_per_value() -> None:
    vault = _vault()
    first = vault.tokenize("ping alice@acme.eu", "acme").text
    second = vault.tokenize("again alice@acme.eu", "acme").text
    assert first.split("ping ")[1] == second.split("again ")[1]


def test_no_pii_returns_text_unchanged() -> None:
    vault = _vault()
    result = vault.tokenize("nothing sensitive here", "acme")
    assert result.text == "nothing sensitive here"
    assert result.tokens == []


def test_detokenize_is_tenant_scoped() -> None:
    vault = _vault()
    tokenized = vault.tokenize(_TEXT, "acme").text
    assert vault.detokenize(tokenized, "globex") == tokenized


def test_resolve_unknown_token_returns_none() -> None:
    assert _vault().resolve("[[PII:EMAIL:deadbeef]]", "acme") is None


def test_values_are_encrypted_at_rest() -> None:
    vault = _vault()
    vault.tokenize("alice@acme.eu", "acme")
    stored = b"".join(vault._store.values())  # type: ignore[attr-defined]
    assert b"alice@acme.eu" not in stored


def test_resolve_roundtrips_single_token() -> None:
    vault = _vault()
    token = vault.tokenize("alice@acme.eu", "acme").tokens[0].token
    assert vault.resolve(token, "acme") == "alice@acme.eu"
