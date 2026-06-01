"""add visual content fields to brand knowledge sources

Revision ID: 20260601_0006
Revises: 20260601_0005
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "20260601_0006"
down_revision = "20260601_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("brand_knowledge_sources", sa.Column("screenshot_url", sa.String(), nullable=True))
    op.add_column("brand_knowledge_sources", sa.Column("html_content", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("brand_knowledge_sources", "html_content")
    op.drop_column("brand_knowledge_sources", "screenshot_url")