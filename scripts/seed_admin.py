from __future__ import annotations

import sys
from pathlib import Path

# Ensure the backend package root is on sys.path when running as a script.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import get_password_hash, validate_admin_seed_password
from app.db.session import SessionLocal
from app.models.doctor import Doctor
from app.models.enums import DoctorRole, DoctorStatus

def seed_admin() -> None:
    """Create the default Admin account only if it does not already exist."""
    settings = get_settings()
    admin_password = validate_admin_seed_password(settings.first_admin_password)
    db = SessionLocal()

    try:
        existing_admin = db.scalar(
            select(Doctor).where(Doctor.email == settings.first_admin_email)
        )
        if existing_admin is not None:
            print("Admin already exists")
            return

        admin = Doctor(
            full_name=settings.first_admin_full_name,
            email=settings.first_admin_email,
            password_hash=get_password_hash(admin_password),
            role=DoctorRole.ADMIN,
            status=DoctorStatus.ACTIVE,
            must_change_password=False,
        )
        db.add(admin)
        db.commit()
        print("Admin created successfully")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
