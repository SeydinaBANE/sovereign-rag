import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from sovereign_rag.adapters.oidc_principals import OidcPrincipalResolver
from sovereign_rag.domain.access import Role

_SECRET = "unit-test-secret-key-at-least-32-bytes-long"
_ISSUER = "https://issuer.example.eu"
_AUDIENCE = "sovereign-rag"


def _hs256_resolver(**overrides: Any) -> OidcPrincipalResolver:
    params: dict[str, Any] = {
        "issuer": _ISSUER,
        "audience": _AUDIENCE,
        "jwks_url": "",
        "algorithms": ["HS256"],
        "hs256_secret": _SECRET,
        "subject_claim": "sub",
        "tenant_claim": "tenant_id",
        "roles_claim": "roles",
        "default_tenant": "default",
    }
    params.update(overrides)
    return OidcPrincipalResolver(**params)


def _hs256_token(secret: str = _SECRET, **claims: Any) -> str:
    payload: dict[str, Any] = {
        "sub": "alice",
        "tenant_id": "acme",
        "roles": ["editor"],
        "aud": _AUDIENCE,
        "iss": _ISSUER,
        "exp": int(time.time()) + 300,
    }
    payload.update(claims)
    return jwt.encode(payload, secret, algorithm="HS256")


def test_valid_token_maps_claims() -> None:
    principal = _hs256_resolver().resolve(_hs256_token())
    assert principal is not None
    assert principal.subject == "alice"
    assert principal.tenant_id == "acme"
    assert principal.roles == [Role.EDITOR]


def test_invalid_signature_is_rejected() -> None:
    token = _hs256_token(secret="a-different-but-equally-long-wrong-secret-key")
    assert _hs256_resolver().resolve(token) is None


def test_expired_token_is_rejected() -> None:
    token = _hs256_token(exp=int(time.time()) - 10)
    assert _hs256_resolver().resolve(token) is None


def test_wrong_audience_is_rejected() -> None:
    token = _hs256_token(aud="other-service")
    assert _hs256_resolver().resolve(token) is None


def test_disallowed_algorithm_is_rejected() -> None:
    token = _hs256_token()
    assert _hs256_resolver(algorithms=["RS256"]).resolve(token) is None


def test_missing_tenant_falls_back_to_default() -> None:
    token = _hs256_token(tenant_id=None)
    principal = _hs256_resolver().resolve(token)
    assert principal is not None
    assert principal.tenant_id == "default"


def test_unknown_roles_are_ignored() -> None:
    token = _hs256_token(roles=["editor", "superhero", "viewer"])
    principal = _hs256_resolver().resolve(token)
    assert principal is not None
    assert principal.roles == [Role.EDITOR, Role.VIEWER]


def test_missing_subject_is_rejected() -> None:
    resolver = _hs256_resolver(subject_claim="preferred_username")
    assert resolver.resolve(_hs256_token()) is None


def test_nested_roles_claim_keycloak_style() -> None:
    resolver = _hs256_resolver(roles_claim="realm_access.roles")
    token = _hs256_token(realm_access={"roles": ["admin"]})
    principal = resolver.resolve(token)
    assert principal is not None
    assert principal.roles == [Role.ADMIN]


def test_garbage_token_is_rejected() -> None:
    assert _hs256_resolver().resolve("not-a-jwt") is None


class _FakeJwkClient:
    def __init__(self, public_pem: bytes) -> None:
        self._public_pem = public_pem

    def get_signing_key_from_jwt(self, token: str) -> bytes:
        return self._public_pem


def test_rs256_token_via_jwks() -> None:
    from cryptography.hazmat.primitives import serialization

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    token = jwt.encode(
        {
            "sub": "bob",
            "tenant_id": "globex",
            "roles": ["admin"],
            "aud": _AUDIENCE,
            "iss": _ISSUER,
            "exp": int(time.time()) + 300,
        },
        private_pem,
        algorithm="RS256",
    )
    resolver = _hs256_resolver(algorithms=["RS256"], hs256_secret="")
    resolver._jwks_client = _FakeJwkClient(public_pem)  # type: ignore[assignment]
    principal = resolver.resolve(token)
    assert principal is not None
    assert principal.subject == "bob"
    assert principal.tenant_id == "globex"
    assert principal.roles == [Role.ADMIN]


@pytest.mark.parametrize("token", ["", "a.b", "a.b.c.d"])
def test_malformed_tokens_are_rejected(token: str) -> None:
    assert _hs256_resolver().resolve(token) is None
