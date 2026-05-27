from app.integrations.base import IntegrationProvider, PublishPayload, PublishResult, TestResult, ValidationResult


class NotImplementedProvider(IntegrationProvider):
    provider_name = "not_implemented"

    async def validate_config(self, config: dict) -> ValidationResult:
        return ValidationResult(ok=False, errors=[f"{self.provider_name} integration not yet implemented"])

    async def test_connection(self, config: dict, credentials: dict) -> TestResult:
        return TestResult(ok=False, error=f"{self.provider_name} integration not yet implemented")

    async def publish(self, config: dict, credentials: dict, payload: PublishPayload) -> PublishResult:
        raise NotImplementedError(f"{self.provider_name} publish not yet implemented")

    async def revoke(self, config: dict, credentials: dict) -> None:
        return None


class ShopifyProviderStub(NotImplementedProvider):
    provider_name = "shopify"


class WebflowProviderStub(NotImplementedProvider):
    provider_name = "webflow"


class CustomAPIProviderStub(NotImplementedProvider):
    provider_name = "custom_api"

