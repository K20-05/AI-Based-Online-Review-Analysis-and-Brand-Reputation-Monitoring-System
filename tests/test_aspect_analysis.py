import unittest

from backend.aspect_analysis import analyze_review_aspects, summarize_batch_aspects


class AspectAnalysisTests(unittest.TestCase):
    def test_detects_negative_delivery_signal(self):
        result = analyze_review_aspects(
            "Delivery was very late and the package was damaged.",
            "Negative",
            "delivery was late delayed and the package was damaged",
        )

        self.assertTrue(result["aspect_sentiments"])
        self.assertEqual(result["primary_aspect"], "Delivery")
        self.assertEqual(result["primary_aspect_sentiment"], "Negative")

    def test_detects_positive_support_signal(self):
        result = analyze_review_aspects(
            "Customer support gave a quick response and resolved the issue.",
            "Positive",
            "customer support gave a quick response and resolved the issue",
        )

        aspects = {row["aspect"]: row["sentiment"] for row in result["aspect_sentiments"]}
        self.assertEqual(aspects.get("Customer Support"), "Positive")

    def test_summarizes_batch_aspects(self):
        summary = summarize_batch_aspects(
            [
                {
                    "aspect_sentiments": [
                        {"aspect": "Delivery", "sentiment": "Negative"},
                        {"aspect": "Product Quality", "sentiment": "Positive"},
                    ]
                },
                {
                    "aspect_sentiments": [
                        {"aspect": "Delivery", "sentiment": "Negative"},
                    ]
                },
            ]
        )

        self.assertEqual(summary[0]["aspect"], "Delivery")
        self.assertEqual(summary[0]["negative"], 2)


if __name__ == "__main__":
    unittest.main()
