"""email verification and terms acceptance

Revision ID: 20260609_0010
Revises: 20260607_0009
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa

revision = "20260609_0010"
down_revision = "20260607_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New user columns for email verification + versioned terms acceptance.
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("terms_version_accepted", sa.String(), nullable=True))
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True))

    # Existing accounts are grandfathered in so the new login gate does not lock them out.
    op.execute("UPDATE users SET email_verified = true")

    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_email_verification_tokens_user_id", "email_verification_tokens", ["user_id"])
    op.create_index("ix_email_verification_tokens_token_hash", "email_verification_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_index("ix_email_verification_tokens_token_hash", "email_verification_tokens")
    op.drop_index("ix_email_verification_tokens_user_id", "email_verification_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "terms_version_accepted")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "email_verified")
