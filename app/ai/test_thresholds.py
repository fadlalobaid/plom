"""Focused tests for approved per-class F1 threshold integration."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from app.ai.config import CLASS_NAMES, DEFAULT_THRESHOLDS_CONFIG_PATH
from app.ai.exceptions import ThresholdConfigMissingError
from app.ai.inference import apply_per_class_thresholds, predict_xray, resolve_thresholds
from app.ai.threshold_config import (
    clear_threshold_config_cache,
    get_class_thresholds,
    get_threshold_config,
)


APPROVED_THRESHOLDS = {
    "Atelectasis": 0.1486324518918991,
    "Cardiomegaly": 0.1464694142341613,
    "Effusion": 0.2503989934921264,
    "Infiltration": 0.2342549711465835,
    "Mass": 0.1341352462768554,
    "Nodule": 0.2174040824174881,
    "Pneumonia": 0.0754564180970192,
    "Pneumothorax": 0.1958749294281005,
    "Consolidation": 0.0874695554375648,
    "Edema": 0.2010592818260193,
    "Emphysema": 0.2601074576377868,
    "Fibrosis": 0.2251271605491638,
    "Pleural_Thickening": 0.1480519622564315,
    "Hernia": 0.3377787470817566,
}


class ThresholdConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_threshold_config_cache()

    def tearDown(self) -> None:
        clear_threshold_config_cache()

    def test_exact_class_order(self) -> None:
        expected = [
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
        ]
        self.assertEqual(list(CLASS_NAMES), expected)

    def test_exact_threshold_count(self) -> None:
        thresholds = get_class_thresholds()
        self.assertEqual(len(thresholds), 14)
        self.assertEqual(len(APPROVED_THRESHOLDS), 14)

    def test_every_class_has_threshold(self) -> None:
        thresholds = get_class_thresholds()
        for class_name in CLASS_NAMES:
            self.assertIn(class_name, thresholds)

    def test_no_extra_threshold_classes(self) -> None:
        thresholds = get_class_thresholds()
        self.assertEqual(set(thresholds.keys()), set(CLASS_NAMES))

    def test_class_order_mapping_unchanged(self) -> None:
        self.assertEqual(CLASS_NAMES[0], "Atelectasis")
        self.assertEqual(CLASS_NAMES[1], "Cardiomegaly")
        self.assertEqual(CLASS_NAMES[6], "Pneumonia")
        self.assertEqual(CLASS_NAMES[12], "Pleural_Thickening")
        self.assertEqual(CLASS_NAMES[13], "Hernia")

    def test_loaded_thresholds_match_approved_values(self) -> None:
        thresholds = get_class_thresholds()
        for class_name, expected in APPROVED_THRESHOLDS.items():
            self.assertEqual(thresholds[class_name], expected)

    def test_config_file_path_and_metadata(self) -> None:
        self.assertTrue(DEFAULT_THRESHOLDS_CONFIG_PATH.is_file())
        config = get_threshold_config()
        self.assertEqual(config.schema_version, 1)
        self.assertEqual(config.task, "multilabel_classification")
        self.assertEqual(config.threshold_profile, "f1_balanced")
        self.assertEqual(config.decision_rule, "positive if probability >= threshold")
        self.assertEqual(config.source_path, DEFAULT_THRESHOLDS_CONFIG_PATH.resolve())

    def test_invalid_config_raises_and_no_global_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "bad.json"
            bad_path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            with self.assertRaises(ThresholdConfigMissingError):
                get_threshold_config(path=bad_path)


class PerClassDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_threshold_config_cache()
        self.thresholds = get_class_thresholds()

    def tearDown(self) -> None:
        clear_threshold_config_cache()

    def _probs(self, overrides: dict[str, float]) -> dict[str, float]:
        base = {name: 0.0 for name in CLASS_NAMES}
        base.update(overrides)
        return base

    def test_pneumonia_positive_below_global_half(self) -> None:
        # Test 6 + Test 10
        probs = self._probs({"Pneumonia": 0.08})
        predictions = apply_per_class_thresholds(probs, self.thresholds)
        labels = [item["label"] for item in predictions]
        self.assertIn("Pneumonia", labels)
        pneumonia = next(item for item in predictions if item["label"] == "Pneumonia")
        self.assertEqual(pneumonia["threshold"], APPROVED_THRESHOLDS["Pneumonia"])
        self.assertLess(float(pneumonia["probability"]), 0.5)

    def test_hernia_negative_below_own_threshold(self) -> None:
        # Test 7
        probs = self._probs({"Hernia": 0.30})
        predictions = apply_per_class_thresholds(probs, self.thresholds)
        labels = [item["label"] for item in predictions]
        self.assertNotIn("Hernia", labels)

    def test_multiple_diseases_all_returned(self) -> None:
        # Test 8
        probs = self._probs(
            {
                "Effusion": 0.41,
                "Pneumonia": 0.12,
                "Mass": 0.20,
            }
        )
        predictions = apply_per_class_thresholds(probs, self.thresholds)
        labels = [item["label"] for item in predictions]
        self.assertEqual(labels, ["Effusion", "Mass", "Pneumonia"])

    def test_zero_diseases_returns_empty_list(self) -> None:
        # Test 9
        probs = self._probs({})
        predictions = apply_per_class_thresholds(probs, self.thresholds)
        self.assertEqual(predictions, [])
        invented = {"No Finding", "Normal", "Healthy", "normal"}
        self.assertTrue(invented.isdisjoint({item["label"] for item in predictions}))

    def test_resolve_thresholds_does_not_use_global_half(self) -> None:
        thresholds, strategy = resolve_thresholds()
        self.assertIn("f1_balanced", strategy)
        self.assertEqual(thresholds["Pneumonia"], APPROVED_THRESHOLDS["Pneumonia"])
        self.assertNotEqual(thresholds["Pneumonia"], 0.5)
        self.assertTrue(any(value != 0.5 for value in thresholds.values()))


class InferenceWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_threshold_config_cache()

    def tearDown(self) -> None:
        clear_threshold_config_cache()

    def test_preprocess_called_once_per_inference(self) -> None:
        # Test 11
        fake_batch = np.zeros((1, 224, 224, 3), dtype=np.float32)
        fake_probs = np.array(
            [0.0] * 6 + [0.08] + [0.0] * 7,
            dtype=np.float32,
        )
        mock_model = MagicMock()
        mock_model.output_shape = (None, 14)
        mock_model.predict.return_value = fake_probs

        with (
            patch("app.ai.inference.preprocess_xray", return_value=fake_batch) as prep,
            patch("app.ai.inference.get_model", return_value=mock_model),
        ):
            result = predict_xray(image_bytes=b"fake-bytes")

        prep.assert_called_once()
        mock_model.predict.assert_called_once()
        labels = [item["label"] for item in result["predictions"]]
        self.assertEqual(labels, ["Pneumonia"])
        self.assertEqual(result["predicted_label"], "Pneumonia")

    def test_model_class_count_must_equal_fourteen(self) -> None:
        # Test 12
        fake_batch = np.zeros((1, 224, 224, 3), dtype=np.float32)
        mock_model = MagicMock()
        mock_model.output_shape = (None, 13)
        mock_model.predict.return_value = np.zeros((13,), dtype=np.float32)

        with (
            patch("app.ai.inference.preprocess_xray", return_value=fake_batch),
            patch("app.ai.inference.get_model", return_value=mock_model),
        ):
            from app.ai.exceptions import ClassCountMismatchError

            with self.assertRaises(ClassCountMismatchError):
                predict_xray(image_bytes=b"fake-bytes")

    def test_empty_predictions_do_not_invent_disease_label(self) -> None:
        fake_batch = np.zeros((1, 224, 224, 3), dtype=np.float32)
        mock_model = MagicMock()
        mock_model.output_shape = (None, 14)
        mock_model.predict.return_value = np.zeros((14,), dtype=np.float32)

        with (
            patch("app.ai.inference.preprocess_xray", return_value=fake_batch),
            patch("app.ai.inference.get_model", return_value=mock_model),
        ):
            result = predict_xray(image_bytes=b"fake-bytes")

        self.assertEqual(result["predictions"], [])
        self.assertEqual(result["predicted_label"], "")
        self.assertNotIn(result["predicted_label"], {"No Finding", "Normal", "Healthy"})


if __name__ == "__main__":
    unittest.main()
