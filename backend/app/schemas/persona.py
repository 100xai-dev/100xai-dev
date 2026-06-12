from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PersonaContent(BaseModel):
    """Persona input — the raw onboarding fields."""

    name: str = Field(..., min_length=1, max_length=200)
    domain: str | None = None
    url: str | None = None
    one_liner: str = ""
    audience: str = ""
    tone_tags: list[str] = Field(default_factory=list)
    founder_name: str | None = None
    founder_role: str | None = None
    mission: str | None = None
    accent_color: str | None = None


class PersonaOut(PersonaContent):
    id: str
    brand_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)