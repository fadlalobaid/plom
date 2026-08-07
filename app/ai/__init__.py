"""PulmoScan AI inference package (DenseNet121 chest X-ray multilabel model)."""

__all__ = ["get_model", "is_model_available"]


def __getattr__(name: str):
    if name in {"get_model", "is_model_available"}:
        from app.ai import model_loader

        return getattr(model_loader, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
