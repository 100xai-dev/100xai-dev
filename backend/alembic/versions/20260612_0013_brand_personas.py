"""Add brand_personas table

Revision ID: 20260612_0013
Revises: 20260612_0012
Create Date: 2026-06-12
"""

import sqlalchemy as sa
from alembic import op

revision = "20260612_0013"
down_revision = "20260612_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brand_personas",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column(
            "brand_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("brands.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("one_liner", sa.Text(), nullable=False, server_default=""),
        sa.Column("audience", sa.Text(), nullable=False, server_default=""),
        sa.Column("tone_tags", sa.JSON(), nullable=True),
        sa.Column("founder_name", sa.String(), nullable=True),
        sa.Column("founder_role", sa.String(), nullable=True),
        sa.Column("mission", sa.Text(), nullable=True),
        sa.Column("accent_color", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("brand_personas")