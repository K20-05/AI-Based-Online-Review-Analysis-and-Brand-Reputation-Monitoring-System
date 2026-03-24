import unittest
from pathlib import Path
from unittest.mock import patch

from backend.connectors import DatasetCsvConnector


class ConnectorTests(unittest.TestCase):
    def test_dataset_csv_connector_can_poll_all_files_in_round_robin_order(self):
        fixture_root = Path(__file__).resolve().parent / "fixtures" / "raw_dataset"
        raw_dir = fixture_root / "raw"
        csv_dir = fixture_root / "csv"

        connector = DatasetCsvConnector()
        with (
            patch("backend.connectors.DATASET_DIR", fixture_root),
            patch("backend.connectors.RAW_DATA_DIR", raw_dir),
            patch("backend.connectors.LEGACY_RAW_DATA_DIR", csv_dir),
        ):
            result = connector.fetch_reviews(limit=3, options={"all_files": True})

        self.assertEqual(result.fetched_count, 3)
        self.assertEqual([row["platform"] for row in result.reviews], ["legacy", "preferred", "root"])
        self.assertEqual(
            [row["source_type"] for row in result.reviews],
            [
                "connector:dataset_csv:legacy.csv",
                "connector:dataset_csv:preferred.csv",
                "connector:dataset_csv:root.csv",
            ],
        )


if __name__ == "__main__":
    unittest.main()
