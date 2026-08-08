"""Load and cache approved per-class F1 thresholds (no global 0.5 fallback)."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.ai.config import CLASS_NAMES
from app.ai.exceptions import ThresholdConfigMissingError

DEFAULT_F1_THRESHOLDS_PATH = (
    Path(__file__).resolve().parent / "backend_f1_thresholds.json"
)

EXPECTED_SCHEMA_VERSION = 1
EXPECTED_TASK = "multilabel_classification"
EXPECTED_CLASS_COUNT = 14
EXPECTED_DECISION_RULE = "positive if probability >= threshold"
EXPECTED_THRESHOLD_PROFILE = "f1_balanced"


@dataclass(frozen=True)
class ThresholdConfig:
    """Validated, immutable per-class threshold configuration."""

    schema_version: int
    model_name: str
    task: str
    input_shape: tuple[int, int, int]
    threshold_profile: str
    threshold_source: str
    class_names: tuple[str, ...]
    thresholds: dict[str, float]
    decision_rule: str
    warning: str
    source_path: Path


_lock = threading.Lock()
_cached: ThresholdConfig | None = None


def clear_threshold_config_cache() -> None:
    """Clear the process-wide threshold config cache (tests only)."""
    global _cached
    with _lock:
        _cached = None


def get_threshold_config(
    path: Path | None = None,
    *,
    force_reload: bool = False,
) -> ThresholdConfig:
    """Load threshold JSON once, validate strictly, and cache the result."""
    global _cached
    config_path = path or DEFAULT_F1_THRESHOLDS_PATH

    with _lock:
        if _cached is not None and not force_reload and path is None:
            return _cached

        if not config_path.is_file():
            raise ThresholdConfigMissingError(
                f"Approved threshold configuration file is missing: {config_path}"
            )

        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ThresholdConfigMissingError(
                f"Approved threshold configuration is not valid JSON: {config_path}"
            ) from exc

        validated = _validate_payload(payload, source_path=config_path)
        if path is None:
            _cached = validated
        return validated


def get_class_thresholds() -> dict[str, float]:
    """Return ordered per-class thresholds from the approved artifact."""
    config = get_threshold_config()
    return {name: float(config.thresholds[name]) for name in CLASS_NAMES}


def _validate_payload(payload: Any, *, source_path: Path) -> ThresholdConfig:
    if not isinstance(payload, dict):
        raise ThresholdConfigMissingError(
            "Approved threshold configuration root must be a JSON object"
        )

    schema_version = payload.get("schema_version")
    if schema_version != EXPECTED_SCHEMA_VERSION:
        raise ThresholdConfigMissingError(
            "Approved threshold configuration schema_version must be 1"
        )

    task = payload.get("task")
    if task != EXPECTED_TASK:
        raise ThresholdConfigMissingError(
            "Approved threshold configuration task must be multilabel_classification"
        )

    class_names_raw = payload.get("class_names")
    if not isinstance(class_names_raw, list):
        raise ThresholdConfigMissingError(
            "Approved threshold configuration class_names must be a list"
        )
    class_names = tuple(str(name) for name in class_names_raw)
    if len(class_names) != EXPECTED_CLASS_COUNT:
        raise ThresholdConfigMissingError(
            f"Approved threshold configuration must contain exactly "
            f"{EXPECTED_CLASS_COUNT} class_names"
        )
    if class_names != CLASS_NAMES:
        raise ThresholdConfigMissingError(
            "Approved threshold configuration class_names order does not match "
            "expected DenseNet121 CLASS_NAMES"
        )

    thresholds_raw = payload.get("thresholds")
    if not isinstance(thresholds_raw, dict):
        raise ThresholdConfigMissingError(
            "Approved threshold configuration thresholds must be an object"
        )

    threshold_keys = set(thresholds_raw.keys())
    expected_keys = set(CLASS_NAMES)
    if threshold_keys != expected_keys:
        missing = sorted(expected_keys - threshold_keys)
        unknown = sorted(threshold_keys - expected_keys)
        raise ThresholdConfigMissingError(
            "Approved threshold configuration keys must exactly match CLASS_NAMES "
            f"(missing={missing}, unknown={unknown})"
        )

    thresholds: dict[str, float] = {}
    for name in CLASS_NAMES:
        value = thresholds_raw[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ThresholdConfigMissingError(
                f"Approved threshold for {name} must be numeric"
            )
        numeric = float(value)
        if not (0.0 <= numeric <= 1.0):
            raise ThresholdConfigMissingError(
                f"Approved threshold for {name} must be between 0 and 1"
            )
        thresholds[name] = numeric

    input_shape_raw = payload.get("input_shape")
    if (
        not isinstance(input_shape_raw, list)
        or len(input_shape_raw) != 3
        or [int(v) for v in input_shape_raw] != [224, 224, 3]
    ):
        raise ThresholdConfigMissingError(
            "Approved threshold configuration input_shape must be [224, 224, 3]"
        )

    threshold_profile = payload.get("threshold_profile")
    if threshold_profile != EXPECTED_THRESHOLD_PROFILE:
        raise ThresholdConfigMissingError(
            "Approved threshold configuration threshold_profile must be f1_balanced"
        )

    decision_rule = payload.get("decision_rule")
    if decision_rule != EXPECTED_DECISION_RULE:
        raise ThresholdConfigMissingError(
            "Approved threshold configuration decision_rule is invalid"
        )

    model_name = str(payload.get("model_name") or "")
    threshold_source = str(payload.get("threshold_source") or "")
    warning = str(payload.get("warning") or "")
    if not model_name or not threshold_source or not warning:
        raise ThresholdConfigMissingError(
            "Approved threshold configuration is missing required metadata fields"
        )

    return ThresholdConfig(
        schema_version=int(schema_version),
        model_name=model_name,
        task=str(task),
        input_shape=(224, 224, 3),
        threshold_profile=str(threshold_profile),
        threshold_source=threshold_source,
        class_names=class_names,
        thresholds=thresholds,
        decision_rule=str(decision_rule),
        warning=warning,
        source_path=source_path.resolve(),
    )
