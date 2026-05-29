from datetime import datetime, timedelta, timezone

import jwt as pyjwt

from app.config import get_settings

_ALGORITHM = "HS256"
_ISSUER = "100xai"


class TokenError(ValueError):
    pass


def create_access_token(user_id: str, org_id: str, role: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "iss": _ISSUER,
        "sub": str(user_id),
        "org_id": str(org_id),
        "role": role,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.jwt_expiry_hours)).timestamp()),
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return pyjwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[_ALGORITHM],
            issuer=_ISSUER,
            options={"require": ["exp", "iat", "sub", "org_id", "role", "iss"]},
            leeway=timedelta(seconds=30),
        )
    except pyjwt.ExpiredSignatureError as exc:
        raise TokenError("token expired") from exc
    except pyjwt.InvalidTokenError as exc:
        raise TokenError(f"invalid token: {exc}") from exc
