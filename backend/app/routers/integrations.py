from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.deps import get_current_user, get_db
from app.models import Brand, IntegrationAccount, IntegrationToken, AuditLog
from app.models.base import uuid_str
from app.services.encryption import TokenEncryptor
from app.config import get_settings
from app.integrations.registry import get_provider, UnknownProviderError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/brands/{brand_id}/integrations", tags=["integrations"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_brand_scoped(brand_id: str, db: Session, org_id: str) -> Brand:
    brand = db.query(Brand).filter(Brand.id == brand_id, Brand.org_id == org_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


def _account_to_dict(acc: IntegrationAccount) -> dict:
    return {
        "id": acc.id,
        "brand_id": acc.brand_id,
        "provider": acc.provider,
        "status": acc.status,
        "display_label": acc.display_label,
        "config": acc.config,
        "last_tested_at": acc.last_tested_at.isoformat() if acc.last_tested_at else None,
        "last_error": acc.last_error,
        "created_at": acc.created_at.isoformat() if acc.created_at else None,
    }


def _get_encryptor() -> TokenEncryptor:
    import json as _json

    s = get_settings()
    if s.token_encryption_keyring:
        try:
            keyring = _json.loads(s.token_encryption_keyring)
        except _json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=500, detail=f"TOKEN_ENCRYPTION_KEYRING is not valid JSON: {exc}"
            )
        if not isinstance(keyring, dict) or not keyring:
            raise HTTPException(status_code=500, detail="TOKEN_ENCRYPTION_KEYRING must be a non-empty object")
        return TokenEncryptor(keyring=keyring, active_key_id=s.token_encryption_key_id)
    if not s.token_encryption_key:
        raise HTTPException(status_code=500, detail="TOKEN_ENCRYPTION_KEY not configured")
    return TokenEncryptor(key_b64=s.token_encryption_key, key_id=s.token_encryption_key_id)


# ---------------------------------------------------------------------------
# GET /v1/brands/:id/integrations
# ---------------------------------------------------------------------------

@router.get("")
def list_integrations(brand_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _get_brand_scoped(brand_id, db, current_user.org_id)
    accounts = (
        db.query(IntegrationAccount)
        .filter(IntegrationAccount.brand_id == brand_id)
        .all()
    )
    return {"items": [_account_to_dict(a) for a in accounts]}


# ---------------------------------------------------------------------------
# WordPress setup: POST /v1/brands/:id/integrations/wordpress
# ---------------------------------------------------------------------------

class WordPressSetupIn(BaseModel):
    site_url: str
    username: str
    application_password: str
    default_status: str = "draft"
    default_categories: list[int] = []
    default_author_id: Optional[int] = None


@router.post("/wordpress", status_code=201)
async def setup_wordpress(
    brand_id: str,
    body: WordPressSetupIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    brand = _get_brand_scoped(brand_id, db, current_user.org_id)
    provider = get_provider("wordpress")

    config = {
        "site_url": body.site_url.rstrip("/"),
        "default_status": body.default_status,
        "default_categories": body.default_categories,
        "default_author_id": body.default_author_id,
    }
    credentials = {
        "username": body.username,
        "application_password": body.application_password,
    }

    # Validate config shape
    val = await provider.validate_config(config)
    if not val.ok:
        raise HTTPException(status_code=422, detail=val.errors)

    # Test connection
    test = await provider.test_connection(config, credentials)
    now = datetime.now(timezone.utc)

    # Upsert integration account
    existing = (
        db.query(IntegrationAccount)
        .filter(IntegrationAccount.brand_id == brand_id, IntegrationAccount.provider == "wordpress")
        .first()
    )

    if not test.ok:
        # Persist failed record so team can see the error
        if existing:
            existing.status = "failed"
            existing.last_error = test.error
            existing.last_tested_at = now
        else:
            db.add(IntegrationAccount(
                id=uuid_str(),
                brand_id=brand_id,
                provider="wordpress",
                status="failed",
                config=config,
                last_tested_at=now,
                last_error=test.error,
                created_by=current_user.id,
            ))
        db.add(AuditLog(
            org_id=brand.org_id,
            user_id=current_user.id,
            brand_id=brand_id,
            action="integration.wordpress.test_failed",
            resource_type="integration_account",
            metadata_json={"error": test.error},
        ))
        db.commit()
        raise HTTPException(status_code=422, detail={"error": test.error, "site_info": {}})

    # Success — store config + encrypt credentials
    config["site_info"] = test.site_info

    if existing:
        existing.status = "active"
        existing.config = config
        existing.display_label = test.site_info.get("name")
        existing.last_tested_at = now
        existing.last_error = None
        account = existing
    else:
        account = IntegrationAccount(
            id=uuid_str(),
            brand_id=brand_id,
            provider="wordpress",
            status="active",
            display_label=test.site_info.get("name"),
            config=config,
            last_tested_at=now,
            last_error=None,
            created_by=current_user.id,
        )
        db.add(account)

    db.flush()  # get account.id

    # Encrypt and store credentials
    encryptor = _get_encryptor()
    ciphertext, key_id = encryptor.encrypt(credentials)

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
        user_id=current_user.id,
        brand_id=brand_id,
        action="integration.wordpress.configured",
        resource_type="integration_account",
        resource_id=account.id,
        metadata_json={"site_info": test.site_info},
    ))

    db.commit()

    return {
        "integration_account_id": account.id,
        "status": "active",
        "tested_at": now.isoformat(),
        "site_info": test.site_info,
    }


