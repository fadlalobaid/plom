"""Application configuration loaded from environment variables and a `.env` file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import EmailStr, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production"]

_INSECURE_SECRET_PLACEHOLDER = "change-me-use-a-long-random-secret-in-production"


class Settings(BaseSettings):
    """Centralized application settings for PulmoScan."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    project_name: str = Field(
        default="PulmoScan Backend API",
        description="Display name of the API.",
    )
    project_description: str = Field(
        default=(
            "Backend API for Intelligent Lung Disease Diagnosis System using "
            "Chest X-ray images and clinical data."
        ),
        description="Short description shown in OpenAPI documentation.",
    )
    project_version: str = Field(
        default="1.0.0",
        description="API version string.",
    )
    environment: Environment = Field(
        default="development",
        description="Deployment environment.",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode and verbose error responses.",
    )
    api_v1_prefix: str = Field(
        default="/api/v1",
        description="URL prefix for version 1 API routes.",
    )
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:65167",
            "http://localhost:3000",
            "http://127.0.0.1:65167",
            "http://127.0.0.1:3000",
        ],
        min_length=1,
        description="Browser origins allowed to make cross-origin API requests.",
    )
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/pulmoscan",
        description="SQLAlchemy database connection URL.",
    )
    secret_key: str = Field(
        default=_INSECURE_SECRET_PLACEHOLDER,
        min_length=32,
        description="Secret key used to sign JWT access tokens.",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="Algorithm used to sign and verify JWT access tokens.",
    )
    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        description="Access token lifetime in minutes.",
    )
    upload_dir: Path = Field(
        default=Path("uploads"),
        description="Legacy local upload directory (X-rays now use Supabase Storage).",
    )
    max_xray_upload_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=1,
        description="Maximum allowed X-ray upload size in bytes.",
    )
    supabase_url: str = Field(
        default="",
        description="Supabase project URL used by the backend storage client.",
    )
    supabase_service_role_key: str = Field(
        default="",
        description="Supabase service role key for private Storage access (backend only).",
    )
    supabase_xray_bucket: str = Field(
        default="xray-images",
        min_length=1,
        description="Private Supabase Storage bucket for chest X-ray files.",
    )
    supabase_signed_url_expire_seconds: int = Field(
        default=3600,
        ge=60,
        le=86_400,
        description="Default lifetime for signed X-ray download URLs in seconds.",
    )
    ai_model_path: Path = Field(
        default=Path("app/ai/models/DenseNet121_best_restored.keras"),
        description=(
            "Filesystem path to the DenseNet121 Keras model used for X-ray inference."
        ),
    )
    ai_inference_enabled: bool = Field(
        default=True,
        description=(
            "Enable real DenseNet121 sigmoid multilabel inference. Set false to force "
            "the legacy Mock AI path."
        ),
    )
    ai_decision_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "TEMPORARY global multilabel decision threshold used when "
            "model_backend_config.json is absent. Prefer per-class thresholds from "
            "training artifacts when available."
        ),
    )
    first_admin_full_name: str = Field(
        default="System Administrator",
        description="Full name used when seeding the first admin account.",
    )
    first_admin_email: EmailStr = Field(
        default="admin@sb3.com",
        description="Email used when seeding the first admin account.",
    )
    first_admin_password: str = Field(
        default="admin0021",
        min_length=8,
        max_length=128,
        description="Password used when seeding the first admin account.",
    )

    @field_validator("upload_dir", "ai_model_path", mode="before")
    @classmethod
    def parse_path_settings(cls, value: str | Path) -> Path:
        return Path(value)

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: list[str]) -> list[str]:
        origins = [origin.rstrip("/") for origin in value]
        if any(not origin or origin == "*" for origin in origins):
            raise ValueError("CORS_ORIGINS must contain non-empty, explicit origins.")
        return origins

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        if self.environment == "production" and self.secret_key == _INSECURE_SECRET_PLACEHOLDER:
            raise ValueError("SECRET_KEY must be set to a secure value in production.")
        if self.environment == "production" and (
            not self.supabase_url or not self.supabase_service_role_key
        ):
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in production."
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
