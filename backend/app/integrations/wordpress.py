from datetime import datetime

import httpx

from app.integrations.base import (
    IntegrationProvider,
    PublishPayload,
    PublishResult,
    TestResult,
    ValidationResult,
)


class WordPressProvider(IntegrationProvider):
    provider_name = "wordpress"

    async def validate_config(self, config: dict) -> ValidationResult:
        errors = []
        if not config.get("site_url"):
            errors.append("site_url is required")
        if config.get("default_status", "draft") not in {"draft", "publish"}:
            errors.append("default_status must be draft or publish")
        return ValidationResult(ok=not errors, errors=errors)

    async def test_connection(self, config: dict, credentials: dict) -> TestResult:
        site_url = config["site_url"].rstrip("/")
        auth = (credentials["username"], credentials["application_password"])
        async with httpx.AsyncClient(timeout=15, auth=auth) as client:
            try:
                rest_response = await client.get(f"{site_url}/wp-json/")
                if rest_response.status_code != 200:
                    return TestResult(
                        ok=False,
                        error=f"REST API not reachable (HTTP {rest_response.status_code})",
                    )
                site_info = rest_response.json()

                user_response = await client.get(f"{site_url}/wp-json/wp/v2/users/me")
                if user_response.status_code == 401:
                    return TestResult(
                        ok=False,
                        error="Authentication failed - check username and application password",
                    )
                if user_response.status_code != 200:
                    return TestResult(
                        ok=False,
                        error=f"Auth check failed (HTTP {user_response.status_code})",
                    )
                user_info = user_response.json()
            except httpx.RequestError as exc:
                return TestResult(ok=False, error=f"Network error: {exc}")

        capabilities = user_info.get("capabilities", {})
        if not (capabilities.get("publish_posts") or capabilities.get("edit_posts")):
            return TestResult(ok=False, error="User lacks publish/edit capability for posts")
        return TestResult(
            ok=True,
            site_info={
                "name": site_info.get("name", ""),
                "description": site_info.get("description", ""),
                "url": site_info.get("url", site_url),
                "user_display_name": user_info.get("name", ""),
                "user_capabilities": list(capabilities.keys()),
            },
        )

    async def publish(self, config: dict, credentials: dict, payload: PublishPayload) -> PublishResult:
        site_url = config["site_url"].rstrip("/")
        auth = (credentials["username"], credentials["application_password"])
        post_data = {
            "title": payload.title,
            "slug": payload.slug,
            "content": payload.merged_html,
            "excerpt": payload.meta_description,
            "status": config.get("default_status", "draft"),
            "categories": config.get("default_categories", []),
            "tags": payload.tags or config.get("default_tags", []),
        }
        if config.get("default_author_id"):
            post_data["author"] = config["default_author_id"]
        async with httpx.AsyncClient(timeout=30, auth=auth) as client:
            response = await client.post(f"{site_url}/wp-json/wp/v2/posts", json=post_data)
            response.raise_for_status()
            post = response.json()
        return PublishResult(
            external_id=str(post["id"]),
            public_url=post["link"],
            published_at=datetime.fromisoformat(post["date_gmt"].replace("Z", "+00:00"))
            if post.get("date_gmt")
            else None,
            raw_response=post,
        )

    async def revoke(self, config: dict, credentials: dict) -> None:
        return None

