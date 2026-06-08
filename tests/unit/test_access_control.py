import pytest

from sovereign_rag.domain.access import Permission, Principal, Role, permissions_for
from sovereign_rag.domain.exceptions import AuthorizationError
from sovereign_rag.services import access_control


def test_viewer_cannot_ingest():
    assert Permission.INGEST not in permissions_for([Role.VIEWER])


def test_admin_has_all_permissions():
    granted = permissions_for([Role.ADMIN])
    assert set(Permission) == set(granted)


def test_require_raises_for_missing_permission():
    viewer = Principal(subject="v", tenant_id="acme", roles=[Role.VIEWER])
    with pytest.raises(AuthorizationError):
        access_control.require(viewer, Permission.INGEST)


def test_require_passes_for_granted_permission():
    editor = Principal(subject="e", tenant_id="acme", roles=[Role.EDITOR])
    access_control.require(editor, Permission.INGEST)


def test_ensure_tenant_blocks_cross_tenant_access():
    principal = Principal(subject="e", tenant_id="acme", roles=[Role.EDITOR])
    with pytest.raises(AuthorizationError):
        access_control.ensure_tenant(principal, "globex")
