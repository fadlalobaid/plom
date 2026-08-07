"""Safe unit tests for AI config/readiness (no model.predict / no training)."""

from __future__ import annotations

import unittest
from pathlib import Path

from app.ai.config import CLASS_NAMES, MODEL_VERSION, TARGET_SIZE
from app.ai.model_loader import is_model_available, resolve_model_path
from app.core.config import get_settings


class AIConfigTests(unittest.TestCase):
    def test_class_names_order_and_count(self) -> None:
        self.assertEqual(len(CLASS_NAMES), 14)
        self.assertEqual(CLASS_NAMES[0], "Atelectasis")
        self.assertEqual(CLASS_NAMES[-1], "Hernia")
        self.assertEqual(CLASS_NAMES[6], "Pneumonia")

    def test_target_size_and_model_version(self) -> None:
        self.assertEqual(TARGET_SIZE, (224, 224))
        self.assertEqual(MODEL_VERSION, "DenseNet121_best_restored")
        self.assertLessEqual(len(MODEL_VERSION), 50)

    def test_ai_settings_defaults(self) -> None:
        settings = get_settings()
        self.assertTrue(str(settings.ai_model_path).endswith(".keras"))
        self.assertGreaterEqual(settings.ai_decision_threshold, 0.0)
        self.assertLessEqual(settings.ai_decision_threshold, 1.0)

    def test_resolve_model_path_is_path(self) -> None:
        path = resolve_model_path()
        self.assertIsInstance(path, Path)

    def test_is_model_available_does_not_raise(self) -> None:
        # May be True/False depending on whether the binary was placed locally.
        self.assertIn(is_model_available(), (True, False))


if __name__ == "__main__":
    unittest.main()
