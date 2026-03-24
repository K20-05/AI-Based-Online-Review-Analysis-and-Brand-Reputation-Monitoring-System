import json
import os
import time
import unittest
from pathlib import Path
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
