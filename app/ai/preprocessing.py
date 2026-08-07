"""X-ray preprocessing for DenseNet121 inference.

Exact training preprocessing from Desktop ``train.ipynb``:

    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])

    def preprocess_image(img):
        img = img / 255.0
        img = (img - mean) / std
        return img

TARGET_SIZE=(224, 224), COLOR_MODE='rgb'. No augmentations at inference.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np

from app.ai.config import (
    COLOR_MODE,
    IMAGENET_MEAN,
    IMAGENET_STD,
    TARGET_SIZE,
)
from app.ai.exceptions import ImageMissingError, PreprocessingError


def preprocess_image_array(img: np.ndarray) -> np.ndarray:
    """Apply the exact training normalization to a float32 HxWxC array in 0–255."""
    try:
        array = np.asarray(img, dtype=np.float32)
        array = array / 255.0
        mean = np.asarray(IMAGENET_MEAN, dtype=np.float32)
        std = np.asarray(IMAGENET_STD, dtype=np.float32)
        return (array - mean) / std
    except Exception as exc:  # noqa: BLE001
        raise PreprocessingError("Failed to normalize X-ray image array") from exc


def _load_image_array(
    *,
    image_path: str | Path | None = None,
    image_bytes: bytes | None = None,
    target_size: tuple[int, int],
) -> np.ndarray:
    try:
        from keras.utils import img_to_array, load_img
    except Exception:  # noqa: BLE001
        from tensorflow.keras.utils import img_to_array, load_img

    try:
        if image_bytes is not None:
            image = load_img(
                BytesIO(image_bytes),
                target_size=target_size,
                color_mode=COLOR_MODE,
            )
        elif image_path is not None:
            path = Path(image_path)
            if not path.is_file():
                raise ImageMissingError("X-ray image file was not found for preprocessing")
            image = load_img(
                path,
                target_size=target_size,
                color_mode=COLOR_MODE,
            )
        else:
            raise PreprocessingError("No image source provided for preprocessing")
        return img_to_array(image).astype("float32")
    except ImageMissingError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PreprocessingError("Failed to load X-ray image for preprocessing") from exc


def preprocess_xray(
    image_path: str | Path | None = None,
    *,
    image_bytes: bytes | None = None,
    target_size: tuple[int, int] = TARGET_SIZE,
) -> np.ndarray:
    """Return a batched float32 tensor with shape (1, H, W, 3)."""
    original_array = _load_image_array(
        image_path=image_path,
        image_bytes=image_bytes,
        target_size=target_size,
    )
    processed = preprocess_image_array(original_array)
    batch = np.expand_dims(np.asarray(processed, dtype=np.float32), axis=0)

    expected = (1, target_size[0], target_size[1], 3)
    if batch.shape != expected:
        raise PreprocessingError(
            f"Unexpected preprocessing output shape {batch.shape}; expected {expected}"
        )
    return batch
