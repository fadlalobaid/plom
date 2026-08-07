"""Internal AI/inference exceptions (not for direct client exposure)."""


class AIError(Exception):
    """Base class for AI package errors."""


class ModelFileMissingError(AIError):
    """Raised when the configured Keras model file is not found."""


class ModelLoadError(AIError):
    """Raised when the Keras model cannot be loaded."""


class UnsupportedModelShapeError(AIError):
    """Raised when model input/output shapes are incompatible."""


class ImageMissingError(AIError):
    """Raised when the local image path does not exist."""


class PreprocessingError(AIError):
    """Raised when image preprocessing fails."""


class PredictionError(AIError):
    """Raised when model prediction fails."""


class NonFinitePredictionError(AIError):
    """Raised when model outputs contain NaN/Inf."""


class ClassCountMismatchError(AIError):
    """Raised when prediction width does not match CLASS_NAMES."""


class ThresholdConfigMissingError(AIError):
    """Raised when multilabel thresholds are required but unavailable."""


class InferenceNotReadyError(AIError):
    """Raised when real inference is blocked pending verified configuration."""
