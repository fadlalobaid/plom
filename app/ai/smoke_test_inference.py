"""Standalone DenseNet121 multilabel smoke test (no FastAPI / no DB / no PHI).

Usage (WSL/Linux env with Keras 3):

    python -m app.ai.smoke_test_inference
"""

from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _make_dummy_xray_bytes() -> bytes:
    """Create a synthetic RGB PNG for pipeline validation (not a clinical image)."""
    import numpy as np
    from PIL import Image

    array = np.zeros((224, 224, 3), dtype=np.uint8)
    array[:, :] = (40, 40, 40)
    array[60:160, 60:160] = (180, 180, 180)
    buffer = BytesIO()
    Image.fromarray(array, mode="RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def main() -> int:
    from app.ai.config import CLASS_NAMES, MODEL_VERSION
    from app.ai.inference import predict_xray
    from app.ai.model_loader import get_model, get_model_metadata_summary, is_model_available

    print("=== PulmoScan DenseNet121 Smoke Test ===")
    print(f"model_version: {MODEL_VERSION}")
    print(f"class_count: {len(CLASS_NAMES)}")
    print(f"model_file_available: {is_model_available()}")
    if not is_model_available():
        print("MODEL FILE MISSING at AI_MODEL_PATH")
        return 1

    model = get_model()
    summary = get_model_metadata_summary()
    print(f"input_shape: {summary['input_shape']}")
    print(f"output_shape: {summary['output_shape']}")
    print(f"final_activation_check: sigmoid expected")

    image_bytes = _make_dummy_xray_bytes()
    result = predict_xray(image_bytes=image_bytes)

    print(f"probability_vector_length: {len(result['all_probabilities'])}")
    print(f"threshold_strategy: {result['threshold_strategy']}")
    print(f"selected_labels: {[item['label'] for item in result['predictions']]}")
    print(
        "selected_probabilities: "
        + ", ".join(
            f"{item['label']}={item['probability']:.4f}"
            for item in result["predictions"]
        )
    )
    print(f"summary_predicted_label: {result['predicted_label']}")
    print(f"summary_confidence_score: {result['confidence_score']:.5f}")
    print("top_5_probabilities:")
    ranked = sorted(
        result["all_probabilities"].items(),
        key=lambda item: item[1],
        reverse=True,
    )[:5]
    for label, score in ranked:
        print(f"  {label}: {score:.4f}")

    assert len(result["all_probabilities"]) == len(CLASS_NAMES)
    assert result["model_version"] == MODEL_VERSION
    assert getattr(model.layers[-1].activation, "__name__", "") == "sigmoid"
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
