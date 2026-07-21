"""AI analysis service for chest X-ray images."""

from decimal import Decimal
from pathlib import Path


class XrayImageFileNotFoundError(Exception):
    """Raised when the X-ray image file does not exist on disk."""


def analyze_xray_image(image_path: str) -> dict[str, str | Decimal | None]:
    """Analyze a chest X-ray image and return a mock diagnosis result."""
    path = Path(image_path)
    if not path.is_file():
        raise XrayImageFileNotFoundError(f"X-ray image file not found: {image_path}")

    return {
        "predicted_label": "normal",
        "confidence_score": Decimal("0.87000"),
        "model_version": "mock-ai-v1",
        "report_text": (
            "Temporary mock diagnosis: no significant abnormal findings detected "
            "in the chest X-ray image."
        ),
        "visual_map_path": None,
    }