# ---------------------------------------------------------------------------
# Test connection: POST /v1/brands/:id/integrations/:provider/test
# ---------------------------------------------------------------------------

@router.post("/{provider}/test")
async def test_integration(
    brand_id: str,
    provider: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _get_brand_scoped(brand_id, db, current_user.org_id)

    try:
        prov = get_provider(provider)
    except UnknownProviderError:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    account = (
        db.query(IntegrationAccount)
        .filter(IntegrationAccount.brand_id == brand_id, IntegrationAccount.provider == provider)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Integration not configured")

    token = (
        db.query(IntegrationToken)
        .filter(IntegrationToken.integration_account_id == account.id)
        .first()
    )
    if not token:
        raise HTTPException(status_code=500, detail="Integration credentials missing")

    encryptor = _get_encryptor()
    credentials = encryptor.decrypt(token.encrypted_payload, token.encryption_key_id)

    test = await prov.test_connection(account.config, credentials)
    now = datetime.now(timezone.utc)

    account.last_tested_at = now
    account.status = "active" if test.ok else "failed"
    account.last_error = test.error if not test.ok else None
    db.commit()

    return {"ok": test.ok, "error": test.error, "site_info": test.site_info}


# ---------------------------------------------------------------------------
# DELETE /v1/brands/:id/integrations/:provider
# ---------------------------------------------------------------------------

@router.delete("/{provider}", status_code=204)
async def remove_integration(
    brand_id: str,
    provider: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    brand = _get_brand_scoped(brand_id, db, current_user.org_id)

    account = (
        db.query(IntegrationAccount)
        .filter(IntegrationAccount.brand_id == brand_id, IntegrationAccount.provider == provider)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Attempt remote revocation (best-effort)
    try:
        prov = get_provider(provider)
        token = (
            db.query(IntegrationToken)
            .filter(IntegrationToken.integration_account_id == account.id)
            .first()
        )
        if token:
            encryptor = _get_encryptor()
            creds = encryptor.decrypt(token.encrypted_payload, token.encryption_key_id)
            await prov.revoke(account.config, creds)
    except Exception as exc:
        logger.warning("Revoke failed for %s: %s", provider, exc)

    db.add(AuditLog(
        org_id=brand.org_id,
        user_id=current_user.id,
        brand_id=brand_id,
        action=f"integration.{provider}.removed",
        resource_type="integration_account",
        resource_id=account.id,
        metadata_json={},
    ))

    db.delete(account)
    db.commit()
