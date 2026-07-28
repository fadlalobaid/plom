"""Verify RLS/REVOKE security hardening after migration."""

from __future__ import annotations

from sqlalchemy import create_engine, text

from app.core.config import get_settings

TABLES = (
    "users",
    "patients",
    "xray_images",
    "diagnosis_results",
    "audit_logs",
    "alembic_version",
)


def main() -> None:
    engine = create_engine(get_settings().database_url)

    with engine.connect() as conn:
        print("=== RLS ===")
        rows = conn.execute(
            text(
                """
                SELECT c.relname AS table_name,
                       c.relrowsecurity AS rls_enabled,
                       c.relforcerowsecurity AS rls_forced
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relkind = 'r'
                  AND c.relname = ANY(:tables)
                ORDER BY c.relname
                """
            ),
            {"tables": list(TABLES)},
        ).mappings()
        for row in rows:
            print(dict(row))

        print("=== POLICIES ===")
        policies = conn.execute(
            text(
                """
                SELECT tablename, policyname
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = ANY(:tables)
                """
            ),
            {"tables": list(TABLES)},
        ).mappings().all()
        print("policy_count", len(policies), policies)

        print("=== GRANTS anon/authenticated ===")
        grants = conn.execute(
            text(
                """
                SELECT table_name, grantee,
                       string_agg(privilege_type, ', ' ORDER BY privilege_type)
                         AS privileges
                FROM information_schema.role_table_grants
                WHERE table_schema = 'public'
                  AND table_name = ANY(:tables)
                  AND grantee IN ('anon', 'authenticated')
                GROUP BY table_name, grantee
                ORDER BY table_name, grantee
                """
            ),
            {"tables": list(TABLES)},
        ).mappings().all()
        print("remaining_grants", len(grants))
        for grant in grants:
            print(dict(grant))

        print("=== postgres backend access ===")
        print("users", conn.execute(text("SELECT count(*) FROM public.users")).scalar())
        print(
            "patients",
            conn.execute(text("SELECT count(*) FROM public.patients")).scalar(),
        )
        print(
            "alembic",
            conn.execute(text("SELECT version_num FROM public.alembic_version")).scalar(),
        )

        print("=== storage ===")
        bucket = conn.execute(
            text(
                "SELECT name, public FROM storage.buckets WHERE id = 'xray-images'"
            )
        ).mappings().one()
        print(dict(bucket))
        storage_policies = conn.execute(
            text(
                """
                SELECT count(*) FROM pg_policies
                WHERE schemaname = 'storage' AND tablename = 'objects'
                """
            )
        ).scalar()
        print("storage.objects policies", storage_policies)

    for role in ("anon", "authenticated"):
        print(f"=== {role} blocked ===")
        for table in TABLES:
            with engine.connect() as conn:
                conn.execute(text(f"SET ROLE {role}"))
                try:
                    conn.execute(text(f'SELECT count(*) FROM public."{table}"'))
                    print(table, "UNEXPECTED ACCESS")
                except Exception as exc:  # noqa: BLE001
                    print(table, "BLOCKED:", str(exc).split("\n")[0])
                finally:
                    conn.rollback()

        for table in TABLES:
            with engine.connect() as conn:
                conn.execute(text(f"SET ROLE {role}"))
                try:
                    conn.execute(text(f'INSERT INTO public."{table}" DEFAULT VALUES'))
                    print(table, "UNEXPECTED INSERT")
                except Exception as exc:  # noqa: BLE001
                    print(table, "INSERT BLOCKED:", str(exc).split("\n")[0])
                finally:
                    conn.rollback()


if __name__ == "__main__":
    main()
