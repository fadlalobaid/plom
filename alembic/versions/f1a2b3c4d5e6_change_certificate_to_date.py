"""change users.certificate from string to date

Revision ID: f1a2b3c4d5e6
Revises: e8f2a1b3c4d5
Create Date: 2026-07-28 14:10:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "e8f2a1b3c4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Convert optional certificate text to an optional certificate date."""
    op.execute(
        sa.text(
            """
            ALTER TABLE public.users
            ALTER COLUMN certificate TYPE DATE
            USING (
                CASE
                    WHEN certificate IS NULL OR btrim(certificate) = '' THEN NULL
                    WHEN certificate ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                        THEN certificate::date
                    ELSE NULL
                END
            )
            """
        )
    )


def downgrade() -> None:
    """Restore certificate as a free-form string column."""
    op.execute(
        sa.text(
            """
            ALTER TABLE public.users
            ALTER COLUMN certificate TYPE VARCHAR(500)
            USING (
                CASE
                    WHEN certificate IS NULL THEN NULL
                    ELSE to_char(certificate, 'YYYY-MM-DD')
                END
            )
            """
        )
    )
