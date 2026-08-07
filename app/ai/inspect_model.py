"""Standalone DenseNet121 model inspection script (no FastAPI / no DB).

Usage (from project root, with TensorFlow available):

    python app/ai/inspect_model.py

Or:

    set AI_MODEL_PATH=C:\\path\\to\\DenseNet121_best_restored.keras
    python -m app.ai.inspect_model

This script intentionally avoids importing ``app.core.config`` / Pydantic so it
can run in a separate TensorFlow environment (e.g. Python 3.10) used only for
model inspection.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Exact training class order from Desktop train.ipynb (CFG.CLASS_NAMES).
CLASS_NAMES = (
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

DEFAULT_MODEL_PATH = BACKEND_ROOT / "app" / "ai" / "models" / "DenseNet121_best_restored.keras"


def resolve_model_path() -> Path:
    configured = os.environ.get("AI_MODEL_PATH", "").strip()
    path = Path(configured) if configured else DEFAULT_MODEL_PATH
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def _layer_activation_name(layer) -> str:
    activation = getattr(layer, "activation", None)
    if activation is None:
        return "none"
    return getattr(activation, "__name__", str(activation))


def main() -> int:
    model_path = resolve_model_path()

    print("=== PulmoScan AI Model Inspection ===")
    print(f"AI_MODEL_PATH env/default resolved exists: {model_path.is_file()}")
    if not model_path.is_file():
        print(
            "MODEL FILE MISSING.\n"
            "Manually copy DenseNet121_best_restored.keras to:\n"
            f"  {DEFAULT_MODEL_PATH}\n"
            "or set AI_MODEL_PATH to the absolute file location."
        )
        return 1

    import json
    import zipfile

    model_name = "unknown"
    input_shape = None
    output_shape = None
    input_dtype = "unknown"
    output_dtype = "unknown"
    final_layer_class = "unknown"
    activation_name = "unknown"
    total_params = "unknown"
    saved_keras_version = "unknown"
    loaded_runtime = False

    # Prefer archive metadata for Keras 3 .keras zip packages when the installed
    # TensorFlow/Keras runtime cannot load the file.
    if zipfile.is_zipfile(model_path):
        with zipfile.ZipFile(model_path) as archive:
            if "metadata.json" in archive.namelist():
                metadata = json.loads(archive.read("metadata.json"))
                saved_keras_version = str(metadata.get("keras_version", "unknown"))
            if "config.json" in archive.namelist():
                config = json.loads(archive.read("config.json"))
                model_name = str(config.get("config", {}).get("name", "unknown"))
                layers = config.get("config", {}).get("layers", [])
                if layers:
                    first = layers[0].get("config", {})
                    last = layers[-1].get("config", {})
                    input_shape = first.get("batch_shape") or first.get("batch_input_shape")
                    input_dtype = str(first.get("dtype", "unknown"))
                    final_layer_class = str(layers[-1].get("class_name", "unknown"))
                    activation_name = str(last.get("activation", "unknown"))
                    units = last.get("units")
                    if units is not None:
                        output_shape = (None, int(units))
                        output_dtype = str(last.get("dtype", "unknown"))

    print(f"Saved keras_version (metadata): {saved_keras_version}")

    try:
        import tensorflow as tf

        print(f"Runtime TensorFlow version: {tf.__version__}")
        print("Attempting tf.keras.models.load_model(..., compile=False) ...")
        model = tf.keras.models.load_model(model_path, compile=False)
        loaded_runtime = True
        model_name = getattr(model, "name", model_name)
        input_shape = getattr(model, "input_shape", input_shape)
        output_shape = getattr(model, "output_shape", output_shape)
        final_layer = model.layers[-1]
        final_layer_class = final_layer.__class__.__name__
        activation_name = _layer_activation_name(final_layer)
        total_params = model.count_params()
        try:
            input_dtype = str(model.inputs[0].dtype) if model.inputs else input_dtype
        except Exception:  # noqa: BLE001
            pass
        try:
            output_dtype = str(model.outputs[0].dtype) if model.outputs else output_dtype
        except Exception:  # noqa: BLE001
            pass
        print("Runtime load: SUCCESS")
    except Exception as exc:  # noqa: BLE001
        print(f"Runtime load: FAILED ({type(exc).__name__}: {exc})")
        print(
            "NOTE: This .keras package appears to be Keras 3 format. "
            "Use TensorFlow/Keras 3-compatible runtime (e.g. tensorflow>=2.16 / keras 3.x) "
            "before enabling real inference."
        )

    print(f"model.name: {model_name}")
    print(f"input_shape: {input_shape}")
    print(f"output_shape: {output_shape}")
    print(f"input dtype: {input_dtype}")
    print(f"output dtype: {output_dtype}")
    print(f"final layer class: {final_layer_class}")
    print(f"final layer activation: {activation_name}")
    print(f"total parameters: {total_params}")
    print(f"weights loaded in this runtime: {loaded_runtime}")

    output_width = None
    if isinstance(output_shape, (tuple, list)) and output_shape:
        try:
            output_width = int(output_shape[-1])
        except (TypeError, ValueError):
            output_width = None

    print("--- Classification type (architecture-based) ---")
    if output_width == 14 and activation_name == "sigmoid":
        print(
            "Likely 14-output multilabel model; class order still requires confirmation."
        )
    elif activation_name == "softmax" and output_width is not None:
        print(
            f"Softmax output with {output_width} classes; "
            "class order still requires confirmation."
        )
    elif activation_name == "sigmoid" and output_width == 1:
        print("Likely binary sigmoid model; labels still require confirmation.")
    else:
        print(
            "Unable to confidently classify task type from architecture alone "
            f"(output_width={output_width}, activation={activation_name})."
        )

    print("--- Confirmed training artifacts (train.ipynb) ---")
    print(f"Confirmed CLASS_NAMES length: {len(CLASS_NAMES)}")
    for index, name in enumerate(CLASS_NAMES):
        print(f"  [{index}] {name}")
    print(
        "Preprocessing confirmed: img/255.0 then ImageNet mean/std; "
        "target 224x224 RGB (custom preprocess_image, NOT densenet.preprocess_input)."
    )
    print(
        "Threshold artifact model_backend_config.json is REQUIRED before replacing Mock AI."
    )
    print("Mock AI remains active in app/services/ai_service.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
