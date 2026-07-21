from __future__ import annotations

import sys
from pathlib import Path

# Ensure the backend package root is on sys.path when running as a script.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.doctor import Doctor
from app.models.enums import DoctorRole, DoctorStatus

ADMIN_EMAIL = "admin@sb3.com"
ADMIN_PASSWORD = "admin0021"
ADMIN_FULL_NAME = "System Administrator"


def seed_admin() -> None:
    """Create the default Admin account only if it does not already exist."""
    db = SessionLocal()

    try:
        existing_admin = db.scalar(
            select(Doctor).where(Doctor.email == ADMIN_EMAIL)
        )
        if existing_admin is not None:
            print("Admin already exists")
            return

        admin = Doctor(
            full_name=ADMIN_FULL_NAME,
            email=ADMIN_EMAIL,
            password_hash=get_password_hash(ADMIN_PASSWORD),
            role=DoctorRole.ADMIN,
            status=DoctorStatus.ACTIVE,
        )
        db.add(admin)
        db.commit()
        print("Admin created successfully")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
