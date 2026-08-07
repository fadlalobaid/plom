"""AI analysis service for chest X-ray images.

Architecture:
    diagnosis_service -> ai_service -> app.ai.inference -> model_loader -> Keras model

``image_path`` is typically a private Supabase Storage object key. Legacy local
paths and in-memory bytes are also supported for smoke tests.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path

from app.ai.exceptions import AIError, ImageMissingError
from app.core.config import get_settings
from app.services.storage_service import StorageError, download_xray_file

logger = logging.getLogger(__name__)


class XrayImageFileNotFoundError(Exception):
    """Raised when the X-ray image cannot be retrieved for analysis."""


class AIServiceNotReadyError(Exception):
    """Raised when real inference cannot run safely."""


def analyze_xray_image(image_path: str) -> dict[str, str | Decimal | None]:
    """Analyze a chest X-ray and return a DiagnosisResult-compatible payload."""
    if not image_path or not image_path.strip():
        raise XrayImageFileNotFoundError("X-ray image storage path is missing")

    settings = get_settings()
    if not settings.ai_inference_enabled:
        return _mock_analyze_xray_image()

    try:
        image_bytes = _resolve_image_bytes(image_path)
        from app.ai.inference import predict_xray

        result = predict_xray(image_bytes=image_bytes)
    except ImageMissingError as exc:
        raise XrayImageFileNotFoundError("X-ray image file was not found") from exc
    except StorageError as exc:
        logger.exception("Storage failure during AI analysis")
        raise XrayImageFileNotFoundError("X-ray image could not be retrieved from storage") from exc
    except AIError as exc:
        logger.exception("AI inference failure")
        raise AIServiceNotReadyError("AI analysis failed") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected AI analysis failure")
        raise AIServiceNotReadyError("AI analysis failed") from exc

    confidence = result["confidence_score"]
    if not isinstance(confidence, Decimal):
        confidence = Decimal(str(confidence))

    return {
        "predicted_label": str(result["predicted_label"]),
        "confidence_score": confidence,
        "model_version": str(result["model_version"]),
        "report_text": (
            str(result["report_text"]) if result.get("report_text") is not None else None
        ),
        "visual_map_path": (
            str(result["visual_map_path"])
            if result.get("visual_map_path") is not None
            else None
        ),
    }


def _resolve_image_bytes(image_path: str) -> bytes:
    """Load image bytes from local filesystem or Supabase Storage."""
    local_path = Path(image_path)
    if local_path.is_file():
        return local_path.read_bytes()

    # Fake seed markers are DB-only placeholders and are not stored in Supabase.
    if image_path.startswith("fake/"):
        raise XrayImageFileNotFoundError(
            "Seed placeholder X-ray path has no stored image bytes"
        )

    return download_xray_file(image_path)


def _mock_analyze_xray_image() -> dict[str, str | Decimal | None]:
    """Legacy Mock AI path kept behind AI_INFERENCE_ENABLED=false."""
    return {
        "predicted_label": "normal",
        "confidence_score": Decimal("0.87000"),
        "model_version": "mock-ai-v1",
        "report_text": (
            "Temporary mock diagnosis: no significant abnormal findings detected "
            "in the chest X-ray image."
        ),
        "visual_map_path": None,
    }


def is_ai_model_file_available() -> bool:
    """Non-blocking readiness helper (does not load Keras)."""
    from app.ai.model_loader import is_model_available

    return is_model_available()
