"""add forced password change flag

Revision ID: b644742109fd
Revises: 45bf4051d8f8
Create Date: 2026-07-23 18:20:03.778098

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b644742109fd"
down_revision: str | Sequence[str] | None = "45bf4051d8f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the flag while preserving access for all existing accounts."""
    op.add_column(
        "doctors",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column(
        "doctors",
        "must_change_password",
        server_default=None,
    )


def downgrade() -> None:
    """Remove the standalone password-change state flag."""
    op.drop_column("doctors", "must_change_password")
