"""AI constants confirmed from the DenseNet121 training notebook.

Source of truth for class order and preprocessing:
``C:\\Users\\fadlalobaid\\OneDrive\\Desktop\\train.ipynb``
(CFG.CLASS_NAMES, TARGET_SIZE, and preprocess_image).

Do NOT alphabetically re-sort CLASS_NAMES — order matches the trained
sigmoid output heads.
"""

from __future__ import annotations

from pathlib import Path

# Exact order from training CFG.CLASS_NAMES (train.ipynb).
CLASS_NAMES: tuple[str, ...] = (
    "Atelectasis",
    "Cardiomegaly",
    "Effusion",
    "Infiltration",
    "Mass",
    "Nodule",
    "Pneumonia",
    "Pneumothorax",
    "Consolidation",
    "Edema",
    "Emphysema",
    "Fibrosis",
    "Pleural_Thickening",
    "Hernia",
)

TARGET_SIZE: tuple[int, int] = (224, 224)
COLOR_MODE = "rgb"
MODEL_VERSION = "DenseNet121_best_restored"

# ImageNet mean/std used by training preprocess_image (values in [0, 1] space).
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

# Optional JSON with per-class thresholds produced by training
# (model_backend_config.json). When absent, a TEMPORARY global fallback of 0.5
# is used and clearly marked in inference metadata.
DEFAULT_THRESHOLDS_CONFIG_PATH = (
    Path(__file__).resolve().parent / "models" / "model_backend_config.json"
)

# Temporary development fallback ONLY when no threshold artifact exists.
# Training evaluation also inspected threshold=0.5 as a baseline.
THRESHOLD_STRATEGY_TEMPORARY_GLOBAL = "temporary_global_threshold"
THRESHOLD_STRATEGY_PER_CLASS_CONFIG = "per_class_from_model_backend_config"


def get_temporary_global_threshold() -> float:
    """Return the configured temporary global threshold (default 0.5)."""
    from app.core.config import get_settings

    return float(get_settings().ai_decision_threshold)

# Marker used to embed full multilabel JSON inside DiagnosisResult.report_text
# until a dedicated JSONB/child-table migration is approved.
MULTILABEL_JSON_MARKER = "<<<MULTILABEL_JSON>>>"
