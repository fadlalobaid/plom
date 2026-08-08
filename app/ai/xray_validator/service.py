"""Chest X-ray content validation interface.

This module is intentionally separate from DenseNet121 disease inference.

No dedicated Chest-Xray-vs-Not-Chest-Xray model is currently present in the
repository. When content validation is enabled, the service fails closed
instead of inventing heuristic or disease-model-based content checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings


class ValidatorUnavailableError(Exception):
    """Raised when strict content validation is required but unavailable."""


@dataclass(frozen=True)
class ContentValidationResult:
    """Structured content-validation outcome (not a medical diagnosis)."""

    is_chest_xray: bool | None
    confidence: float | None
    status: str
    method: str
    detail: str


def resolve_validator_model_path() -> Path:
    settings = get_settings()
    path = Path(settings.xray_validator_model_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def is_content_validator_available() -> bool:
    """Return True only when a dedicated validator model file exists."""
    return resolve_validator_model_path().is_file()


def validate_chest_xray_content(
    *,
    file_bytes: bytes,
    extension: str,
) -> ContentValidationResult:
    """Validate whether bytes appear suitable as a chest X-ray input.

    Does NOT diagnose diseases and does NOT use DenseNet121 disease outputs.
    """
    del file_bytes, extension  # Unused until a dedicated validator model exists.

    settings = get_settings()
    if not settings.xray_content_validation_enabled:
        return ContentValidationResult(
            is_chest_xray=None,
            confidence=None,
            status="skipped",
            method="disabled",
            detail=(
                "Chest X-ray content-model validation is disabled. "
                "Deterministic file/integrity checks still apply."
            ),
        )

    if not is_content_validator_available():
        raise ValidatorUnavailableError(
            "XRAY_CONTENT_VALIDATION_ENABLED is true but no dedicated "
            "Chest-Xray-vs-Not-Chest-Xray validator model is available at "
            f"{resolve_validator_model_path()}"
        )

    # Placeholder for future dedicated validator integration.
    # Intentionally not implemented: do not fake content validation.
    raise ValidatorUnavailableError(
        "A dedicated Chest-Xray validator model file was found, but validator "
        "inference is not yet integrated. Refuse to silently accept content."
    )
