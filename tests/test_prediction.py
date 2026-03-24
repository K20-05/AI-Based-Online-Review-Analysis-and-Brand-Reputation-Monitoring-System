import unittest

import numpy as np

from backend.predict import (
    calibrate_prediction_confidence,
    predict_with_confidence_details,
    predict_with_neutral_guard,
)


class ProbabilityModel:
    classes_ = np.array(["Negative", "Neutral", "Positive"])

    def __init__(self, probabilities):
        self._probabilities = np.asarray(probabilities, dtype=float)

    def predict_proba(self, text_matrix):
        return self._probabilities

    def predict(self, text_matrix):
        indices = np.argmax(self._probabilities, axis=1)
        return self.classes_[indices]


class LabelOnlyModel:
    def predict(self, text_matrix):
        return np.array(["Positive", "Negative"])


class PredictionGuardTests(unittest.TestCase):
    def test_returns_model_predictions_when_probabilities_are_unavailable(self):
        result = predict_with_neutral_guard(LabelOnlyModel(), [[0], [1]])

        self.assertEqual(result, ["Positive", "Negative"])

    def test_marks_low_confidence_predictions_as_neutral(self):
        result = predict_with_neutral_guard(ProbabilityModel([[0.33, 0.34, 0.33]]), [[0]])

        self.assertEqual(result, ["Neutral"])

    def test_marks_ambiguous_positive_negative_predictions_as_neutral(self):
        result = predict_with_neutral_guard(ProbabilityModel([[0.49, 0.02, 0.49]]), [[0]])

        self.assertEqual(result, ["Neutral"])

    def test_keeps_confident_predictions(self):
        result = predict_with_neutral_guard(ProbabilityModel([[0.1, 0.08, 0.82]]), [[0]])

        self.assertEqual(result, ["Positive"])

    def test_returns_decision_details_for_ambiguous_predictions(self):
        result = predict_with_confidence_details(ProbabilityModel([[0.56, 0.01, 0.43]]), [[0]])[0]

        self.assertEqual(result["predicted_sentiment"], "Neutral")
        self.assertEqual(result["raw_predicted_sentiment"], "Negative")
        self.assertEqual(result["neutral_guard_reason"], "pos_neg_ambiguous")
        self.assertGreater(result["decision_confidence"], 0.55)

    def test_calibrated_confidence_is_tempered_for_short_translated_inputs(self):
        confidence = calibrate_prediction_confidence(
            0.984,
            "good",
            translation_applied=True,
            language_confidence=0.81,
        )

        self.assertLess(confidence, 0.90)
        self.assertGreater(confidence, 0.70)

    def test_calibrated_confidence_uses_normalized_phrase_length_for_mapped_inputs(self):
        confidence = calibrate_prediction_confidence(
            0.984,
            "good",
            translation_applied=True,
            language_confidence=0.69,
            normalized_review="very good",
        )

        self.assertGreater(confidence, 0.80)
        self.assertLess(confidence, 0.90)


if __name__ == "__main__":
    unittest.main()
