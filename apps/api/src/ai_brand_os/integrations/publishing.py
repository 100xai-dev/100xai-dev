from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PublishPayload:
    title: str
    slug: str
    merged_html: str
    meta_title: str | None = None
    meta_description: str | None = None
    featured_image_url: str | None = None
    status: str = "draft"


@dataclass(frozen=True)
class PublishResult:
    external_id: str
    public_url: str
    raw_response: dict


class PublishAdapter(Protocol):
    def publish(self, payload: PublishPayload) -> PublishResult:
        """Publish content to a CMS and return provider metadata."""

