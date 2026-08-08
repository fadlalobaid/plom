"""add auth_sessions table for persistent refresh login

Revision ID: a9c4e2f7b1d0
Revises: f1a2b3c4d5e6
Create Date: 2026-08-08 15:20:00.000000

Stores hashed opaque refresh tokens only. Raw refresh tokens are never persisted.
Sessions have no absolute server-side expiry so users remain signed in until
explicit logout or security-driven revocation (tradeoff documented in auth service).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9c4e2f7b1d0"
down_revision: str | Sequence[str] | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create auth_sessions and secure it like other sensitive tables."""
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("doctor_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_created", sa.String(length=45), nullable=True),
        sa.Column("ip_last_used", sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refresh_token_hash", name="uq_auth_sessions_refresh_token_hash"),
    )
    op.create_index(
        op.f("ix_auth_sessions_doctor_id"),
        "auth_sessions",
        ["doctor_id"],
        unique=False,
    )

    # Match existing Supabase Data API hardening for sensitive tables.
    op.execute('ALTER TABLE public."auth_sessions" ENABLE ROW LEVEL SECURITY')
    op.execute(
        'REVOKE ALL ON TABLE public."auth_sessions" FROM anon, authenticated'
    )


def downgrade() -> None:
    """Drop auth_sessions."""
    op.execute(
        'GRANT ALL ON TABLE public."auth_sessions" TO anon, authenticated'
    )
    op.execute('ALTER TABLE public."auth_sessions" DISABLE ROW LEVEL SECURITY')
    op.drop_index(op.f("ix_auth_sessions_doctor_id"), table_name="auth_sessions")
    op.drop_table("auth_sessions")
