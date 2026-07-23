"""preserve password flag rollout default

Revision ID: 8c44b32f4d6f
Revises: b644742109fd
Create Date: 2026-07-23 18:31:32.343335

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8c44b32f4d6f"
down_revision: str | Sequence[str] | None = "b644742109fd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Keep old application instances able to insert accounts during rollout."""
    op.alter_column(
        "doctors",
        "must_change_password",
        server_default=sa.false(),
    )


def downgrade() -> None:
    """Remove the compatibility default while retaining the column."""
    op.alter_column(
        "doctors",
        "must_change_password",
        server_default=None,
    )
