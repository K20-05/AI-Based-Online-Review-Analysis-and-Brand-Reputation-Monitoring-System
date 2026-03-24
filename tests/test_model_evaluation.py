import unittest

import numpy as np

from backend.model_evaluation import (
    build_calibration_frame,
    build_language_evaluation_frame,
    expected_calibration_error,
)


class ModelEvaluationTests(unittest.TestCase):
    def test_build_language_evaluation_frame_groups_by_language(self):
        frame = build_language_evaluation_frame(
            ["Positive", "Negative", "Neutral", "Negative"],
            ["Positive", "Positive", "Neutral", "Negative"],
            ["en", "en", "hi", "hi"],
        )

        self.assertEqual(set(frame["source_language"]), {"en", "hi"})
        self.assertEqual(int(frame.loc[frame["source_language"] == "en", "support"].iloc[0]), 2)
        self.assertEqual(int(frame.loc[frame["source_language"] == "hi", "support"].iloc[0]), 2)

    def test_build_calibration_frame_returns_bin_summary(self):
        calibration = build_calibration_frame(
            ["Positive", "Negative", "Neutral"],
            np.array(
                [
                    [0.05, 0.10, 0.85],
                    [0.70, 0.20, 0.10],
                    [0.10, 0.75, 0.15],
                ]
            ),
            ["Negative", "Neutral", "Positive"],
            bins=5,
        )

        self.assertFalse(calibration.empty)
        self.assertIn("gap", calibration.columns)
        self.assertGreaterEqual(float(calibration["sample_count"].sum()), 3)

    def test_expected_calibration_error_is_zero_for_perfect_predictions(self):
        ece = expected_calibration_error(
            ["Positive", "Negative"],
            np.array(
                [
                    [0.0, 0.0, 1.0],
                    [1.0, 0.0, 0.0],
                ]
            ),
            ["Negative", "Neutral", "Positive"],
            bins=5,
        )

        self.assertEqual(ece, 0.0)


if __name__ == "__main__":
    unittest.main()
