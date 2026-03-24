import unittest

import pandas as pd

from backend.brand_score import summarize_sentiment_counts


class BrandScoreTests(unittest.TestCase):
    def test_summarize_sentiment_counts_calculates_percentages_and_weighted_score(self):
        df = pd.DataFrame(
            {
                "predicted_sentiment": [
                    "Positive",
                    "Positive",
                    "Neutral",
                    "Negative",
                ]
            }
        )

        payload = summarize_sentiment_counts(df)

        self.assertEqual(payload["total_reviews"], 4)
        self.assertEqual(payload["positive"], 2)
        self.assertEqual(payload["neutral"], 1)
        self.assertEqual(payload["negative"], 1)
        self.assertEqual(payload["positive_pct"], 50.0)
        self.assertEqual(payload["neutral_pct"], 25.0)
        self.assertEqual(payload["negative_pct"], 25.0)
        self.assertEqual(payload["brand_reputation_score"], 37.5)

    def test_summarize_sentiment_counts_handles_empty_frames(self):
        payload = summarize_sentiment_counts(pd.DataFrame({"predicted_sentiment": []}))

        self.assertEqual(payload["total_reviews"], 0)
        self.assertEqual(payload["brand_reputation_score"], 0.0)


if __name__ == "__main__":
    unittest.main()
