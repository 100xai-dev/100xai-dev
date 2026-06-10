from __future__ import annotations

import logging

import httpx

from app.integrations.base import (
    IntegrationProvider,
    PublishPayload,
    PublishResult,
    TestResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class WordPressProvider(IntegrationProvider):
    """
    WordPress REST API integration using Application Passwords (WP 5.6+).
    No plugin required. HTTP Basic Auth with username + app password.
    """

    provider_name = "wordpress"

    WPCOM_API = "https://public-api.wordpress.com/rest/v1.1"

    @staticmethod
    def _is_oauth(config: dict, credentials: dict) -> bool:
        """True when this account is connected via WordPress.com OAuth rather than
        self-hosted Application Passwords."""
        return (config or {}).get("auth_type") == "oauth" or bool((credentials or {}).get("access_token"))

    async def validate_config(self, config: dict) -> ValidationResult:
        errors = []
        if config.get("auth_type") == "oauth":
            if not config.get("blog_id"):
                errors.append("blog_id is required for WordPress.com OAuth")
        elif not config.get("site_url"):
            errors.append("site_url is required")
        if config.get("default_status") not in (None, "draft", "publish"):
            errors.append("default_status must be 'draft' or 'publish'")
        return ValidationResult(ok=len(errors) == 0, errors=errors)

    async def test_connection(self, config: dict, credentials: dict) -> TestResult:
        if self._is_oauth(config, credentials):
            return await self._test_connection_oauth(config, credentials)
        return await self._test_connection_app_password(config, credentials)

    async def _test_connection_oauth(self, config: dict, credentials: dict) -> TestResult:
        token = credentials.get("access_token", "")
        blog_id = config.get("blog_id")
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
            try:
                me = await client.get(f"{self.WPCOM_API}/me")
                if me.status_code == 401:
                    return TestResult(ok=False, error="WordPress.com token rejected — reconnect required")
                if me.status_code != 200:
                    return TestResult(ok=False, error=f"WordPress.com auth check failed (HTTP {me.status_code})")
                site = await client.get(f"{self.WPCOM_API}/sites/{blog_id}")
                site_info = site.json() if site.status_code == 200 else {}
            except httpx.RequestError as e:
                return TestResult(ok=False, error=f"Network error: {e}")
        return TestResult(
            ok=True,
            site_info={
                "name": site_info.get("name", ""),
                "description": site_info.get("description", ""),
                "url": site_info.get("URL", config.get("site_url", "")),
                "user_display_name": me.json().get("display_name", ""),
            },
        )

    async def _test_connection_app_password(self, config: dict, credentials: dict) -> TestResult:
        site_url = config["site_url"].rstrip("/")
        username = credentials.get("username", "")
        app_password = credentials.get("application_password", "")

        auth = (username, app_password)

        async with httpx.AsyncClient(timeout=15, auth=auth, follow_redirects=True) as client:
            # 1. Verify REST API is reachable
            try:
                resp = await client.get(f"{site_url}/wp-json/")
                if resp.status_code != 200:
                    return TestResult(
                        ok=False,
                        error=f"REST API not reachable (HTTP {resp.status_code})",
                    )
                site_info = resp.json()
            except httpx.RequestError as e:
                return TestResult(ok=False, error=f"Network error: {e}")

            # 2. Verify auth by hitting /users/me
            try:
                resp = await client.get(f"{site_url}/wp-json/wp/v2/users/me")
                if resp.status_code == 401:
                    return TestResult(
                        ok=False,
                        error="Authentication failed — check username and application password",
                    )
                if resp.status_code != 200:
                    return TestResult(ok=False, error=f"Auth check failed (HTTP {resp.status_code})")
                user_info = resp.json()
            except httpx.RequestError as e:
                return TestResult(ok=False, error=f"Network error during auth: {e}")

            # 3. Verify write capability
            caps = user_info.get("capabilities", {})
            
            # InstaWP workaround: If capabilities are empty but auth succeeded,
            # try a test post creation to verify actual permissions
            if len(caps) == 0:
                try:
                    # Test with a draft post creation
                    test_post = {
                        "title": "Connection Test (Auto-Delete)",
                        "content": "Temporary test post for integration verification.",
                        "status": "draft"
                    }
                    test_resp = await client.post(f"{site_url}/wp-json/wp/v2/posts", json=test_post)
                    
                    if test_resp.status_code == 201:
                        # Success! User can create posts. Clean up test post.
                        post_data = test_resp.json()
                        post_id = post_data.get("id")
                        if post_id:
                            await client.delete(f"{site_url}/wp-json/wp/v2/posts/{post_id}?force=true")
                        # Assume administrator capabilities if post creation succeeded
                        caps = {"publish_posts": True, "edit_posts": True}
                    elif test_resp.status_code == 403:
                        return TestResult(
                            ok=False,
                            error="User lacks permissions to create posts (verified by test)",
                        )
                except httpx.RequestError:
                    # Network error during test, but auth worked, so continue
                    pass
            
            # Standard capability check (works for normal WordPress, fails for InstaWP)
            if not (caps.get("publish_posts") or caps.get("edit_posts")):
                return TestResult(
                    ok=False,
                    error="User lacks publish/edit capability for posts",
                )

            return TestResult(
                ok=True,
                site_info={
                    "name": site_info.get("name", ""),
                    "description": site_info.get("description", ""),
                    "url": site_info.get("url", site_url),
                    "user_display_name": user_info.get("name", ""),
                    "user_capabilities": list(caps.keys()),
                },
            )

    async def _upload_media(
        self,
        site_url: str,
        auth: tuple[str, str],
        image_url: str,
    ) -> dict:
        """Download image from URL and upload to WP media library."""
        async with httpx.AsyncClient(timeout=30) as client:
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            content_type = img_resp.headers.get("content-type", "image/jpeg")
            filename = image_url.split("/")[-1].split("?")[0] or "featured.jpg"

        async with httpx.AsyncClient(timeout=30, auth=auth) as client:
            resp = await client.post(
                f"{site_url}/wp-json/wp/v2/media",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": content_type,
                },
                content=img_resp.content,
            )
            resp.raise_for_status()
            return resp.json()

    async def publish(self, config: dict, credentials: dict, payload: PublishPayload) -> PublishResult:
        if self._is_oauth(config, credentials):
            return await self._publish_oauth(config, credentials, payload)
        return await self._publish_app_password(config, credentials, payload)

    async def _publish_oauth(self, config: dict, credentials: dict, payload: PublishPayload) -> PublishResult:
        """Publish via the WordPress.com REST v1.1 API using a Bearer token."""
        blog_id = config["blog_id"]
        headers = {"Authorization": f"Bearer {credentials['access_token']}"}
        post_data: dict = {
            "title": payload.title,
            "slug": payload.slug,
            "content": payload.merged_html,
            "excerpt": payload.meta_description,
            "status": config.get("default_status", "draft"),
        }
        if payload.tags:
            post_data["tags"] = ",".join(payload.tags)
        if config.get("default_categories"):
            post_data["categories"] = ",".join(str(c) for c in config["default_categories"])
        if payload.featured_image_url:
            # WP.com sideloads remote images passed via media_urls and attaches the
            # first as the featured image.
            post_data["media_urls"] = [payload.featured_image_url]

        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            resp = await client.post(f"{self.WPCOM_API}/sites/{blog_id}/posts/new", json=post_data)
            resp.raise_for_status()
            post = resp.json()

        return PublishResult(
            external_id=str(post.get("ID")),
            public_url=post.get("URL", ""),
            published_at=post.get("date"),
            raw_response=post,
        )

    async def _publish_app_password(self, config: dict, credentials: dict, payload: PublishPayload) -> PublishResult:
        site_url = config["site_url"].rstrip("/")
        auth = (credentials["username"], credentials["application_password"])

        # 1. Upload featured image if present
        featured_media_id = None
        if payload.featured_image_url:
            try:
                media = await self._upload_media(site_url, auth, payload.featured_image_url)
                featured_media_id = media["id"]
            except Exception as exc:
                logger.warning("Featured image upload failed: %s", exc)

        # 2. Create post
        post_data: dict = {
            "title": payload.title,
            "slug": payload.slug,
            "content": payload.merged_html,
            "excerpt": payload.meta_description,
            "status": config.get("default_status", "draft"),
            "categories": config.get("default_categories", []),
            "tags": payload.tags or config.get("default_tags", []),
        }
        if featured_media_id:
            post_data["featured_media"] = featured_media_id
        if config.get("default_author_id"):
            post_data["author"] = config["default_author_id"]

        async with httpx.AsyncClient(timeout=30, auth=auth) as client:
            resp = await client.post(f"{site_url}/wp-json/wp/v2/posts", json=post_data)
            resp.raise_for_status()
            post = resp.json()

        return PublishResult(
            external_id=str(post["id"]),
            public_url=post["link"],
            published_at=post.get("date_gmt"),
            raw_response=post,
        )

    async def revoke(self, config: dict, credentials: dict) -> None:
        """WordPress Application Passwords don't require remote revocation."""
        pass
