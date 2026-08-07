"""Lazy singleton Keras 3 model loader for DenseNet121 inference."""

from __future__ import annotations

import logging
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.ai.config import CLASS_NAMES
from app.ai.exceptions import (
    ClassCountMismatchError,
    ModelFileMissingError,
    ModelLoadError,
    UnsupportedModelShapeError,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_model_lock = threading.Lock()
_cached_model: Any | None = None


def resolve_model_path() -> Path:
    """Return the absolute path configured by AI_MODEL_PATH."""
    settings = get_settings()
    path = Path(settings.ai_model_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def is_model_available() -> bool:
    """Return True when the configured model file exists on disk."""
    try:
        return resolve_model_path().is_file()
    except Exception:  # noqa: BLE001
        return False


def _validate_model_metadata(model: Any) -> None:
    """Ensure sigmoid multilabel head matches confirmed CLASS_NAMES."""
    output_shape = getattr(model, "output_shape", None)
    if output_shape is None:
        raise UnsupportedModelShapeError("Model output shape is unavailable")

    try:
        output_width = int(output_shape[-1])
    except (TypeError, ValueError, IndexError) as exc:
        raise UnsupportedModelShapeError("Unsupported model output shape") from exc

    if output_width != len(CLASS_NAMES):
        raise ClassCountMismatchError(
            "Model output width does not match confirmed CLASS_NAMES length"
        )

    final_layer = model.layers[-1]
    activation = getattr(final_layer, "activation", None)
    activation_name = getattr(activation, "__name__", str(activation))
    if activation_name != "sigmoid":
        raise UnsupportedModelShapeError(
            f"Expected final activation 'sigmoid', found {activation_name!r}"
        )


def get_model() -> Any:
    """Load and cache the Keras model once per process (lazy singleton)."""
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    with _model_lock:
        if _cached_model is not None:
            return _cached_model

        model_path = resolve_model_path()
        if not model_path.is_file():
            raise ModelFileMissingError(
                "Configured AI model file was not found. Place "
                "DenseNet121_best_restored.keras at the path set by AI_MODEL_PATH."
            )

        try:
            import keras

            logger.info("Loading Keras AI model from configured AI_MODEL_PATH")
            model = keras.models.load_model(model_path, compile=False)
            _validate_model_metadata(model)
        except (
            ModelFileMissingError,
            UnsupportedModelShapeError,
            ClassCountMismatchError,
        ):
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to load Keras AI model")
            raise ModelLoadError(
                "Failed to load the configured Keras AI model. "
                "Ensure a Keras 3-compatible runtime is installed."
            ) from exc

        _cached_model = model
        return _cached_model


@lru_cache
def get_model_metadata_summary() -> dict[str, str]:
    """Return a small non-sensitive summary after a successful load."""
    model = get_model()
    return {
        "name": str(getattr(model, "name", "unknown")),
        "input_shape": str(getattr(model, "input_shape", None)),
        "output_shape": str(getattr(model, "output_shape", None)),
    }


def clear_model_cache() -> None:
    """Drop the cached model (tests / reloads only)."""
    global _cached_model
    with _model_lock:
        _cached_model = None
    get_model_metadata_summary.cache_clear()
