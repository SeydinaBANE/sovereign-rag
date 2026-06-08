from sovereign_rag.adapters.principals import StaticPrincipalResolver
from sovereign_rag.config import ApiKeyPrincipal
from sovereign_rag.domain.access import Role


def _resolver() -> StaticPrincipalResolver:
    return StaticPrincipalResolver(
        [ApiKeyPrincipal(key="acme-key", subject="alice", tenant_id="acme", roles=[Role.EDITOR])]
    )


def test_resolver_returns_principal_for_known_key():
    principal = _resolver().resolve("acme-key")
    assert principal is not None
    assert principal.tenant_id == "acme"
    assert Role.EDITOR in principal.roles


def test_resolver_returns_none_for_unknown_key():
    assert _resolver().resolve("nope") is None
