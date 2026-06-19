from fastapi import HTTPException, status


ROLE_ORDER = {
    "viewer": 1,
    "team_member": 2,
    "admin": 3,
    "superadmin": 99,
}


def require_role(actual: str, allowed: set[str]) -> None:
    # A platform superadmin satisfies every role requirement.
    if actual == "superadmin":
        return
    if actual not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")

