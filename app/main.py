from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>PulmoScan API</title>
        <style>
            :root {
                color-scheme: dark;
                font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont,
                    "Segoe UI", sans-serif;
            }

            * {
                box-sizing: border-box;
            }

            body {
                min-height: 100vh;
                margin: 0;
                display: grid;
                place-items: center;
                overflow: hidden;
                color: #eaf6ff;
                background:
                    radial-gradient(circle at 15% 20%, #164e63 0, transparent 32%),
                    radial-gradient(circle at 85% 80%, #1e3a8a 0, transparent 30%),
                    #07111f;
            }

            body::before,
            body::after {
                content: "";
                position: fixed;
                width: 18rem;
                height: 18rem;
                border-radius: 50%;
                filter: blur(80px);
                opacity: 0.25;
                pointer-events: none;
            }

            body::before {
                top: -7rem;
                right: -4rem;
                background: #22d3ee;
            }

            body::after {
                bottom: -8rem;
                left: -4rem;
                background: #3b82f6;
            }

            main {
                width: min(92%, 680px);
                padding: clamp(2rem, 6vw, 4rem);
                text-align: center;
                border: 1px solid rgba(148, 211, 255, 0.18);
                border-radius: 28px;
                background: rgba(9, 24, 42, 0.72);
                box-shadow: 0 32px 80px rgba(0, 0, 0, 0.35);
                backdrop-filter: blur(20px);
            }

            .logo {
                width: 74px;
                height: 74px;
                margin: 0 auto 1.5rem;
                display: grid;
                place-items: center;
                border-radius: 22px;
                color: #07111f;
                font-size: 2rem;
                background: linear-gradient(135deg, #67e8f9, #60a5fa);
                box-shadow: 0 14px 35px rgba(34, 211, 238, 0.25);
            }

            h1 {
                margin: 0;
                font-size: clamp(2rem, 7vw, 3.5rem);
                letter-spacing: -0.04em;
                line-height: 1.05;
            }

            h1 span {
                color: #67e8f9;
            }

            .description {
                max-width: 480px;
                margin: 1.25rem auto 2rem;
                color: #a9bfd2;
                font-size: 1.05rem;
                line-height: 1.7;
            }

            .status {
                display: inline-flex;
                align-items: center;
                gap: 0.65rem;
                padding: 0.7rem 1rem;
                border: 1px solid rgba(74, 222, 128, 0.2);
                border-radius: 999px;
                color: #bbf7d0;
                background: rgba(34, 197, 94, 0.08);
                font-weight: 600;
            }

            .status-dot {
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background: #4ade80;
                box-shadow: 0 0 0 6px rgba(74, 222, 128, 0.12);
                animation: pulse 2s infinite;
            }

            footer {
                margin-top: 2rem;
                color: #668099;
                font-size: 0.85rem;
            }

            @keyframes pulse {
                50% {
                    box-shadow: 0 0 0 10px rgba(74, 222, 128, 0);
                }
            }
        </style>
    </head>
    <body>
        <main>
            <div class="logo" aria-hidden="true">🫁</div>
            <h1>Pulmo<span>Scan</span> API</h1>
            <p class="description">
                Intelligent lung diagnosis backend services are ready and
                operating normally.
            </p>
            <div class="status">
                <span class="status-dot" aria-hidden="true"></span>
                All systems operational
            </div>
            <footer>Powered by FastAPI</footer>
        </main>
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
