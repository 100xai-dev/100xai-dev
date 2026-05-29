from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class TestResult:
    ok: bool
    error: str | None = None
    site_info: dict = field(default_factory=dict)


@dataclass
class PublishPayload:
    title: str
    slug: str
    merged_html: str
    meta_description: str = ""
    featured_image_url: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class PublishResult:
    external_id: str
    public_url: str
    published_at: str | None = None
    raw_response: dict = field(default_factory=dict)


class IntegrationProvider(ABC):
    """Base class for all integration providers."""

    provider_name: str

    @abstractmethod
    async def validate_config(self, config: dict) -> ValidationResult:
        """Validate config shape (no network call)."""

    @abstractmethod
    async def test_connection(self, config: dict, credentials: dict) -> TestResult:
        """Make a real call to verify credentials."""

    @abstractmethod
    async def publish(self, config: dict, credentials: dict, payload: PublishPayload) -> PublishResult:
        """Publish content. Used by blog pipeline."""

    @abstractmethod
    async def revoke(self, config: dict, credentials: dict) -> None:
        """Clean up remote state on disconnect."""
