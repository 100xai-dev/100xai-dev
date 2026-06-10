"""WordPress.com OAuth2 connect flow.

Provides an alternative to self-hosted Application Passwords: the user authorizes
100xAI against their WordPress.com account and we store a Bearer access token.

The callback is intentionally NOT authenticated (WordPress.com redirects the
browser to it). It's protected instead by a signed ``state`` token minted by the
authenticated ``/start`` endpoint, which carries the brand/org/user.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import AuditLog, Brand, IntegrationAccount, IntegrationToken
from app.models.base import uuid_str
from app.routers.integrations import _get_encryptor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations/wordpress/oauth", tags=["integrations"])

_AUTHORIZE_URL = "https://public-api.wordpress.com/oauth2/authorize"
_TOKEN_URL = "https://public-api.wordpress.com/oauth2/token"
_STATE_ALG = "HS256"
_STATE_ISS = "100xai-wpcom-oauth"


def _mint_state(brand_id: str, org_id: str, user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return pyjwt.encode(
        {
            "iss": _STATE_ISS,
            "brand_id": brand_id,
            "org_id": org_id,
            "user_id": user_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
        },
        get_settings().jwt_secret,
        algorithm=_STATE_ALG,
    )


def _decode_state(state: str) -> dict:
    try:
        return pyjwt.decode(
            state,
            get_settings().jwt_secret,
            algorithms=[_STATE_ALG],
            issuer=_STATE_ISS,
            options={"require": ["exp", "brand_id", "org_id", "user_id"]},
        )
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid or expired OAuth state: {exc}")


@router.get("/start")
def start_wpcom_oauth(
    brand_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return the WordPress.com authorize URL to redirect the user to."""
    s = get_settings()
    if not s.wpcom_client_id:
        raise HTTPException(status_code=503, detail="WordPress.com OAuth is not configured")

    brand = db.query(Brand).filter(Brand.id == brand_id, Brand.org_id == current_user.org_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    params = {
        "client_id": s.wpcom_client_id,
        "redirect_uri": s.wpcom_redirect_uri,
        "response_type": "code",
        "scope": "global",
        "state": _mint_state(brand_id, current_user.org_id, current_user.id),
    }
    return {"authorize_url": f"{_AUTHORIZE_URL}?{urlencode(params)}"}


@router.get("/callback")
async def wpcom_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """Exchange the authorization code for a token and persist the integration."""
    s = get_settings()
    frontend = s.frontend_url.rstrip("/")

    if error:
        return RedirectResponse(f"{frontend}/brands?wpcom_error={error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    claims = _decode_state(state)
    brand_id = claims["brand_id"]

    brand = db.query(Brand).filter(Brand.id == brand_id, Brand.org_id == claims["org_id"]).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    data = {
        "client_id": s.wpcom_client_id,
        "client_secret": s.wpcom_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": s.wpcom_redirect_uri,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(_TOKEN_URL, data=data)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"WordPress.com token exchange failed: {exc}")

    if resp.status_code != 200:
        logger.warning("WP.com token exchange failed: %s %s", resp.status_code, resp.text[:300])
        return RedirectResponse(f"{frontend}/brands/{brand_id}/integrations/wordpress?wpcom_error=token_exchange")

    token = resp.json()
    access_token = token.get("access_token")
    blog_id = str(token.get("blog_id") or "")
    blog_url = token.get("blog_url") or ""
    if not access_token or not blog_id:
        return RedirectResponse(f"{frontend}/brands/{brand_id}/integrations/wordpress?wpcom_error=incomplete_token")

    config = {
        "auth_type": "oauth",
        "blog_id": blog_id,
        "site_url": blog_url.rstrip("/"),
        "default_status": "publish",
        "default_categories": [],
    }

    account = (
        db.query(IntegrationAccount)
        .filter(IntegrationAccount.brand_id == brand_id, IntegrationAccount.provider == "wordpress")
        .first()
    )
    now = datetime.now(timezone.utc)
    if account:
        account.status = "active"
        account.config = config
        account.display_label = blog_url or "WordPress.com"
        account.last_tested_at = now
        account.last_error = None
    else:
        account = IntegrationAccount(
            id=uuid_str(),
            brand_id=brand_id,
            provider="wordpress",
            status="active",
            display_label=blog_url or "WordPress.com",
            config=config,
            last_tested_at=now,
            last_error=None,
            created_by=claims["user_id"],
        )
        db.add(account)
    db.flush()

    encryptor = _get_encryptor()
    ciphertext, key_id = encryptor.encrypt({"access_token": access_token})
    existing_token = (
        db.query(IntegrationToken)
        .filter(IntegrationToken.integration_account_id == account.id)
        .first()
    )
    if existing_token:
        existing_token.encrypted_payload = ciphertext
        existing_token.encryption_key_id = key_id
    else:
        db.add(IntegrationToken(
            id=uuid_str(),
            integration_account_id=account.id,
            encrypted_payload=ciphertext,
            encryption_key_id=key_id,
        ))

    db.add(AuditLog(
        org_id=brand.org_id,
        user_id=claims["user_id"],
        brand_id=brand_id,
        action="integration.wordpress.oauth_connected",
        resource_type="integration_account",
        resource_id=account.id,
        metadata_json={"blog_id": blog_id, "blog_url": blog_url},
    ))
    db.commit()

    return RedirectResponse(f"{frontend}/brands/{brand_id}/integrations/wordpress?wpcom_connected=1")
