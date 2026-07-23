"""Verify ORM models load and register with SQLAlchemy metadata."""

from app.db.base import Base
from app.models import DiagnosisResult, Doctor, Patient, XrayImage

MODELS: list[type] = [
    Doctor,
    Patient,
    XrayImage,
    DiagnosisResult,
]


def load_models() -> list[type]:
    """Import and return all active ORM models."""
    assert "must_change_password" in Doctor.__table__.columns
    return MODELS


def main() -> None:
    models = load_models()
    tables = sorted(Base.metadata.tables.keys())
    print(f"Loaded {len(models)} models.")
    print(f"Registered tables: {', '.join(tables)}")


if __name__ == "__main__":
    main()
