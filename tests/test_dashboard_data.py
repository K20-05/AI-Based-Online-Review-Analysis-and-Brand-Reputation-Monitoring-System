import json
import os
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import backend.dashboard_data as dashboard_data


class DashboardDataTests(unittest.TestCase):
    def test_dashboard_brand_payload_recalculates_when_cached_score_is_stale(self):
        root = Path(__file__).resolve().parent
        brand_score_path = root / "_tmp_brand_score.json"
        predictions_path = root / "_tmp_final_predictions.csv"
        realtime_path = root / "_tmp_realtime_reviews.csv"
        for path in (brand_score_path, predictions_path, realtime_path):
            self.addCleanup(lambda target=path: target.unlink(missing_ok=True))

        brand_score_path.write_text(json.dumps({"cached": True}), encoding="utf-8")
        predictions_path.write_text("review_id,predicted_sentiment\n1,Positive\n", encoding="utf-8")
        realtime_path.write_text("review_id,predicted_sentiment\nrt-1,Negative\n", encoding="utf-8")

        base_time = time.time_ns()
        os.utime(brand_score_path, ns=(base_time, base_time))
        os.utime(predictions_path, ns=(base_time, base_time))
        os.utime(realtime_path, ns=(base_time + 1_000_000, base_time + 1_000_000))

        fresh_payload = {"fresh": True}
        with (
            patch.object(dashboard_data, "BRAND_SCORE_PATH", brand_score_path),
            patch.object(dashboard_data, "PREDICTIONS_PATH", predictions_path),
            patch.object(dashboard_data, "REALTIME_REVIEWS_PATH", realtime_path),
            patch.object(dashboard_data, "calculate_brand_score", return_value=fresh_payload) as mocked,
        ):
            payload = dashboard_data.dashboard_brand_payload()

        self.assertEqual(payload, fresh_payload)
        mocked.assert_called_once()

    def test_dashboard_keywords_payload_prefers_sentiment_distinct_keywords(self):
        keyword_source = pd.DataFrame(
            {
                "brand_key": ["demo", "demo", "demo"],
                "sentiment": ["Positive", "Neutral", "Negative"],
                "review_date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
                "cleaned_review": [
                    "app easy easy easy love love love great great great",
                    "app okay okay okay filter filter filter items",
                    "app refund refund refund worst worst worst bad bad bad",
                ],
            }
        )

        with patch.object(dashboard_data, "_filtered_keyword_frame_cached", return_value=keyword_source):
            grouped = dashboard_data._dashboard_keyword_groups_cached.__wrapped__(("cache", 1, 1))
            positive = grouped["Positive"]
            neutral = grouped["Neutral"]
            negative = grouped["Negative"]
            overall = dashboard_data._dashboard_keywords_cached.__wrapped__(("cache", 1, 1))

        self.assertNotIn("app", [item["word"] for item in positive])
        self.assertNotIn("app", [item["word"] for item in neutral])
        self.assertNotIn("app", [item["word"] for item in negative])
        self.assertIn("love", [item["word"] for item in positive])
        self.assertIn("okay", [item["word"] for item in neutral])
        self.assertIn("refund", [item["word"] for item in negative])
        self.assertNotIn("app", [item["word"] for item in overall])

    def test_dashboard_keyword_groups_payload_uses_current_disk_cache_for_default_scope(self):
        root = Path(__file__).resolve().parent
        predictions_path = root / "_tmp_keyword_predictions.csv"
        realtime_path = root / "_tmp_keyword_realtime.csv"
        keyword_cache_path = root / "_tmp_keyword_groups_cache.json"
        for path in (predictions_path, realtime_path, keyword_cache_path):
            self.addCleanup(lambda target=path: target.unlink(missing_ok=True))

        predictions_path.write_text("review_id,predicted_sentiment\n1,Positive\n", encoding="utf-8")
        realtime_path.write_text("", encoding="utf-8")
        cached_payload = {
            "Positive": [{"word": "easy", "count": 12}],
            "Neutral": [{"word": "okay", "count": 4}],
            "Negative": [{"word": "refund", "count": 7}],
        }
        keyword_cache_path.write_text(json.dumps(cached_payload), encoding="utf-8")

        base_time = time.time_ns()
        os.utime(predictions_path, ns=(base_time, base_time))
        os.utime(realtime_path, ns=(base_time, base_time))
        os.utime(keyword_cache_path, ns=(base_time + 1_000_000, base_time + 1_000_000))

        with (
            patch.object(dashboard_data, "PREDICTIONS_PATH", predictions_path),
            patch.object(dashboard_data, "REALTIME_REVIEWS_PATH", realtime_path),
            patch.object(dashboard_data, "KEYWORD_GROUPS_CACHE_PATH", keyword_cache_path),
            patch.object(dashboard_data, "_dashboard_keyword_groups_cached") as mocked_groups,
        ):
            payload = dashboard_data.dashboard_keyword_groups_payload()

        self.assertEqual(payload["Positive"][0]["word"], "easy")
        self.assertEqual(payload["Neutral"][0]["word"], "okay")
        self.assertEqual(payload["Negative"][0]["word"], "refund")
        mocked_groups.assert_not_called()

    def test_review_samples_use_current_disk_cache(self):
        root = Path(__file__).resolve().parent
        predictions_path = root / "_tmp_review_sample_predictions.csv"
        realtime_path = root / "_tmp_review_sample_realtime.csv"
        review_sample_cache_path = root / "_tmp_review_samples_cache.pkl"
        for path in (predictions_path, realtime_path, review_sample_cache_path):
            self.addCleanup(lambda target=path: target.unlink(missing_ok=True))

        predictions_path.write_text("review_id,predicted_sentiment\n1,Positive\n", encoding="utf-8")
        realtime_path.write_text("", encoding="utf-8")

        base_time = time.time_ns()
        os.utime(predictions_path, ns=(base_time, base_time))
        os.utime(realtime_path, ns=(base_time, base_time))
        cache_key = (
            str(predictions_path.resolve()),
            int(predictions_path.stat().st_mtime_ns),
            int(predictions_path.stat().st_size),
            str(realtime_path.resolve()),
            int(realtime_path.stat().st_mtime_ns),
            int(realtime_path.stat().st_size),
        )
        cached_frame = pd.DataFrame(
            {
                "row_order": [0],
                "brand_key": ["demo"],
                "platform_key": ["market"],
                "sentiment": ["Positive"],
                "parsed_review_date": pd.to_datetime(["2026-01-01"]),
                "review_date_display": ["2026-01-01"],
                "display_review": ["Fast delivery and very easy checkout."],
                "brand": ["Demo Brand"],
                "platform": ["Demo Market"],
                "rating": [5],
            }
        )
        pd.to_pickle({"signature": cache_key, "frame": cached_frame}, review_sample_cache_path)

        dashboard_data._review_sample_source_frame_cached.cache_clear()
        self.addCleanup(dashboard_data._review_sample_source_frame_cached.cache_clear)

        with (
            patch.object(dashboard_data, "PREDICTIONS_PATH", predictions_path),
            patch.object(dashboard_data, "REALTIME_REVIEWS_PATH", realtime_path),
            patch.object(dashboard_data, "REVIEW_SAMPLE_CACHE_PATH", review_sample_cache_path),
            patch.object(dashboard_data, "_prediction_frame_cached") as mocked_predictions,
        ):
            samples = dashboard_data.review_samples("Positive")

        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["brand"], "Demo Brand")
        self.assertEqual(samples[0]["platform"], "Demo Market")
        mocked_predictions.assert_not_called()


if __name__ == "__main__":
    unittest.main()
