from __future__ import annotations

import os
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)) or str(default))
    except ValueError:
        return default


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATASET_DIR = Path(_env("DATASET_DIR", str(BASE_DIR / "dataset")))
RAW_DATA_DIR = Path(_env("RAW_DATA_DIR", str(DATASET_DIR / "raw")))
LEGACY_RAW_DATA_DIR = Path(_env("LEGACY_RAW_DATA_DIR", str(DATASET_DIR / "csv")))
PROCESSED_DATA_DIR = Path(_env("PROCESSED_DATA_DIR", str(DATASET_DIR / "processed")))
MODEL_ARTIFACTS_DIR = Path(_env("MODEL_ARTIFACTS_DIR", str(DATASET_DIR / "models")))
REPORTS_DIR = Path(_env("REPORTS_DIR", str(DATASET_DIR / "reports")))
STATE_DIR = Path(_env("STATE_DIR", str(DATASET_DIR / "state")))
FRONTEND_DIR = PROJECT_ROOT / "frontend"
LOGIN_ILLUSTRATION_PATH = FRONTEND_DIR / "assets" / "login-illustration.svg"

for d in (DATASET_DIR, RAW_DATA_DIR, LEGACY_RAW_DATA_DIR, PROCESSED_DATA_DIR, MODEL_ARTIFACTS_DIR, REPORTS_DIR, STATE_DIR):
    d.mkdir(parents=True, exist_ok=True)

RAW_DATA_EXCLUSIONS = {"cleaned_reviews.csv", "feature_dataset.csv", "final_predictions.csv", "brand_reputation_by_brand.csv", "sentiment_trends.csv", "platform_summary.csv", "model_metrics.csv", "training_history.csv", "language_evaluation.csv", "calibration_report.csv", "brand_score.json", "model_report.txt", "realtime_reviews.csv"}
TRAINING_SAMPLE_LIMIT_PER_DATASET = _env_int("TRAINING_SAMPLE_LIMIT_PER_DATASET", 10000)
DEFAULT_DATASET_CONNECTOR_FILES = ("Alibaba.csv", "Aliexpress.csv", "Amazon shopping.csv", "Daraz Online Shopping App.csv", "eBay online shopping & selling.csv", "Flipkart.csv", "Lazada.csv", "Meesho.csv", "Myntra.csv", "Shein.csv", "Snapdeal.csv", "Walmart.csv")
DATASET_CONNECTOR_FILE_NAMES = tuple(part.strip() for part in _env("DATASET_CONNECTOR_FILE_NAMES", "").split(",") if part.strip()) or DEFAULT_DATASET_CONNECTOR_FILES

CLEANED_DATA_PATH = PROCESSED_DATA_DIR / "cleaned_reviews.csv"
FEATURE_DATASET_PATH = PROCESSED_DATA_DIR / "feature_dataset.csv"
PREDICTIONS_PATH = PROCESSED_DATA_DIR / "final_predictions.csv"
REALTIME_REVIEWS_PATH = PROCESSED_DATA_DIR / "realtime_reviews.csv"
BRAND_SCORE_PATH = PROCESSED_DATA_DIR / "brand_score.json"
BRAND_REPUTATION_BY_BRAND_PATH = PROCESSED_DATA_DIR / "brand_reputation_by_brand.csv"
SENTIMENT_TRENDS_PATH = PROCESSED_DATA_DIR / "sentiment_trends.csv"
PLATFORM_SUMMARY_PATH = PROCESSED_DATA_DIR / "platform_summary.csv"

MODEL_PATH = MODEL_ARTIFACTS_DIR / "sentiment_model.pkl"
VECTORIZER_PATH = MODEL_ARTIFACTS_DIR / "tfidf_vectorizer.pkl"
LEGACY_VECTORIZER_PATH = MODEL_ARTIFACTS_DIR / "tfidf_vectorizer_legacy.pkl"
LEGACY_MATRIX_PATH = MODEL_ARTIFACTS_DIR / "X_tfidf_legacy.pkl"

MODEL_REPORT_PATH = REPORTS_DIR / "model_report.txt"
MODEL_METRICS_PATH = REPORTS_DIR / "model_metrics.csv"
TRAINING_HISTORY_PATH = REPORTS_DIR / "training_history.csv"
LANGUAGE_EVALUATION_PATH = REPORTS_DIR / "language_evaluation.csv"
CALIBRATION_REPORT_PATH = REPORTS_DIR / "calibration_report.csv"
CONFUSION_MATRIX_PATH = REPORTS_DIR / "confusion_matrix.png"
MODEL_METRICS_CHART_PATH = REPORTS_DIR / "model_metrics.png"
TRAINING_HISTORY_CHART_PATH = REPORTS_DIR / "training_history.png"
SENTIMENT_DISTRIBUTION_PATH = REPORTS_DIR / "sentiment_distribution.png"
REVIEW_TRENDS_CHART_PATH = REPORTS_DIR / "review_trends.png"
KEYWORD_FREQUENCY_PATH = REPORTS_DIR / "keyword_frequency.png"
PLATFORM_DISTRIBUTION_PATH = REPORTS_DIR / "platform_distribution.png"

USER_STORE_PATH = STATE_DIR / "dashboard_users.json"
CONNECTOR_STATE_PATH = STATE_DIR / "connector_state.json"
CONNECTOR_SCHEDULER_PATH = STATE_DIR / "connector_scheduler.json"
