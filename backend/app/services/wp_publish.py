"""Shared helper for publishing an approved/generated blog draft to a brand's
connected WordPress site.

Used by both the manual approve endpoint (app/routers/blogs.py) and the
scheduled auto-publish worker task (worker/tasks/scheduler.py), so the publish
behaviour stays identical in both paths.
"""
from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from app.models.blog import BlogDraft, BlogJob

logger = logging.getLogger(__name__)


class WPPublishError(Exception):
    """Raised when a blog draft cannot be published to WordPress."""


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")[:200]


async def publish_blog_draft(
    db: Session,
    brand_id: str,
    job: BlogJob,
    draft: BlogDraft,
    *,
    status: str = "publish",
) -> str:
    """Publish ``draft`` to the brand's connected WordPress site.

    Returns the public URL. Raises WPPublishError on any failure (no HTTP
    coupling, so the worker can use it too).
    """
    # Lazy imports avoid import cycles at module load.
    from app.integrations.base import PublishPayload
    from app.integrations.registry import get_provider
    from app.models import IntegrationAccount
    from app.routers.integrations import _credentials_for_account

    account = (
        db.query(IntegrationAccount)
        .filter(
            IntegrationAccount.brand_id == brand_id,
            IntegrationAccount.provider == "wordpress",
            IntegrationAccount.status == "active",
        )
        .first()
    )
    if not account:
        account = (
            db.query(IntegrationAccount)
            .filter(IntegrationAccount.brand_id == brand_id, IntegrationAccount.provider == "wordpress")
            .first()
        )
    if not account:
        raise WPPublishError("No WordPress integration connected for this brand")

    credentials = _credentials_for_account(account, db)
    has_app_password = credentials.get("username") and credentials.get("application_password")
    has_oauth = credentials.get("access_token")
    if not (has_app_password or has_oauth):
        raise WPPublishError("WordPress integration has no usable credentials")

    cfg = dict(account.config or {})
    # OAuth accounts don't need site_url (they use WordPress.com API)
    # Only validate site_url for Application Password accounts
    if has_app_password and not cfg.get("site_url"):
        raise WPPublishError("WordPress integration is missing site_url")
    cfg["default_status"] = status  # "publish" = live, "draft" = WP draft

    tags = list(job.brief.tags) if (job.brief and job.brief.tags) else []
    payload = PublishPayload(
        title=draft.title,
        slug=_slugify(draft.title),
        merged_html=draft.html_content,
        meta_description=draft.meta_description or "",
        featured_image_url=draft.featured_image_url,
        tags=tags,
    )

    provider = get_provider("wordpress")
    try:
        result = await provider.publish(cfg, credentials, payload)
    except Exception as exc:  # noqa: BLE001 - surface any provider/network error
        logger.exception("WordPress publish failed for blog %s", job.id)
        raise WPPublishError(str(exc)) from exc

    if account.status != "active":
        account.status = "active"
    return result.public_url
