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
    expiry = timedelta(minutes=settings.access_token_expiry_minutes)
    payload = {
        "iss": _ISSUER,
        "sub": str(user_id),
        "org_id": str(org_id),
        "role": role,
        "token_type": "access",
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + expiry).timestamp()),
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


def create_refresh_token(user_id: str, org_id: str, role: str) -> str:
    import uuid as _uuid
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expiry = timedelta(days=settings.refresh_token_expiry_days)
    payload = {
        "iss": _ISSUER,
        "sub": str(user_id),
        "org_id": str(org_id),
        "role": role,
        "token_type": "refresh",
        "jti": str(_uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int((now + expiry).timestamp()),
    }
    return pyjwt.encode(payload, settings.refresh_token_secret, algorithm=_ALGORITHM)


def decode_refresh_token(token: str) -> dict:
    settings = get_settings()
    try:
        return pyjwt.decode(
            token,
            settings.refresh_token_secret,
            algorithms=[_ALGORITHM],
            issuer=_ISSUER,
            options={"require": ["exp", "iat", "sub", "org_id", "role", "iss"]},
            leeway=timedelta(seconds=30),
        )
    except pyjwt.ExpiredSignatureError as exc:
        raise TokenError("refresh token expired") from exc
    except pyjwt.InvalidTokenError as exc:
        raise TokenError(f"invalid refresh token: {exc}") from exc
