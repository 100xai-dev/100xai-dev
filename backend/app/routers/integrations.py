from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List

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
    """Convert IntegrationAccount to dict for legacy API compatibility"""
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

def _account_to_channel_integration(acc: IntegrationAccount) -> dict:
    """Convert IntegrationAccount to ChannelIntegration format for new frontend"""
    # Map provider names to channel types
    provider_to_channel = {
        "wordpress": "wordpress",
        "webhook": "webhook", 
        "shopify": "shopify",
        "webflow": "ghost"  # Map webflow to ghost for now
    }
    
    # Map status values
    status_map = {
        "active": "connected",
        "pending": "disconnected", 
        "failed": "error",
        "testing": "testing"
    }
    
    return {
        "id": acc.id,
        "brand_id": acc.brand_id,
        "channel_type": provider_to_channel.get(acc.provider, acc.provider),
        "name": acc.display_label or f"{acc.provider.title()} Integration",
        "status": status_map.get(acc.status, "disconnected"),
        "config": {
            **acc.config,
            "last_tested_at": acc.last_tested_at.isoformat() if acc.last_tested_at else None,
            "last_error": acc.last_error
        },
        "created_at": acc.created_at.isoformat() if acc.created_at else None,
        "updated_at": acc.updated_at.isoformat() if acc.updated_at else None,
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
# GET /v1/brands/:id/integrations - Updated to support both legacy and channel formats
# ---------------------------------------------------------------------------


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


class WordPressTestConfig(BaseModel):
    site_url: str
    username: str
    password: str
    auth_type: str = "application_password"
    custom_post_type: Optional[str] = "post"
    auto_publish: Optional[bool] = True

class WebhookTestConfig(BaseModel):
    webhook_url: str
    auth_type: str = "none"
    auth_token: Optional[str] = None
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    api_key_header: Optional[str] = None
    api_key_value: Optional[str] = None
    hmac_secret: Optional[str] = None
    hmac_algorithm: Optional[str] = "sha256"
    payload_format: str = "json"
    webhook_timeout: Optional[int] = 30


# ---------------------------------------------------------------------------
# Test WordPress config (before saving): POST /v1/brands/:id/integrations/wordpress/test
# Must be declared BEFORE /{provider}/test so FastAPI's literal match wins.
# ---------------------------------------------------------------------------

@router.post("/wordpress/test")
async def test_wordpress_config(
    brand_id: str,
    config: WordPressTestConfig,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Test WordPress configuration before saving"""
    _get_brand_scoped(brand_id, db, current_user.org_id)

    try:
        provider = get_provider("wordpress")

        wp_config = {
            "site_url": config.site_url.rstrip("/"),
            "default_status": "draft" if not config.auto_publish else "publish",
            "default_categories": [],
            "default_author_id": None,
        }

        credentials = {
            "username": config.username,
            "application_password": config.password,
        }

        test_result = await provider.test_connection(wp_config, credentials)

        if test_result.ok:
            return {
                "success": True,
                "site_info": {
                    "name": test_result.site_info.get("name", "WordPress Site"),
                    "url": config.site_url,
                    "wp_version": test_result.site_info.get("wp_version", "Unknown"),
                    "can_publish": True
                }
            }
        else:
            return {
                "success": False,
                "error": test_result.error or "Connection test failed"
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"WordPress test failed: {str(e)}"
        }


# ---------------------------------------------------------------------------
# Test webhook config (before saving): POST /v1/brands/:id/integrations/webhook/test
# Must be declared BEFORE /{provider}/test so FastAPI's literal match wins.
# ---------------------------------------------------------------------------

@router.post("/webhook/test")
async def test_webhook_config(
    brand_id: str,
    config: WebhookTestConfig,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Test webhook configuration before saving"""
    _get_brand_scoped(brand_id, db, current_user.org_id)

    try:
        import httpx
        import time

        test_payload = {
            "event": "connection_test",
            "brand_id": brand_id,
            "test_data": {
                "message": "This is a test webhook from 100xAI",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

        headers = {"Content-Type": "application/json"}

        if config.auth_type == "bearer" and config.auth_token:
            headers["Authorization"] = f"Bearer {config.auth_token}"
        elif config.auth_type == "api_key" and config.api_key_header and config.api_key_value:
            headers[config.api_key_header] = config.api_key_value
        elif config.auth_type == "hmac" and config.hmac_secret:
            headers["X-Webhook-Signature"] = "test-signature"

        start_time = time.time()

        async with httpx.AsyncClient(timeout=config.webhook_timeout) as client:
            if config.auth_type == "basic" and config.auth_username and config.auth_password:
                auth = (config.auth_username, config.auth_password)
            else:
                auth = None

            response = await client.post(
                config.webhook_url,
                json=test_payload if config.payload_format == "json" else None,
                data=test_payload if config.payload_format == "form_data" else None,
                headers=headers,
                auth=auth
            )

        response_time = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "response_status": response.status_code,
            "response_time": response_time
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Webhook test failed: {str(e)}"
        }


# ---------------------------------------------------------------------------
# Test connection: POST /v1/brands/:id/integrations/:provider/test
# ---------------------------------------------------------------------------

def _credentials_for_account(account: IntegrationAccount, db: Session) -> dict:
    """Resolve credentials for an integration account.

    Accounts created via the proper setup flow store an encrypted IntegrationToken.
    Accounts created via the channel endpoint store credentials inline in config
    (plaintext). Support both so connection testing works regardless of origin.
    """
    token = (
        db.query(IntegrationToken)
        .filter(IntegrationToken.integration_account_id == account.id)
        .first()
    )
    if token:
        encryptor = _get_encryptor()
        return encryptor.decrypt(token.encrypted_payload, token.encryption_key_id)

    cfg = account.config or {}
    if account.provider == "wordpress":
        return {
            "username": cfg.get("username", ""),
            "application_password": cfg.get("application_password") or cfg.get("password", ""),
        }
    # Generic fallback: pass through whatever creds-ish keys exist in config
    return {k: cfg.get(k) for k in ("username", "password", "application_password", "auth_token") if cfg.get(k)}


@router.post("/{provider_or_id}/test")
async def test_integration(
    brand_id: str,
    provider_or_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Test a configured integration. ``provider_or_id`` may be either an
    integration account id (used by the integrations list page) or a provider
    name (e.g. ``wordpress``)."""
    _get_brand_scoped(brand_id, db, current_user.org_id)

    # Resolve account by id first, then fall back to provider name.
    account = (
        db.query(IntegrationAccount)
        .filter(IntegrationAccount.brand_id == brand_id, IntegrationAccount.id == provider_or_id)
        .first()
    )
    if not account:
        account = (
            db.query(IntegrationAccount)
            .filter(IntegrationAccount.brand_id == brand_id, IntegrationAccount.provider == provider_or_id)
            .first()
        )
    if not account:
        raise HTTPException(status_code=404, detail="Integration not configured")

    try:
        prov = get_provider(account.provider)
    except UnknownProviderError:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {account.provider}")

    credentials = _credentials_for_account(account, db)

    test = await prov.test_connection(account.config, credentials)
    now = datetime.now(timezone.utc)

    account.last_tested_at = now
    account.status = "active" if test.ok else "failed"
    account.last_error = test.error if not test.ok else None
    db.commit()

    return {
        "ok": test.ok,
        "success": test.ok,
        "error": test.error,
        "site_info": test.site_info,
    }


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


# ---------------------------------------------------------------------------
# New Channel Integration API for Frontend
# ---------------------------------------------------------------------------

class ChannelIntegrationCreate(BaseModel):
    channel_type: str
    name: str
    config: Dict[str, Any]

class ChannelIntegrationUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None



# Update existing endpoint to support both formats
@router.get("")
def list_integrations(
    brand_id: str, 
    format: str = "legacy",  # "legacy" or "channel"
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
):
    """List integrations - supports both legacy and new channel format"""
    _get_brand_scoped(brand_id, db, current_user.org_id)
    accounts = (
        db.query(IntegrationAccount)
        .filter(IntegrationAccount.brand_id == brand_id)
        .all()
    )
    
    if format == "channel":
        return [_account_to_channel_integration(acc) for acc in accounts]
    else:
        return {"items": [_account_to_dict(a) for a in accounts]}

# POST /v1/brands/{brand_id}/integrations - Create new integration 
@router.post("", status_code=201)
async def create_channel_integration(
    brand_id: str,
    integration: ChannelIntegrationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new channel integration"""
    brand = _get_brand_scoped(brand_id, db, current_user.org_id)
    
    # Map channel types back to providers
    channel_to_provider = {
        "wordpress": "wordpress",
        "webhook": "webhook",
        "shopify": "shopify", 
        "ghost": "webflow"  # Map ghost back to webflow
    }
    
    provider = channel_to_provider.get(integration.channel_type)
    if not provider:
        raise HTTPException(status_code=400, detail=f"Unsupported channel type: {integration.channel_type}")
    
    # Check if integration already exists
    existing = (
        db.query(IntegrationAccount)
        .filter(IntegrationAccount.brand_id == brand_id, IntegrationAccount.provider == provider)
        .first()
    )
    
    if existing:
        raise HTTPException(status_code=409, detail=f"Integration for {provider} already exists")
    
    # Create new integration account
    account = IntegrationAccount(
        id=uuid_str(),
        brand_id=brand_id,
        provider=provider,
        status="pending",
        display_label=integration.name,
        config=integration.config,
        created_by=current_user.id,
    )
    
    db.add(account)
    db.commit()
    db.refresh(account)
    
    return _account_to_channel_integration(account)

# PUT /v1/brands/{brand_id}/integrations/{integration_id} - Update integration
@router.put("/{integration_id}")
async def update_channel_integration(
    brand_id: str,
    integration_id: str,
    update_data: ChannelIntegrationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update an existing channel integration"""
    _get_brand_scoped(brand_id, db, current_user.org_id)
    
    account = (
        db.query(IntegrationAccount)
        .filter(IntegrationAccount.id == integration_id, IntegrationAccount.brand_id == brand_id)
        .first()
    )
    
    if not account:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Update fields
    if update_data.name is not None:
        account.display_label = update_data.name
    if update_data.config is not None:
        account.config = {**account.config, **update_data.config}
    
    account.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(account)
    
    return _account_to_channel_integration(account)

# DELETE /v1/brands/{brand_id}/integrations/{integration_id} - Delete integration  
@router.delete("/{integration_id}", status_code=204)
async def delete_channel_integration(
    brand_id: str,
    integration_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a channel integration"""
    brand = _get_brand_scoped(brand_id, db, current_user.org_id)
    
    account = (
        db.query(IntegrationAccount)
        .filter(IntegrationAccount.id == integration_id, IntegrationAccount.brand_id == brand_id)
        .first()
    )
    
    if not account:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Log the deletion
    db.add(AuditLog(
        org_id=brand.org_id,
        user_id=current_user.id,
        brand_id=brand_id,
        action=f"integration.{account.provider}.removed",
        resource_type="integration_account",
        resource_id=account.id,
        metadata_json={},
    ))
    
    db.delete(account)
    db.commit()

# Connection testing for both list-page (by id) and provider-name flows is
# handled by the consolidated POST /{provider_or_id}/test endpoint above.

