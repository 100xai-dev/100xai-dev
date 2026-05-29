from __future__ import annotations

from app.integrations.base import (
    IntegrationProvider,
    PublishPayload,
    PublishResult,
    TestResult,
    ValidationResult,
)
from app.integrations.wordpress import WordPressProvider


class _ProviderStub(IntegrationProvider):
    """Stub for providers not yet implemented."""

    provider_name: str = "stub"

    async def validate_config(self, config: dict) -> ValidationResult:
        return ValidationResult(
            ok=False,
            errors=[f"{self.provider_name.capitalize()} integration not yet implemented"],
        )

    async def test_connection(self, config: dict, credentials: dict) -> TestResult:
        return TestResult(ok=False, error=f"{self.provider_name.capitalize()} integration not yet implemented")

    async def publish(self, config: dict, credentials: dict, payload: PublishPayload) -> PublishResult:
        raise NotImplementedError(f"{self.provider_name} publish not yet implemented")

    async def revoke(self, config: dict, credentials: dict) -> None:
        pass


class ShopifyProviderStub(_ProviderStub):
    provider_name = "shopify"


class WebflowProviderStub(_ProviderStub):
    provider_name = "webflow"


class CustomAPIProviderStub(_ProviderStub):
    provider_name = "custom_api"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class UnknownProviderError(Exception):
    pass


PROVIDERS: dict[str, type[IntegrationProvider]] = {
    "wordpress": WordPressProvider,
    "shopify": ShopifyProviderStub,
    "webflow": WebflowProviderStub,
    "custom_api": CustomAPIProviderStub,
}


def get_provider(name: str) -> IntegrationProvider:
    if name not in PROVIDERS:
        raise UnknownProviderError(f"Unknown provider: {name}")
    return PROVIDERS[name]()
