import pytest

from app.auth.rbac import require_role
from fastapi import HTTPException


def test_require_role_allows_superadmin_for_any_set():
    # Should not raise even though "superadmin" is not in the allowed set.
    require_role("superadmin", {"admin"})
    require_role("superadmin", {"viewer"})


def test_require_role_still_blocks_unlisted_normal_role():
    with pytest.raises(HTTPException) as exc:
        require_role("viewer", {"admin"})
    assert exc.value.status_code == 403
