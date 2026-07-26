"""restructure users and patients tables

Revision ID: d7e4f91a8b23
Revises: c3a91e7b2d04
Create Date: 2026-07-26 14:20:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7e4f91a8b23"
down_revision: str | Sequence[str] | None = "c3a91e7b2d04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_GOVERNORATE_VALUES = (
    "إدلب",
    "الحسكة",
    "حلب",
    "حماة",
    "حمص",
    "دمشق",
    "درعا",
    "دير الزور",
    "الرقة",
    "ريف دمشق",
    "السويداء",
    "طرطوس",
    "القنيطرة",
    "اللاذقية",
)


def upgrade() -> None:
    """Rename doctors->users and restructure user/patient location fields safely."""
    # Drop foreign keys pointing at doctors.id before renaming the table.
    op.drop_constraint(
        "patients_created_by_doctor_id_fkey",
        "patients",
        type_="foreignkey",
    )
    op.drop_constraint(
        "xray_images_doctor_id_fkey",
        "xray_images",
        type_="foreignkey",
    )
    op.drop_constraint(
        "diagnosis_results_doctor_id_fkey",
        "diagnosis_results",
        type_="foreignkey",
    )
    op.drop_constraint(
        "audit_logs_user_id_fkey",
        "audit_logs",
        type_="foreignkey",
    )

    op.rename_table("doctors", "users")

    op.create_foreign_key(
        "patients_created_by_doctor_id_fkey",
        "patients",
        "users",
        ["created_by_doctor_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "xray_images_doctor_id_fkey",
        "xray_images",
        "users",
        ["doctor_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "diagnosis_results_doctor_id_fkey",
        "diagnosis_results",
        "users",
        ["doctor_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "audit_logs_user_id_fkey",
        "audit_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- users required profile fields ---
    op.add_column("users", sa.Column("governorate", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("area", sa.String(length=255), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE users
            SET specialization = COALESCE(NULLIF(TRIM(specialization), ''), 'General')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET date_of_birth = COALESCE(date_of_birth, DATE '1990-01-01')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET phone_number = CASE
                WHEN phone_number ~ '^\\d{10}$' THEN phone_number
                WHEN phone_number ~ '^\\+9639\\d{8}$' THEN '0' || substring(phone_number from 5)
                WHEN phone_number ~ '^9639\\d{8}$' THEN '0' || substring(phone_number from 4)
                ELSE '0900000000'
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET governorate = COALESCE(governorate, 'دمشق'),
                area = COALESCE(NULLIF(TRIM(area), ''), 'غير محدد')
            """
        )
    )

    op.alter_column("users", "specialization", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("users", "date_of_birth", existing_type=sa.Date(), nullable=False)
    op.alter_column(
        "users",
        "phone_number",
        existing_type=sa.String(length=50),
        type_=sa.String(length=10),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column("users", "governorate", existing_type=sa.String(length=50), nullable=False)
    op.alter_column("users", "area", existing_type=sa.String(length=255), nullable=False)

    # --- patients restructure ---
    op.add_column("patients", sa.Column("governorate", sa.String(length=50), nullable=True))
    op.add_column("patients", sa.Column("area", sa.String(length=255), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE patients
            SET first_name = COALESCE(NULLIF(TRIM(first_name), ''), 'Unknown'),
                father_name = COALESCE(NULLIF(TRIM(father_name), ''), 'Unknown'),
                mother_name = COALESCE(NULLIF(TRIM(mother_name), ''), 'Unknown'),
                last_name = COALESCE(NULLIF(TRIM(last_name), ''), 'Unknown'),
                governorate = COALESCE(governorate, 'دمشق'),
                area = COALESCE(
                    NULLIF(TRIM(area), ''),
                    COALESCE(NULLIF(TRIM(address), ''), 'غير محدد')
                ),
                phone_number = CASE
                    WHEN phone_number IS NULL OR TRIM(phone_number) = '' THEN NULL
                    WHEN phone_number ~ '^\\d{10}$' THEN phone_number
                    WHEN phone_number ~ '^\\+9639\\d{8}$' THEN '0' || substring(phone_number from 5)
                    WHEN phone_number ~ '^9639\\d{8}$' THEN '0' || substring(phone_number from 4)
                    ELSE NULL
                END
            """
        )
    )

    op.alter_column("patients", "first_name", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("patients", "father_name", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("patients", "mother_name", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("patients", "last_name", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("patients", "governorate", existing_type=sa.String(length=50), nullable=False)
    op.alter_column("patients", "area", existing_type=sa.String(length=255), nullable=False)
    op.alter_column(
        "patients",
        "phone_number",
        existing_type=sa.String(length=50),
        type_=sa.String(length=10),
        existing_nullable=True,
        nullable=True,
    )

    op.drop_column("patients", "full_name")
    op.drop_column("patients", "address")


def downgrade() -> None:
    """Best-effort reverse migration for the users/patients restructure."""
    op.add_column("patients", sa.Column("address", sa.String(length=500), nullable=True))
    op.add_column("patients", sa.Column("full_name", sa.String(length=255), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE patients
            SET full_name = TRIM(CONCAT_WS(' ', first_name, father_name, last_name)),
                address = area
            """
        )
    )
    op.alter_column("patients", "full_name", existing_type=sa.String(length=255), nullable=False)

    op.drop_column("patients", "area")
    op.drop_column("patients", "governorate")
    op.alter_column(
        "patients",
        "phone_number",
        existing_type=sa.String(length=10),
        type_=sa.String(length=50),
        existing_nullable=True,
        nullable=True,
    )
    op.alter_column("patients", "first_name", existing_type=sa.String(length=255), nullable=True)
    op.alter_column("patients", "father_name", existing_type=sa.String(length=255), nullable=True)
    op.alter_column("patients", "mother_name", existing_type=sa.String(length=255), nullable=True)
    op.alter_column("patients", "last_name", existing_type=sa.String(length=255), nullable=True)

    op.drop_column("users", "area")
    op.drop_column("users", "governorate")
    op.alter_column(
        "users",
        "phone_number",
        existing_type=sa.String(length=10),
        type_=sa.String(length=50),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column("users", "date_of_birth", existing_type=sa.Date(), nullable=True)
    op.alter_column("users", "specialization", existing_type=sa.String(length=255), nullable=True)

    op.drop_constraint("audit_logs_user_id_fkey", "audit_logs", type_="foreignkey")
    op.drop_constraint("diagnosis_results_doctor_id_fkey", "diagnosis_results", type_="foreignkey")
    op.drop_constraint("xray_images_doctor_id_fkey", "xray_images", type_="foreignkey")
    op.drop_constraint("patients_created_by_doctor_id_fkey", "patients", type_="foreignkey")

    op.rename_table("users", "doctors")

    op.create_foreign_key(
        "patients_created_by_doctor_id_fkey",
        "patients",
        "doctors",
        ["created_by_doctor_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "xray_images_doctor_id_fkey",
        "xray_images",
        "doctors",
        ["doctor_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "diagnosis_results_doctor_id_fkey",
        "diagnosis_results",
        "doctors",
        ["doctor_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "audit_logs_user_id_fkey",
        "audit_logs",
        "doctors",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Keep unused constant referenced for documentation of allowed values.
    _ = _GOVERNORATE_VALUES
