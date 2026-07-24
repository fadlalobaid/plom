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
        docs_url=None,
    redoc_url=None,
    openapi_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
    ],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() :
    return """
    <html>
        <head>
            <title>PulmoScan API</title>
        </head>
        <body>
            <h1>PulmoScan Backend API</h1>
            <p>Status: Active ✅</p>
            <p>FastAPI Backend is running successfully</p>
        </body>
    </html>
 """

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
