import pytest
from pydantic import ValidationError

from app.schemas.brand_profile import BrandProfileContent


def test_brand_profile_content_accepts_required_shape() -> None:
    profile = BrandProfileContent(
        name="Acme",
        site_url="https://acme.com",
        one_liner="Acme helps teams publish better content.",
        industry="Marketing",
        allowed_topics=["content strategy"],
        audience_personas=["founders building a repeatable marketing engine"],
        tone_rules="Clear, direct, and practical. Avoid hype.",
        banned_phrases=["delve"],
        unique_angle="Brand memory first",
        ctas=["Book a strategy call"],
    )

    assert profile.name == "Acme"
    assert profile.ctas == ["Book a strategy call"]


def test_brand_profile_content_rejects_missing_required_arrays() -> None:
    with pytest.raises(ValidationError):
        BrandProfileContent(
            name="Acme",
            one_liner="Acme helps teams publish better content.",
            tone_rules="Clear, direct, and practical. Avoid hype.",
            banned_phrases=[],
            unique_angle="Brand memory first",
            ctas=["Book a strategy call"],
        )

