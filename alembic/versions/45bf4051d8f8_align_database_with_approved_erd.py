"""align database with approved ERD

Revision ID: 45bf4051d8f8
Revises: f8da21c0acab
Create Date: 2026-07-23 17:26:39.756049

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "45bf4051d8f8"
down_revision: str | Sequence[str] | None = "f8da21c0acab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable ERD fields without modifying existing data or contracts."""
    op.add_column("doctors", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column(
        "doctors",
        sa.Column("national_id", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "doctors",
        sa.Column("certificate", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "doctors",
        sa.Column("phone_number", sa.String(length=50), nullable=True),
    )
    op.create_index(
        op.f("ix_doctors_national_id"),
        "doctors",
        ["national_id"],
        unique=True,
    )

    op.add_column(
        "patients",
        sa.Column("first_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "patients",
        sa.Column("father_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "patients",
        sa.Column("mother_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "patients",
        sa.Column("last_name", sa.String(length=255), nullable=True),
    )

    op.add_column(
        "xray_images",
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "xray_images",
        sa.Column("result", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    """Refuse an automatic downgrade that could discard populated ERD fields."""
    raise RuntimeError(
        "Downgrade blocked: removing ERD alignment columns could destroy data. "
        "Create and review an explicit archival migration if rollback is required."
    )
