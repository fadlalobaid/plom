"""DenseNet121 sigmoid multilabel inference.

Rules:
- DO NOT apply Softmax
- DO NOT apply Sigmoid again
- DO NOT use argmax as the disease-selection rule
- Each output is an independent disease probability
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from app.ai.config import (
    CLASS_NAMES,
    DEFAULT_THRESHOLDS_CONFIG_PATH,
    MODEL_VERSION,
    MULTILABEL_JSON_MARKER,
    THRESHOLD_STRATEGY_PER_CLASS_CONFIG,
    THRESHOLD_STRATEGY_TEMPORARY_GLOBAL,
    get_temporary_global_threshold,
)
from app.ai.exceptions import (
    ClassCountMismatchError,
    NonFinitePredictionError,
    PredictionError,
    ThresholdConfigMissingError,
    UnsupportedModelShapeError,
)
from app.ai.model_loader import get_model
from app.ai.preprocessing import preprocess_xray


def _as_python_float(value: Any) -> float:
    return float(np.asarray(value).item())


def resolve_thresholds(profile: str | None = None) -> tuple[dict[str, float], str]:
    """Return (thresholds_by_class, strategy_name).

    Prefer ``model_backend_config.json`` per-class thresholds when present.
    Otherwise use the temporary documented global fallback of 0.5.
    """
    path = DEFAULT_THRESHOLDS_CONFIG_PATH
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        profiles = payload.get("threshold_profiles") or {}
        selected = profile or payload.get("default_threshold_profile")
        thresholds: dict[str, float] | None = None
        if selected and selected in profiles:
            thresholds = {str(k): float(v) for k, v in profiles[selected].items()}
        elif isinstance(payload.get("thresholds"), dict):
            thresholds = {str(k): float(v) for k, v in payload["thresholds"].items()}

        if thresholds:
            missing = [name for name in CLASS_NAMES if name not in thresholds]
            if missing:
                raise ThresholdConfigMissingError(
                    "Threshold configuration is missing classes required by CLASS_NAMES"
                )
            ordered = {name: float(thresholds[name]) for name in CLASS_NAMES}
            strategy = f"{THRESHOLD_STRATEGY_PER_CLASS_CONFIG}:{selected or 'thresholds'}"
            return ordered, strategy

    temporary = get_temporary_global_threshold()
    ordered = {name: float(temporary) for name in CLASS_NAMES}
    return ordered, f"{THRESHOLD_STRATEGY_TEMPORARY_GLOBAL}:{temporary}"


def predict_probabilities(
    *,
    image_path: str | Path | None = None,
    image_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Run the model and return raw per-class sigmoid probabilities."""
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
    """Sigmoid multilabel prediction with thresholding (no Softmax / no argmax selection)."""
    probability_result = predict_probabilities(
        image_path=image_path,
        image_bytes=image_bytes,
    )
    thresholds, threshold_strategy = resolve_thresholds(threshold_profile)
    all_probabilities: dict[str, float] = probability_result["all_probabilities"]

    predictions = [
        {
            "label": class_name,
            "probability": all_probabilities[class_name],
        }
        for class_name in CLASS_NAMES
        if all_probabilities[class_name] >= thresholds[class_name]
    ]
    # Sort selected findings by probability descending for readability only.
    predictions.sort(key=lambda item: item["probability"], reverse=True)

    if predictions:
        # Backward-compatible summary fields only — NOT the multilabel selection rule.
        predicted_label = str(predictions[0]["label"])
        confidence_score = float(predictions[0]["probability"])
        findings_text = ", ".join(
            f"{item['label']} ({item['probability'] * 100:.1f}%)"
            for item in predictions
        )
        report_text = (
            "AI-assisted model prediction detected: "
            f"{findings_text}. "
            "Assistive screening output only; not a confirmed medical diagnosis."
        )
    else:
        # "No Finding" is NOT a trained class; it means no label exceeded threshold.
        predicted_label = "No Finding"
        confidence_score = float(max(all_probabilities.values()))
        report_text = (
            "AI-assisted model prediction detected no labels above the configured "
            "decision threshold. Assistive screening output only; not a confirmed "
            "medical diagnosis."
        )

    multilabel_payload = {
        "predictions": predictions,
        "all_probabilities": all_probabilities,
        "thresholds": thresholds,
        "threshold_strategy": threshold_strategy,
        "model_version": MODEL_VERSION,
        "class_names": list(CLASS_NAMES),
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
        "input_shape": probability_result["input_shape"],
        "output_shape": probability_result["output_shape"],
    }
