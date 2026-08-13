"""DenseNet121 sigmoid multilabel inference.

Rules:
- DO NOT apply Softmax
- DO NOT apply Sigmoid again
- DO NOT use argmax as the disease-selection rule
- Each output is an independent disease probability
- Disease decisions use approved per-class thresholds only
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from app.ai.config import (
    CLASS_NAMES,
    MODEL_VERSION,
    MULTILABEL_JSON_MARKER,
    THRESHOLD_STRATEGY_PER_CLASS_CONFIG,
)
from app.ai.exceptions import (
    ClassCountMismatchError,
    NonFinitePredictionError,
    PredictionError,
    UnsupportedModelShapeError,
)
from app.ai.model_loader import get_model
from app.ai.preprocessing import preprocess_xray
from app.ai.threshold_config import get_class_thresholds, get_threshold_config
from app.core import messages


def _as_python_float(value: Any) -> float:
    return float(np.asarray(value).item())


def resolve_thresholds(profile: str | None = None) -> tuple[dict[str, float], str]:
    """Return approved per-class thresholds.

    ``profile`` is accepted for call-site compatibility but ignored: production
    decisions always use the validated ``f1_balanced`` artifact.
    """
    del profile  # Approved artifact is authoritative; no runtime profile switching.
    config = get_threshold_config()
    thresholds = get_class_thresholds()
    strategy = (
        f"{THRESHOLD_STRATEGY_PER_CLASS_CONFIG}"
        f" ({config.source_path.name})"
    )
    return thresholds, strategy


def apply_per_class_thresholds(
    all_probabilities: dict[str, float],
    thresholds: dict[str, float],
) -> list[dict[str, float | str]]:
    """Apply approved per-class decision rule without reinterpreting probabilities."""
    predictions: list[dict[str, float | str]] = []
    for class_name in CLASS_NAMES:
        probability = float(all_probabilities[class_name])
        threshold = float(thresholds[class_name])
        if probability >= threshold:
            predictions.append(
                {
                    "label": class_name,
                    "probability": probability,
                    "threshold": threshold,
                }
            )
    return predictions


def predict_probabilities(
    *,
    image_path: str | Path | None = None,
    image_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Run the model and return raw per-class sigmoid probabilities."""
    # Preprocessing occurs exactly once before predict.
    batch = preprocess_xray(image_path=image_path, image_bytes=image_bytes)
    model = get_model()

    output_shape = getattr(model, "output_shape", None)
    if output_shape is not None:
        try:
            width = int(output_shape[-1])
        except (TypeError, ValueError) as exc:
            raise UnsupportedModelShapeError("Unsupported model output shape") from exc
        if width != len(CLASS_NAMES):
            raise ClassCountMismatchError(
                "Model output width does not match confirmed CLASS_NAMES length"
            )

    try:
        raw = model.predict(batch, verbose=0)
    except Exception as exc:  # noqa: BLE001
        raise PredictionError("Model prediction failed") from exc

    probs = np.asarray(raw, dtype=np.float32).reshape(-1)
    if probs.shape[0] != len(CLASS_NAMES):
        raise ClassCountMismatchError(
            "Prediction vector length does not match confirmed CLASS_NAMES length"
        )
    if not np.all(np.isfinite(probs)):
        raise NonFinitePredictionError("Model produced non-finite outputs")

    all_probabilities = {
        class_name: _as_python_float(probs[index])
        for index, class_name in enumerate(CLASS_NAMES)
    }
    return {
        "model_version": MODEL_VERSION,
        "class_names": list(CLASS_NAMES),
        "all_probabilities": all_probabilities,
        "probability_vector": [
            all_probabilities[name] for name in CLASS_NAMES
        ],
        "input_shape": list(batch.shape),
        "output_shape": list(getattr(model, "output_shape", (None, len(CLASS_NAMES)))),
    }


def predict_xray(
    *,
    image_path: str | Path | None = None,
    image_bytes: bytes | None = None,
    threshold_profile: str | None = None,
) -> dict[str, Any]:
    """Sigmoid multilabel prediction with approved per-class thresholds."""
    # Ensure threshold artifact is valid before exposing inference results.
    threshold_config = get_threshold_config()
    probability_result = predict_probabilities(
        image_path=image_path,
        image_bytes=image_bytes,
    )
    thresholds, threshold_strategy = resolve_thresholds(threshold_profile)
    all_probabilities: dict[str, float] = probability_result["all_probabilities"]

    predictions = apply_per_class_thresholds(all_probabilities, thresholds)

    if predictions:
        # Backward-compatible summary fields: highest-probability positive label.
        # Full multilabel output remains in predictions / embedded JSON.
        top_prediction = max(
            predictions,
            key=lambda item: float(item["probability"]),
        )
        predicted_label = str(top_prediction["label"])
        confidence_score = float(top_prediction["probability"])
        findings_text = ", ".join(
            f"{item['label']} ({float(item['probability']) * 100:.1f}%)"
            for item in sorted(
                predictions,
                key=lambda item: float(item["probability"]),
                reverse=True,
            )
        )
        report_text = (
            "AI-assisted analysis / model output detected: "
            f"{findings_text}. "
            f"{threshold_config.warning}"
        )
    else:
        # Empty predictions means no class exceeded its approved threshold.
        # Do NOT invent a trained disease class (e.g. No Finding).
        # Legacy DB column predicted_label is non-null, so use an empty summary.
        predicted_label = ""
        confidence_score = float(max(all_probabilities.values()))
        # User-facing Arabic summary only; full multilabel payload follows the marker.
        report_text = messages.NO_POSITIVE_FINDINGS

    multilabel_payload = {
        "predictions": predictions,
        "all_probabilities": all_probabilities,
        "thresholds": thresholds,
        "threshold_strategy": threshold_strategy,
        "threshold_profile": threshold_config.threshold_profile,
        "decision_rule": threshold_config.decision_rule,
        "model_version": MODEL_VERSION,
        "class_names": list(CLASS_NAMES),
        "warning": threshold_config.warning,
    }

    return {
        "predicted_label": predicted_label,
        "confidence_score": confidence_score,
        "model_version": MODEL_VERSION,
        "report_text": (
            f"{report_text}\n{MULTILABEL_JSON_MARKER}\n"
            f"{json.dumps(multilabel_payload, ensure_ascii=True)}"
        ),
        "visual_map_path": None,
        "predictions": predictions,
        "all_probabilities": all_probabilities,
        "thresholds": thresholds,
        "threshold_strategy": threshold_strategy,
        "warning": threshold_config.warning,
        "input_shape": probability_result["input_shape"],
        "output_shape": probability_result["output_shape"],
    }
