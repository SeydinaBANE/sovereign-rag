import os

import pytest

pytest.importorskip("psycopg")
pytest.importorskip("cryptography")

from sovereign_rag.adapters.postgres_pii_vault import PostgresPIIVault

pytestmark = pytest.mark.integration

_SECRET = "integration-vault-secret-0123456789"


@pytest.fixture
def dsn() -> str:
    value = os.environ.get("SRAG_PII_VAULT_DSN")
    if not value:
        pytest.skip("SRAG_PII_VAULT_DSN not set")
    _reset(value)
    return value


def _reset(dsn: str) -> None:
    import psycopg

    with psycopg.connect(dsn) as conn:
        conn.execute("DROP TABLE IF EXISTS pii_vault")
        conn.commit()


def test_vault_tokenizes_and_detokenizes_across_instances(dsn: str) -> None:
    minter = PostgresPIIVault(secret=_SECRET, dsn=dsn)
    result = minter.tokenize("email alice@acme.eu please", "acme")
    assert "alice@acme.eu" not in result.text
    assert result.tokens

    other_replica = PostgresPIIVault(secret=_SECRET, dsn=dsn)
    assert other_replica.detokenize(result.text, "acme") == "email alice@acme.eu please"


def test_vault_resolve_is_tenant_scoped(dsn: str) -> None:
    vault = PostgresPIIVault(secret=_SECRET, dsn=dsn)
    result = vault.tokenize("contact alice@acme.eu", "acme")
    token = result.tokens[0].token
    assert vault.resolve(token, "acme") == "alice@acme.eu"
    assert vault.resolve(token, "intruder") is None
