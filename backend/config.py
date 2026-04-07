from __future__ import annotations

import os
import secrets
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


def _env_flag(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value.strip())
    except ValueError:
        return default


def _first_env(*names: str) -> str:
    for name in names:
        raw_value = os.getenv(name)
        if raw_value is None:
            continue
        value = raw_value.strip()
        if value:
            return value
    return ""


def _split_csv_env(name: str) -> tuple[str, ...]:
    raw_value = os.getenv(name, "")
    return tuple(part.strip() for part in raw_value.split(",") if part.strip())


INSECURE_SECRET_KEY_VALUES = {
    "",
    "brandpulse-dev-secret-key",
    "change-this-secret-key",
    "replace-with-a-long-random-secret",
}


def is_insecure_admin_password(value: str) -> bool:
    normalized = str(value or "").strip().casefold()
    return normalized in {
        "",
        "admin123",
        "password",
        "changeme",
        "change-this-admin-password",
    }


BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
RAW_DATA_DIR = DATASET_DIR / "raw"
LEGACY_RAW_DATA_DIR = DATASET_DIR / "csv"
PROCESSED_DATA_DIR = DATASET_DIR / "processed"
MODEL_ARTIFACTS_DIR = DATASET_DIR / "models"
REPORTS_DIR = DATASET_DIR / "reports"
STATE_DIR = DATASET_DIR / "state"
FRONTEND_DIR = BASE_DIR.parent / "frontend"
LOGIN_ILLUSTRATION_PATH = FRONTEND_DIR / "assets" / "login-illustration.svg"
LOCAL_SESSION_SECRET_PATH = BASE_DIR.parent / ".flask-session-secret"
_load_env_file(BASE_DIR.parent / ".env")

for directory in (
    DATASET_DIR,
    RAW_DATA_DIR,
    LEGACY_RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    MODEL_ARTIFACTS_DIR,
    REPORTS_DIR,
    STATE_DIR,
):
    directory.mkdir(parents=True, exist_ok=True)

RAW_DATA_EXCLUSIONS = {
    "cleaned_reviews.csv",
    "feature_dataset.csv",
    "final_predictions.csv",
    "brand_reputation_by_brand.csv",
    "sentiment_trends.csv",
    "platform_summary.csv",
    "model_metrics.csv",
    "training_history.csv",
    "language_evaluation.csv",
    "calibration_report.csv",
    "brand_score.json",
    "model_report.txt",
    "realtime_reviews.csv",
}

TRAINING_SAMPLE_LIMIT_PER_DATASET = 10000

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

MONGO_URI = os.getenv("MONGO_URI", "").strip()
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "brand_review_analysis")
MONGO_REVIEWS_COLLECTION = os.getenv("MONGO_REVIEWS_COLLECTION", "processed_reviews")
MONGO_PREDICTIONS_COLLECTION = os.getenv("MONGO_PREDICTIONS_COLLECTION", "review_predictions")
MONGO_REALTIME_REVIEWS_COLLECTION = os.getenv("MONGO_REALTIME_REVIEWS_COLLECTION", "realtime_reviews")
MONGO_CONNECT_TIMEOUT_MS = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "2000"))

def load_or_create_local_secret(path: Path) -> str:
    try:
        existing_secret = path.read_text(encoding="utf-8").strip()
    except OSError:
        existing_secret = ""
    if existing_secret:
        return existing_secret

    generated_secret = secrets.token_urlsafe(32)
    try:
        path.write_text(generated_secret, encoding="utf-8")
    except OSError:
        return generated_secret
    return generated_secret


def resolve_secret_key(secret_path: Path | None = None) -> str:
    configured_secret = os.getenv("SECRET_KEY", "").strip()
    if configured_secret and configured_secret.casefold() not in INSECURE_SECRET_KEY_VALUES:
        return configured_secret
    return load_or_create_local_secret(secret_path or LOCAL_SESSION_SECRET_PATH)


SECRET_KEY = resolve_secret_key()


def resolve_runtime_server_settings() -> dict[str, str | int | bool]:
    host = _first_env("APP_HOST", "FLASK_RUN_HOST") or "127.0.0.1"
    port = _env_int("APP_PORT", _env_int("FLASK_RUN_PORT", 5000))
    debug = _env_flag("APP_DEBUG", _env_flag("FLASK_DEBUG", False))
    return {
        "host": host,
        "port": port,
        "debug": debug,
    }

DASHBOARD_ADMIN_EMAIL = os.getenv("DASHBOARD_ADMIN_EMAIL", "admin@brandpulse.ai")
DASHBOARD_ADMIN_PASSWORD = os.getenv("DASHBOARD_ADMIN_PASSWORD", "").strip()

ALLOWED_CORS_ORIGINS = _split_csv_env("ALLOWED_CORS_ORIGINS") 

SESSION_COOKIE_SECURE = _env_flag("SESSION_COOKIE_SECURE", False)
