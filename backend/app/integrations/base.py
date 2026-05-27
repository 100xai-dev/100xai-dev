from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TestResult:
    ok: bool
    site_info: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class PublishPayload:
    title: str
    slug: str
    merged_html: str
    meta_description: str | None = None
    featured_image_url: str | None = None
    tags: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class PublishResult:
    external_id: str
    public_url: str
    published_at: datetime | None
    raw_response: dict[str, Any]


class IntegrationProvider(ABC):
    provider_name: str

    @abstractmethod
    async def validate_config(self, config: dict) -> ValidationResult:
        pass

    @abstractmethod
    async def test_connection(self, config: dict, credentials: dict) -> TestResult:
        pass

    @abstractmethod
    async def publish(self, config: dict, credentials: dict, payload: PublishPayload) -> PublishResult:
        pass

    @abstractmethod
    async def revoke(self, config: dict, credentials: dict) -> None:
        pass

