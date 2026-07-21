"""Seed the first admin account from application settings."""

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.doctor import Doctor
from app.models.enums import DoctorRole, DoctorStatus


def seed_admin() -> None:
    """Create the first admin account when it does not already exist."""
    settings = get_settings()
    db = SessionLocal()

    try:
        existing_admin = db.scalar(
            select(Doctor).where(Doctor.email == settings.first_admin_email)
        )
        if existing_admin is not None:
            print(f"Admin already exists: {settings.first_admin_email}")
            return

        admin = Doctor(
            full_name=settings.first_admin_full_name,
            email=settings.first_admin_email,
            password_hash=get_password_hash(settings.first_admin_password),
            role=DoctorRole.ADMIN,
            status=DoctorStatus.ACTIVE,
        )
        db.add(admin)
        db.commit()
        print(f"Admin created: {settings.first_admin_email}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
