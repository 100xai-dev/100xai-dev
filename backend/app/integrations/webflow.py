"""Webflow integration provider for the new integration system."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx
import re
import time

from app.integrations.base import (
    IntegrationProvider,
    PublishPayload,
    PublishResult,
    TestResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class WebflowProvider(IntegrationProvider):
    """
    Webflow CMS integration using the CMS API.
    Supports publishing blog posts to Webflow CMS collections.
    """

    provider_name = "webflow"

    def __init__(self):
        self.api_base = "https://api.webflow.com/v2"
        self.rate_limit_remaining = 120  # Default rate limit for CMS plans
        self.rate_limit_reset = None

    async def validate_config(self, config: dict) -> ValidationResult:
        """Validate Webflow configuration without making network calls."""
        errors = []
        
        # Check required fields
        if not config.get("site_id"):
            errors.append("site_id is required")
        if not config.get("collection_id"):
            errors.append("collection_id is required")
        
        # Validate optional fields
        default_status = config.get("default_status", "published")
        if default_status not in ("published", "draft"):
            errors.append("default_status must be 'published' or 'draft'")
        
        timeout = config.get("timeout", 30)
        if not isinstance(timeout, int) or timeout < 1 or timeout > 300:
            errors.append("timeout must be an integer between 1 and 300 seconds")
        
        return ValidationResult(ok=len(errors) == 0, errors=errors)

    async def test_connection(self, config: dict, credentials: dict) -> TestResult:
        """Test Webflow connection and validate credentials."""
        api_token = credentials.get("api_token", "")
        if not api_token:
            return TestResult(ok=False, error="API token is required")
        
        site_id = config["site_id"]
        collection_id = config["collection_id"]
        timeout = config.get("timeout", 30)
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Version": "1.0.0"
        }
        
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            try:
                # Test site access
                site_resp = await client.get(f"{self.api_base}/sites/{site_id}")
                if site_resp.status_code == 401:
                    return TestResult(ok=False, error="Webflow authentication failed — check API token")
                if site_resp.status_code == 403:
                    return TestResult(ok=False, error="Webflow access forbidden — check token permissions")
                if site_resp.status_code == 404:
                    return TestResult(ok=False, error=f"Webflow site not found: {site_id}")
                if site_resp.status_code != 200:
                    return TestResult(ok=False, error=f"Webflow site API error: {site_resp.status_code}")
                
                site_data = site_resp.json()
                
                # Test collection access
                collection_resp = await client.get(f"{self.api_base}/collections/{collection_id}")
                if collection_resp.status_code == 404:
                    return TestResult(ok=False, error=f"Webflow collection not found: {collection_id}")
                if collection_resp.status_code != 200:
                    return TestResult(ok=False, error=f"Webflow collection API error: {collection_resp.status_code}")
                
                collection_data = collection_resp.json()
                
                return TestResult(
                    ok=True,
                    site_info={
                        "site_name": site_data.get("displayName", "Unknown Site"),
                        "site_url": self._get_site_url(site_data),
                        "collection_name": collection_data.get("displayName", "Unknown Collection"),
                        "collection_slug": collection_data.get("slug", ""),
                        "field_count": len(collection_data.get("fields", [])),
                    }
                )
                
            except httpx.RequestError as e:
                return TestResult(ok=False, error=f"Network error: {e}")

    async def publish(self, config: dict, credentials: dict, payload: PublishPayload) -> PublishResult:
        """Publish content to Webflow CMS."""
        api_token = credentials.get("api_token", "")
        site_id = config["site_id"]
        collection_id = config["collection_id"]
        auto_publish = config.get("auto_publish", True)
        default_status = config.get("default_status", "published")
        timeout = config.get("timeout", 30)
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Version": "1.0.0"
        }
        
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            try:
                # First, get collection schema for proper field mapping
                collection_resp = await client.get(f"{self.api_base}/collections/{collection_id}")
                if collection_resp.status_code != 200:
                    raise Exception(f"Failed to get collection schema: {collection_resp.status_code}")
                
                collection_data = collection_resp.json()
                collection_fields = {field['slug']: field for field in collection_data.get('fields', [])}
                
                # Prepare Webflow item data
                item_data = await self._prepare_webflow_item(
                    payload, collection_fields, default_status, config
                )
                
                # Create the item
                create_resp = await client.post(
                    f"{self.api_base}/collections/{collection_id}/items",
                    json=item_data
                )
                
                if create_resp.status_code not in [200, 201]:
                    raise Exception(f"Item creation failed: {create_resp.status_code} - {create_resp.text}")
                
                result = create_resp.json()
                item_id = result.get("id")
                
                if not item_id:
                    raise Exception("Item created but no ID returned")
                
                # Auto-publish if configured
                published_at = None
                if auto_publish and default_status == "published":
                    publish_success = await self._publish_item(client, collection_id, item_id)
                    if publish_success:
                        published_at = datetime.now(timezone.utc).isoformat()
                
                # Get the site URL for public link
                site_resp = await client.get(f"{self.api_base}/sites/{site_id}")
                site_data = site_resp.json() if site_resp.status_code == 200 else {}
                site_url = self._get_site_url(site_data)
                
                # Construct public URL
                slug = payload.slug or self._sanitize_slug(payload.title)
                public_url = f"{site_url}/blog/{slug}" if slug else f"{site_url}/blog"
                
                return PublishResult(
                    external_id=item_id,
                    public_url=public_url,
                    published_at=published_at,
                    raw_response=result
                )
                
            except httpx.RequestError as e:
                raise Exception(f"Network error: {e}")

    async def revoke(self, config: dict, credentials: dict) -> None:
        """Clean up Webflow integration (no specific cleanup needed for API tokens)."""
        # Webflow API tokens don't require specific revocation
        # They're managed in the Webflow dashboard
        logger.info("Webflow integration disconnected (no cleanup required)")

    def _get_site_url(self, site_data: dict) -> str:
        """Get the live site URL from site data."""
        # Try custom domain first, then Webflow subdomain
        custom_domain = site_data.get("customDomains", [])
        if custom_domain:
            return f"https://{custom_domain[0]}"
        
        short_name = site_data.get("shortName", "")
        if short_name:
            return f"https://{short_name}.webflow.io"
        
        # Fallback
        return f"https://webflow.io"

    async def _prepare_webflow_item(
        self, 
        payload: PublishPayload, 
        collection_fields: dict, 
        default_status: str,
        config: dict
    ) -> dict:
        """Prepare content for Webflow CMS item format."""
        item_data = {
            "isArchived": False,
            "isDraft": default_status != "published",
            "fieldData": {}
        }
        
        field_data = item_data["fieldData"]
        
        # Map standard fields
        field_data["name"] = payload.title  # Standard CMS name field
        
        if payload.slug:
            field_data["slug"] = self._sanitize_slug(payload.slug)
        
        # Map content to appropriate rich text field
        if payload.merged_html:
            content_field = self._find_content_field(collection_fields)
            if content_field:
                field_data[content_field] = payload.merged_html
        
        # Map meta description
        if payload.meta_description:
            meta_field = self._find_meta_description_field(collection_fields)
            if meta_field:
                field_data[meta_field] = payload.meta_description
        
        # Map featured image
        if payload.featured_image_url:
            image_field = config.get("featured_image_field", "featured-image")
            if image_field in collection_fields:
                field_data[image_field] = {"url": payload.featured_image_url}
        
        # Map tags
        if payload.tags:
            tags_field = self._find_tags_field(collection_fields)
            if tags_field:
                field_data[tags_field] = ", ".join(payload.tags)
        
        # Add publication date
        current_time = datetime.now(timezone.utc).isoformat()
        date_field = self._find_date_field(collection_fields)
        if date_field:
            field_data[date_field] = current_time
        
        return item_data

    def _find_content_field(self, collection_fields: dict) -> Optional[str]:
        """Find the main content field in the collection."""
        # Common content field names
        content_candidates = ["post-body", "content", "body", "description", "text"]
        
        # Look for exact matches first
        for candidate in content_candidates:
            if candidate in collection_fields and collection_fields[candidate].get("type") == "RichText":
                return candidate
        
        # Fallback to first RichText field
        for slug, field in collection_fields.items():
            if field.get("type") == "RichText":
                return slug
        
        return None

    def _find_meta_description_field(self, collection_fields: dict) -> Optional[str]:
        """Find the meta description field."""
        meta_candidates = ["meta-description", "seo-description", "description", "excerpt"]
        
        for candidate in meta_candidates:
            if candidate in collection_fields:
                field_type = collection_fields[candidate].get("type")
                if field_type in ["PlainText", "RichText"]:
                    return candidate
        
        return None

    def _find_tags_field(self, collection_fields: dict) -> Optional[str]:
        """Find the tags/categories field."""
        tag_candidates = ["tags", "categories", "keywords", "labels"]
        
        for candidate in tag_candidates:
            if candidate in collection_fields:
                field_type = collection_fields[candidate].get("type")
                if field_type in ["PlainText", "RichText"]:
                    return candidate
        
        return None

    def _find_date_field(self, collection_fields: dict) -> Optional[str]:
        """Find the publication date field."""
        date_candidates = ["published-date", "date", "created-date", "publish-date"]
        
        for candidate in date_candidates:
            if candidate in collection_fields and collection_fields[candidate].get("type") == "DateTime":
                return candidate
        
        return None

    def _sanitize_slug(self, slug: str) -> str:
        """Sanitize slug for Webflow URL requirements."""
        if not slug:
            return ""
        
        # Convert to lowercase and replace spaces with hyphens
        slug = slug.strip().lower().replace(" ", "-")
        
        # Remove any characters that aren't alphanumeric or hyphens
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        
        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        
        # Remove leading/trailing hyphens
        slug = slug.strip("-")
        
        return slug

    async def _publish_item(self, client: httpx.AsyncClient, collection_id: str, item_id: str) -> bool:
        """Publish a specific item in Webflow."""
        try:
            publish_data = {"itemIds": [item_id]}
            
            response = await client.post(
                f"{self.api_base}/collections/{collection_id}/items/publish",
                json=publish_data
            )
            
            return response.status_code in [200, 202]
            
        except Exception as e:
            logger.error(f"Error publishing Webflow item {item_id}: {e}")
            return False