from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

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
}

TRAINING_SAMPLE_LIMIT_PER_DATASET = 10000

CLEANED_DATA_PATH = DATASET_DIR / "cleaned_reviews.csv"
FEATURE_DATASET_PATH = DATASET_DIR / "feature_dataset.csv"
MODEL_PATH = DATASET_DIR / "sentiment_model.pkl"
VECTORIZER_PATH = DATASET_DIR / "tfidf_vectorizer.pkl"
PREDICTIONS_PATH = DATASET_DIR / "final_predictions.csv"
BRAND_SCORE_PATH = DATASET_DIR / "brand_score.json"
BRAND_REPUTATION_BY_BRAND_PATH = DATASET_DIR / "brand_reputation_by_brand.csv"
MODEL_REPORT_PATH = DATASET_DIR / "model_report.txt"
MODEL_METRICS_PATH = DATASET_DIR / "model_metrics.csv"
TRAINING_HISTORY_PATH = DATASET_DIR / "training_history.csv"
SENTIMENT_TRENDS_PATH = DATASET_DIR / "sentiment_trends.csv"
PLATFORM_SUMMARY_PATH = DATASET_DIR / "platform_summary.csv"
USER_STORE_PATH = DATASET_DIR / "dashboard_users.json"

CONFUSION_MATRIX_PATH = DATASET_DIR / "confusion_matrix.png"
MODEL_METRICS_CHART_PATH = DATASET_DIR / "model_metrics.png"
TRAINING_HISTORY_CHART_PATH = DATASET_DIR / "training_history.png"
SENTIMENT_DISTRIBUTION_PATH = DATASET_DIR / "sentiment_distribution.png"
REVIEW_TRENDS_CHART_PATH = DATASET_DIR / "review_trends.png"
KEYWORD_FREQUENCY_PATH = DATASET_DIR / "keyword_frequency.png"
PLATFORM_DISTRIBUTION_PATH = DATASET_DIR / "platform_distribution.png"

MONGO_URI = ("mongodb+srv://kik81252:kika2005@cluster0.gmpo9u2.mongodb.net/?appName=Cluster0")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "brand_review_analysis")
MONGO_REVIEWS_COLLECTION = os.getenv("MONGO_REVIEWS_COLLECTION", "processed_reviews")
MONGO_PREDICTIONS_COLLECTION = os.getenv("MONGO_PREDICTIONS_COLLECTION", "review_predictions")

SECRET_KEY = os.getenv("SECRET_KEY", "brandpulse-dev-secret-key")
DASHBOARD_ADMIN_EMAIL = os.getenv("DASHBOARD_ADMIN_EMAIL", "admin@brandpulse.ai")
DASHBOARD_ADMIN_PASSWORD = os.getenv("DASHBOARD_ADMIN_PASSWORD", "admin123")
