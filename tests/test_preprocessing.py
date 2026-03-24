import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from backend.preprocessing import clean_text, format_review_dates, normalize_platform, raw_csv_files


class PreprocessingTests(unittest.TestCase):
    def test_normalize_platform_extracts_domain_name(self):
        self.assertEqual(normalize_platform("https://www.amazon.in/product/123"), "amazon")

    def test_format_review_dates_handles_strings_timestamps_and_missing_values(self):
        formatted = format_review_dates(pd.Series(["2026-03-01", "1700000000000", None]))

        self.assertEqual(formatted.iloc[0], "2026-03-01")
        self.assertRegex(formatted.iloc[1], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(formatted.iloc[2], "Unknown")

    def test_clean_text_keeps_signal_words_and_removes_basic_stopwords(self):
        cleaned = clean_text("Delivery was very late but the replacement product was amazing.")

        self.assertIn("delivery", cleaned)
        self.assertIn("late", cleaned)
        self.assertIn("replacement", cleaned)
        self.assertIn("product", cleaned)
        self.assertIn("amazing", cleaned)
        self.assertNotIn(" was ", f" {cleaned} ")

    def test_clean_text_preserves_negative_direction_for_negated_phrases(self):
        cleaned = clean_text("Product is not good and refund not received.")

        self.assertIn("bad", cleaned)
        self.assertIn("refund", cleaned)
        self.assertIn("missing", cleaned)
        self.assertNotIn("received", cleaned)

    def test_raw_csv_files_prefers_raw_locations_and_excludes_generated_csvs(self):
        fixture_root = Path(__file__).resolve().parent / "fixtures" / "raw_dataset"
        raw_dir = fixture_root / "raw"
        csv_dir = fixture_root / "csv"

        with (
            patch("backend.preprocessing.DATASET_DIR", fixture_root),
            patch("backend.preprocessing.RAW_DATA_DIR", raw_dir),
            patch("backend.preprocessing.LEGACY_RAW_DATA_DIR", csv_dir),
        ):
            discovered = raw_csv_files()

        names = [path.name for path in discovered]
        self.assertEqual(names, ["legacy.csv", "preferred.csv", "root.csv"])


if __name__ == "__main__":
    unittest.main()
