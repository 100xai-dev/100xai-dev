from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_str


class BrandPersona(Base, TimestampMixin):
    """One brand-persona record per brand (1:1).

    Stores the raw onboarding inputs only; the presentation persona
    (palette, voice cards, beliefs, values) is derived client-side.
    """

    __tablename__ = "brand_personas"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    brand_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    one_liner: Mapped[str] = mapped_column(Text, nullable=False, default="")
    audience: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tone_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    founder_name: Mapped[str | None] = mapped_column(String)
    founder_role: Mapped[str | None] = mapped_column(String)
    mission: Mapped[str | None] = mapped_column(Text)
    accent_color: Mapped[str | None] = mapped_column(String)