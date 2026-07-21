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
        description="Directory used to store uploaded files.",
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

    @field_validator("upload_dir", mode="before")
    @classmethod
    def parse_upload_dir(cls, value: str | Path) -> Path:
        return Path(value)

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        if self.environment == "production" and self.secret_key == _INSECURE_SECRET_PLACEHOLDER:
            raise ValueError("SECRET_KEY must be set to a secure value in production.")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
