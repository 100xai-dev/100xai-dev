"""superadmin: organization status + user disabled

Revision ID: 20260619_0014
Revises: 20260612_0013
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20260619_0014"
down_revision = "20260612_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
    )
    op.add_column(
        "users",
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "disabled")
    op.drop_column("organizations", "status")
