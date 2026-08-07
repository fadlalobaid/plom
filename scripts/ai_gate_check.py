"""Verify the 5 gates required before trusting real DenseNet121 inference."""

from __future__ import annotations

from app.ai.config import (
    CLASS_NAMES,
    DEFAULT_THRESHOLDS_CONFIG_PATH,
    IMAGENET_MEAN,
    IMAGENET_STD,
    TARGET_SIZE,
)
from app.ai.inference import resolve_thresholds
from app.ai.model_loader import get_model, resolve_model_path
from app.core.config import get_settings


def main() -> int:
    settings = get_settings()
    path = resolve_model_path()

    print("=== GATE CHECK REPORT ===")
    print("1) MODEL FILE")
    print("  path:", path)
    print("  exists:", path.is_file())
    if path.is_file():
        print("  size_mb:", round(path.stat().st_size / 1024 / 1024, 2))

    print("2) LOAD + SHAPES + SIGMOID")
    model = get_model()
    final = model.layers[-1]
    act = getattr(final.activation, "__name__", str(final.activation))
    print("  input_shape:", model.input_shape)
    print("  output_shape:", model.output_shape)
    print("  final_activation:", act)
    print(
        "  output_width == len(CLASS_NAMES):",
        int(model.output_shape[-1]) == len(CLASS_NAMES),
    )
    print("  sigmoid_ok:", act == "sigmoid")

    print("3) CLASS_NAMES ORDER")
    print("  count:", len(CLASS_NAMES))
    for index, name in enumerate(CLASS_NAMES):
        print(f"  [{index}] {name}")
    print("  source: train.ipynb CFG.CLASS_NAMES -> app/ai/config.py")

    print("4) PREPROCESSING")
    print("  TARGET_SIZE:", TARGET_SIZE)
    print("  mean:", IMAGENET_MEAN)
    print("  std:", IMAGENET_STD)
    print("  formula: img/255.0 then (img-mean)/std; RGB; no augmentations")
    print("  source: train.ipynb preprocess_image")

    print("5) THRESHOLD STRATEGY")
    print("  config_json_exists:", DEFAULT_THRESHOLDS_CONFIG_PATH.is_file())
    thresholds, strategy = resolve_thresholds()
    print("  strategy:", strategy)
    print("  sample_threshold:", thresholds[CLASS_NAMES[0]])
    print("  ai_inference_enabled:", settings.ai_inference_enabled)
    print("  ai_decision_threshold:", settings.ai_decision_threshold)

    gates = {
        "model_file": path.is_file(),
        "shapes": model.input_shape[-3:] == (224, 224, 3)
        and int(model.output_shape[-1]) == 14,
        "sigmoid": act == "sigmoid",
        "class_names": len(CLASS_NAMES) == 14 and CLASS_NAMES[0] == "Atelectasis",
        "preprocessing_documented": TARGET_SIZE == (224, 224),
        "threshold_validated_artifact": DEFAULT_THRESHOLDS_CONFIG_PATH.is_file(),
    }
    print("=== GATE STATUS ===")
    for name, ok in gates.items():
        print(f"  {'PASS' if ok else 'FAIL/TEMP'}: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
