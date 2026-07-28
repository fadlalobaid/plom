"""enable RLS and secure public tables from Data API

Revision ID: e8f2a1b3c4d5
Revises: d7e4f91a8b23
Create Date: 2026-07-28 13:50:00.000000

Security-only migration (no schema shape changes).

Context
-------
PulmoScan clients must access data only through FastAPI.
Supabase PostgREST roles ``anon`` / ``authenticated`` must not read or write
application tables directly.

FastAPI connects as PostgreSQL role ``postgres``, which has ``rolbypassrls``
enabled on Supabase. Therefore ENABLE ROW LEVEL SECURITY without FORCE is safe
for the backend, while still blocking Data API roles subject to RLS.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8f2a1b3c4d5"
down_revision: str | Sequence[str] | None = "d7e4f91a8b23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SENSITIVE_TABLES = (
    "users",
    "patients",
    "xray_images",
    "diagnosis_results",
    "audit_logs",
)
_INTERNAL_TABLES = ("alembic_version",)
_ALL_SECURED_TABLES = _SENSITIVE_TABLES + _INTERNAL_TABLES


def upgrade() -> None:
    # 1) Enable RLS (no FORCE — table owners / bypassrls roles keep full access).
    #    No permissive policies are created for anon/authenticated.
    for table_name in _ALL_SECURED_TABLES:
        op.execute(f'ALTER TABLE public."{table_name}" ENABLE ROW LEVEL SECURITY')

    # 2) Revoke direct Data API privileges.
    for table_name in _ALL_SECURED_TABLES:
        op.execute(
            f'REVOKE ALL ON TABLE public."{table_name}" FROM anon, authenticated'
        )

    # 3) Stop auto-granting future public tables/sequences/functions created by
    #    the postgres role to anon/authenticated (common Supabase default).
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "REVOKE ALL ON TABLES FROM anon, authenticated"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "REVOKE ALL ON SEQUENCES FROM anon, authenticated"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "REVOKE ALL ON FUNCTIONS FROM anon, authenticated"
    )


def downgrade() -> None:
    # Restore previous default privilege behavior for role postgres.
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "GRANT ALL ON TABLES TO anon, authenticated"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "GRANT ALL ON SEQUENCES TO anon, authenticated"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "GRANT ALL ON FUNCTIONS TO anon, authenticated"
    )

    for table_name in _ALL_SECURED_TABLES:
        op.execute(
            f'GRANT ALL ON TABLE public."{table_name}" TO anon, authenticated'
        )
        op.execute(f'ALTER TABLE public."{table_name}" DISABLE ROW LEVEL SECURITY')
