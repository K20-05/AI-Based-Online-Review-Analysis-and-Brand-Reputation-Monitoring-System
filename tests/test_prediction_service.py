import unittest

import numpy as np

from backend.prediction_service import parse_predict_payload, predict_batch_reviews, predict_single_review


class ProbabilityModel:
    classes_ = np.array(["Negative", "Neutral", "Positive"])

    def __init__(self, probabilities):
        self._probabilities = np.asarray(probabilities, dtype=float)

    def predict_proba(self, text_matrix):
        return self._probabilities

    def predict(self, text_matrix):
        indices = np.argmax(self._probabilities, axis=1)
        return self.classes_[indices]


class IdentityVectorizer:
    def transform(self, rows):
        return list(rows)


class PredictionServiceTests(unittest.TestCase):
    def test_parse_predict_payload_uses_platform_as_default_brand(self):
        payload = parse_predict_payload({"review_text": "bahut acha", "platform": "Nykaa"})

        self.assertEqual(payload["platform"], "Nykaa")
        self.assertEqual(payload["brand"], "Nykaa")

    def test_predict_single_review_returns_final_prediction_fields(self):
        response = predict_single_review(
            {
                "review_text": "bahut acha",
                "platform": "Nykaa",
                "brand": "Nykaa",
                "rating": 5,
            },
            lambda: (ProbabilityModel([[0.01, 0.02, 0.97]]), IdentityVectorizer()),
        )

        self.assertEqual(response["predicted_sentiment"], "Positive")
        self.assertEqual(response["source_language"], "hi")
        self.assertIn("prediction_confidence", response)
        self.assertIn("raw_model_confidence", response)

    def test_predict_single_review_marks_okish_as_neutral(self):
        response = predict_single_review(
            {
                "review_text": "okish",
                "platform": "Nykaa",
                "brand": "Nykaa",
                "rating": None,
            },
            lambda: (ProbabilityModel([[0.20, 0.10, 0.70]]), IdentityVectorizer()),
        )

        self.assertEqual(response["cleaned_review"], "okay")
        self.assertEqual(response["normalized_review"], "okay")
        self.assertEqual(response["predicted_sentiment"], "Neutral")
        self.assertEqual(response["sentiment_adjustment_reason"], "multilingual_neutral_guard")

    def test_predict_batch_reviews_skips_empty_rows_and_returns_brand_score(self):
        response = predict_batch_reviews(
            [
                {"review_text": "bahut acha", "platform": "Nykaa", "brand": "Nykaa", "rating": 5},
                {"review_text": "  ", "platform": "Nykaa", "brand": "Nykaa"},
            ],
            lambda: (ProbabilityModel([[0.01, 0.02, 0.97]]), IdentityVectorizer()),
        )

        self.assertEqual(response["rows"], 1)
        self.assertEqual(response["results"][0]["predicted_sentiment"], "Positive")
        self.assertIn("brand_score", response)


if __name__ == "__main__":
    unittest.main()
