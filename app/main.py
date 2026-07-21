from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.db.session import get_db
from app.db.test_connection import verify_database_connection

settings = get_settings()

app = FastAPI(
    title=settings.project_name,
    description=settings.project_description,
    version=settings.project_version,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "PulmoScan Backend API is running successfully",
        "project": settings.project_name,
        "backend": "FastAPI",
        "status": "active",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.environment,
        "version": settings.project_version,
    }


@app.get("/db-check")
def db_check(db: Session = Depends(get_db)) -> dict[str, str | int]:
    result = verify_database_connection(db)
    return {
        "status": "ok",
        "database": "connected",
        "result": result,
    }
