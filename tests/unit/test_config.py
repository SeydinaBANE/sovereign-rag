import pytest
from pydantic import ValidationError

from sovereign_rag.config import (
    AuditProvider,
    AuthProvider,
    EmbeddingProvider,
    LLMProvider,
    Settings,
)


def test_settings_defaults_are_valid():
    settings = Settings(_env_file=None)
    assert settings.auth_enabled is False
    assert settings.audit_provider is AuditProvider.FILE


def test_settings_static_auth_without_keys_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, auth_enabled=True, auth_provider=AuthProvider.STATIC, api_keys=[])


def test_settings_mistral_llm_without_key_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_provider=LLMProvider.MISTRAL, mistral_api_key="")


def test_settings_mistral_embedding_without_key_is_rejected():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            embedding_provider=EmbeddingProvider.MISTRAL,
            mistral_api_key="",
        )


def test_settings_vault_requires_strong_secret():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, pii_vault_on_ingest=True, pii_vault_secret="short")


def test_settings_postgres_audit_without_dsn_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, audit_provider=AuditProvider.POSTGRES, audit_dsn="")


def test_settings_oidc_without_audience_is_rejected():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            auth_enabled=True,
            auth_provider=AuthProvider.OIDC,
            oidc_issuer="https://issuer.example.eu",
            oidc_audience="",
        )


def test_settings_empty_allowed_regions_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, allowed_regions=[])
