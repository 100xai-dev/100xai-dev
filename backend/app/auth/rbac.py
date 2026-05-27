from fastapi import HTTPException, status


ROLE_ORDER = {
    "viewer": 1,
    "team_member": 2,
    "admin": 3,
}


def require_role(actual: str, allowed: set[str]) -> None:
    if actual not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")

