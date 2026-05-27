from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from app.auth.jwt import decode_access_token


@dataclass(frozen=True)
class CurrentUser:
    id: str
    org_id: str
    role: str


def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc
    return CurrentUser(id=payload["sub"], org_id=payload["org_id"], role=payload["role"])

