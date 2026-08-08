"""Verify ORM models load and register with SQLAlchemy metadata."""

from app.db.base import Base
from app.models import AuthSession, DiagnosisResult, Doctor, Patient, XrayImage

MODELS: list[type] = [
    Doctor,
    Patient,
    XrayImage,
    DiagnosisResult,
    AuthSession,
]


def load_models() -> list[type]:
    """Import and return all active ORM models."""
    assert "must_change_password" in Doctor.__table__.columns
    assert Doctor.__tablename__ == "users"
    assert "full_name" not in Patient.__table__.columns
    assert "address" not in Patient.__table__.columns
    assert "governorate" in Patient.__table__.columns
    assert AuthSession.__tablename__ == "auth_sessions"
    assert "refresh_token_hash" in AuthSession.__table__.columns
    return MODELS


def main() -> None:
    models = load_models()
    tables = sorted(Base.metadata.tables.keys())
    print(f"Loaded {len(models)} models.")
    print(f"Registered tables: {', '.join(tables)}")


if __name__ == "__main__":
    main()
