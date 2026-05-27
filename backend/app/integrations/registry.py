from app.integrations.base import IntegrationProvider
from app.integrations.stubs import CustomAPIProviderStub, ShopifyProviderStub, WebflowProviderStub
from app.integrations.wordpress import WordPressProvider


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
        raise UnknownProviderError(name)
    return PROVIDERS[name]()

