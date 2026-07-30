from sovereign_rag.adapters.vault_crypto import build_cipher, derive_token


def test_derive_token_is_deterministic_and_tenant_scoped():
    secret = b"a-strong-vault-secret-0123456789"
    token = derive_token(secret, "acme", "EMAIL", "alice@acme.eu")
    assert token == derive_token(secret, "acme", "EMAIL", "alice@acme.eu")
    assert token != derive_token(secret, "other", "EMAIL", "alice@acme.eu")
    assert token.startswith("[[PII:EMAIL:")


def test_build_cipher_round_trips_with_same_secret_and_salt():
    secret = b"a-strong-vault-secret-0123456789"
    salt = b"sovereign-rag-pii-vault"
    cipher = build_cipher(secret, salt)
    token = cipher.encrypt(b"alice@acme.eu")
    assert build_cipher(secret, salt).decrypt(token) == b"alice@acme.eu"


def test_build_cipher_with_different_salt_cannot_decrypt():
    import pytest
    from cryptography.fernet import InvalidToken

    secret = b"a-strong-vault-secret-0123456789"
    token = build_cipher(secret, b"salt-one").encrypt(b"secret-value")
    with pytest.raises(InvalidToken):
        build_cipher(secret, b"salt-two").decrypt(token)
