from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sovereign_rag.adapters.retry import RetryPolicy, retry_call
from sovereign_rag.domain.access import Principal, Role

if TYPE_CHECKING:
    from jwt import PyJWK, PyJWKClient

_VALID_ROLES = {role.value for role in Role}


class OidcPrincipalResolver:
    """Resolves OIDC/JWT bearer tokens to principals.

    Validates RS256 tokens against the issuer JWKS or HS256 tokens against a shared
    secret, then maps standard/custom claims onto the tenant + RBAC model. Any
    invalid, expired or malformed token resolves to ``None`` (rejected as 401).
    """

    def __init__(
        self,
        issuer: str,
        audience: str,
        jwks_url: str,
        algorithms: list[str],
        hs256_secret: str,
        subject_claim: str,
        tenant_claim: str,
        roles_claim: str,
        default_tenant: str,
        jwks_timeout: float = 5.0,
        retry: RetryPolicy | None = None,
    ) -> None:
        self._issuer = issuer
        self._audience = audience
        self._algorithms = algorithms
        self._jwks_timeout = jwks_timeout
        self._retry = retry or RetryPolicy()
        self._hs256_secret = hs256_secret
        self._subject_claim = subject_claim
        self._tenant_claim = tenant_claim
        self._roles_claim = roles_claim
        self._default_tenant = default_tenant
        self._jwks_url = jwks_url or (
            f"{issuer.rstrip('/')}/.well-known/jwks.json" if issuer else ""
        )
        self._jwks_client: PyJWKClient | None = None

    def resolve(self, api_key: str) -> Principal | None:
        import jwt

        try:
            algorithm = str(jwt.get_unverified_header(api_key).get("alg", ""))
            if algorithm not in self._algorithms:
                return None
            key = self._signing_key(api_key, algorithm)
            claims = jwt.decode(
                api_key,
                key,
                algorithms=self._algorithms,
                audience=self._audience or None,
                issuer=self._issuer or None,
                options={"verify_aud": bool(self._audience)},
            )
        except jwt.PyJWTError:
            return None
        return self._to_principal(claims)

    def _signing_key(self, token: str, algorithm: str) -> str | PyJWK:
        if algorithm.startswith("HS"):
            return self._hs256_secret
        return retry_call(
            lambda: self._jwk_client().get_signing_key_from_jwt(token),
            self._retry,
        )

    def _jwk_client(self) -> PyJWKClient:
        if self._jwks_client is None:
            from jwt import PyJWKClient

            self._jwks_client = PyJWKClient(self._jwks_url, timeout=int(self._jwks_timeout))
        return self._jwks_client

    def _to_principal(self, claims: dict[str, Any]) -> Principal | None:
        subject = _claim(claims, self._subject_claim)
        if not isinstance(subject, str) or not subject:
            return None
        tenant = _claim(claims, self._tenant_claim)
        tenant_id = tenant if isinstance(tenant, str) and tenant else self._default_tenant
        return Principal(
            subject=subject,
            tenant_id=tenant_id,
            roles=_roles(_claim(claims, self._roles_claim)),
        )


def _claim(claims: dict[str, Any], path: str) -> object:
    current: object = claims
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _roles(raw: object) -> list[Role]:
    if not isinstance(raw, list):
        return []
    return [Role(value) for value in raw if isinstance(value, str) and value in _VALID_ROLES]
