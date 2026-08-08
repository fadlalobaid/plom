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

# Authoritative approved per-class F1 thresholds for production multilabel decisions.
# Disease selection MUST use this artifact — never a global 0.5 fallback.
DEFAULT_THRESHOLDS_CONFIG_PATH = (
    Path(__file__).resolve().parent / "backend_f1_thresholds.json"
)

THRESHOLD_STRATEGY_PER_CLASS_CONFIG = "per_class_from_backend_f1_thresholds:f1_balanced"

# Marker used to embed full multilabel JSON inside DiagnosisResult.report_text
# until a dedicated JSONB/child-table migration is approved.
MULTILABEL_JSON_MARKER = "<<<MULTILABEL_JSON>>>"
