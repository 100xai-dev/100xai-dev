"""Add logo_url to brand_profiles

Revision ID: 20260612_0012
Revises: 20260609_0011
Create Date: 2026-06-12
"""

import sqlalchemy as sa
from alembic import op

revision = "20260612_0012"
down_revision = "20260609_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("brand_profiles", sa.Column("logo_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("brand_profiles", "logo_url")
