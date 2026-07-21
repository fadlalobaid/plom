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
    return MODELS


def main() -> None:
    tables = sorted(Base.metadata.tables.keys())
    print(f"Loaded {len(MODELS)} models.")
    print(f"Registered tables: {', '.join(tables)}")


if __name__ == "__main__":
    main()
