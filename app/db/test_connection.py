"""Database connectivity verification helpers."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def verify_database_connection(db: Session) -> int:
    """Run SELECT 1 using an injected session (for FastAPI dependencies)."""
    return db.execute(text("SELECT 1")).scalar_one()


def test_database_connection() -> None:
    """Standalone CLI check that opens and closes its own session."""
    db = SessionLocal()

    try:
        result = verify_database_connection(db)
        print("Database connection successful:", result)
    except Exception as error:
        print("Database connection failed:", error)
    finally:
        db.close()


if __name__ == "__main__":
    test_database_connection()
