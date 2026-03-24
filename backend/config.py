from __future__ import annotations

import os
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
RAW_DATA_DIR = DATASET_DIR / "raw"
LEGACY_RAW_DATA_DIR = DATASET_DIR / "csv"
FRONTEND_DIR = BASE_DIR.parent / "frontend"
LOGIN_ILLUSTRATION_PATH = FRONTEND_DIR / "assets" / "login-illustration.svg"
_load_env_file(BASE_DIR.parent / ".env")

RAW_DATA_EXCLUSIONS = {
    "cleaned_reviews.csv",
    "feature_dataset.csv",
    "final_predictions.csv",
    "brand_reputation_by_brand.csv",
    "sentiment_trends.csv",
    "platform_summary.csv",
    "model_metrics.csv",
    "training_history.csv",
    "brand_score.json",
    "model_report.txt",
    "realtime_reviews.csv",
}

TRAINING_SAMPLE_LIMIT_PER_DATASET = 10000

CLEANED_DATA_PATH = DATASET_DIR / "cleaned_reviews.csv"
FEATURE_DATASET_PATH = DATASET_DIR / "feature_dataset.csv"
MODEL_PATH = DATASET_DIR / "sentiment_model.pkl"
VECTORIZER_PATH = DATASET_DIR / "tfidf_vectorizer.pkl"
PREDICTIONS_PATH = DATASET_DIR / "final_predictions.csv"
REALTIME_REVIEWS_PATH = DATASET_DIR / "realtime_reviews.csv"
BRAND_SCORE_PATH = DATASET_DIR / "brand_score.json"
BRAND_REPUTATION_BY_BRAND_PATH = DATASET_DIR / "brand_reputation_by_brand.csv"
MODEL_REPORT_PATH = DATASET_DIR / "model_report.txt"
MODEL_METRICS_PATH = DATASET_DIR / "model_metrics.csv"
TRAINING_HISTORY_PATH = DATASET_DIR / "training_history.csv"
LANGUAGE_EVALUATION_PATH = DATASET_DIR / "language_evaluation.csv"
CALIBRATION_REPORT_PATH = DATASET_DIR / "calibration_report.csv"
SENTIMENT_TRENDS_PATH = DATASET_DIR / "sentiment_trends.csv"
PLATFORM_SUMMARY_PATH = DATASET_DIR / "platform_summary.csv"
USER_STORE_PATH = DATASET_DIR / "dashboard_users.json"
CONNECTOR_STATE_PATH = DATASET_DIR / "connector_state.json"
CONNECTOR_SCHEDULER_PATH = DATASET_DIR / "connector_scheduler.json"

CONFUSION_MATRIX_PATH = DATASET_DIR / "confusion_matrix.png"
MODEL_METRICS_CHART_PATH = DATASET_DIR / "model_metrics.png"
TRAINING_HISTORY_CHART_PATH = DATASET_DIR / "training_history.png"
SENTIMENT_DISTRIBUTION_PATH = DATASET_DIR / "sentiment_distribution.png"
REVIEW_TRENDS_CHART_PATH = DATASET_DIR / "review_trends.png"
KEYWORD_FREQUENCY_PATH = DATASET_DIR / "keyword_frequency.png"
PLATFORM_DISTRIBUTION_PATH = DATASET_DIR / "platform_distribution.png"

MONGO_URI = os.getenv("MONGO_URI", "").strip()
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "brand_review_analysis")
MONGO_REVIEWS_COLLECTION = os.getenv("MONGO_REVIEWS_COLLECTION", "processed_reviews")
MONGO_PREDICTIONS_COLLECTION = os.getenv("MONGO_PREDICTIONS_COLLECTION", "review_predictions")
MONGO_REALTIME_REVIEWS_COLLECTION = os.getenv("MONGO_REALTIME_REVIEWS_COLLECTION", "realtime_reviews")
MONGO_CONNECT_TIMEOUT_MS = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "2000"))

SECRET_KEY = os.getenv("SECRET_KEY", "brandpulse-dev-secret-key")
DASHBOARD_ADMIN_EMAIL = os.getenv("DASHBOARD_ADMIN_EMAIL", "admin@brandpulse.ai")
DASHBOARD_ADMIN_PASSWORD = os.getenv("DASHBOARD_ADMIN_PASSWORD", "admin123")
