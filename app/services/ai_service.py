"""AI analysis service for chest X-ray images."""

from decimal import Decimal


class XrayImageFileNotFoundError(Exception):
    """Raised when the X-ray image storage path is missing or invalid."""


def analyze_xray_image(image_path: str) -> dict[str, str | Decimal | None]:
    """Analyze a chest X-ray image and return a mock diagnosis result.

    ``image_path`` is the private Supabase Storage object path stored in
    ``xray_images.image_path`` (not a public URL and not a local filesystem path).
    """
    if not image_path or not image_path.strip():
        raise XrayImageFileNotFoundError("X-ray image storage path is missing")

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
