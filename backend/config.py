from __future__ import annotations

import os
import secrets
from pathlib import Path

from backend.paths import (
    PROJECT_ROOT,
    FRONTEND_DIR,
    LOGIN_ILLUSTRATION_PATH,
    DATASET_DIR,
    RAW_DATA_DIR,
    LEGACY_RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    MODEL_ARTIFACTS_DIR,
    REPORTS_DIR,
    STATE_DIR,
    RAW_DATA_EXCLUSIONS,
    TRAINING_SAMPLE_LIMIT_PER_DATASET,
    DATASET_CONNECTOR_FILE_NAMES,
    CLEANED_DATA_PATH,
    FEATURE_DATASET_PATH,
    PREDICTIONS_PATH,
    REALTIME_REVIEWS_PATH,
    BRAND_SCORE_PATH,
    BRAND_REPUTATION_BY_BRAND_PATH,
    SENTIMENT_TRENDS_PATH,
    PLATFORM_SUMMARY_PATH,
    MODEL_PATH,
    VECTORIZER_PATH,
    LEGACY_VECTORIZER_PATH,
    LEGACY_MATRIX_PATH,
    MODEL_REPORT_PATH,
    MODEL_METRICS_PATH,
    TRAINING_HISTORY_PATH,
    LANGUAGE_EVALUATION_PATH,
    CALIBRATION_REPORT_PATH,
    CONFUSION_MATRIX_PATH,
    MODEL_METRICS_CHART_PATH,
    TRAINING_HISTORY_CHART_PATH,
    SENTIMENT_DISTRIBUTION_PATH,
    REVIEW_TRENDS_CHART_PATH,
    KEYWORD_FREQUENCY_PATH,
    PLATFORM_DISTRIBUTION_PATH,
    USER_STORE_PATH,
    CONNECTOR_STATE_PATH,
    CONNECTOR_SCHEDULER_PATH,
)

def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)) or str(default))
    except ValueError:
        return default


def _env_flag(name: str, default: bool = False) -> bool:
    raw = _env(name, "")
    return default if not raw else raw.lower() in {"1", "true", "yes", "on"}


def _split_csv_env(name: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in _env(name, "").split(",") if part.strip())


def _first_env(*names: str) -> str:
    for name in names:
        value = _env(name, "")
        if value:
            return value
    return ""


def is_insecure_admin_password(value: str) -> bool:
    return str(value or "").strip().casefold() in {"", "admin123", "password", "changeme", "change-this-admin-password"}


INSECURE_SECRET_KEY_VALUES = {"", "brandpulse-dev-secret-key", "change-this-secret-key", "replace-with-a-long-random-secret"}
DEFAULT_ALLOWED_CORS_ORIGINS = ("http://127.0.0.1:5000", "http://localhost:5000", "http://127.0.0.1:5500", "http://localhost:5500")
HOST = _first_env("APP_HOST", "FLASK_RUN_HOST") or "0.0.0.0"
PORT = _env_int("APP_PORT", _env_int("PORT", _env_int("FLASK_RUN_PORT", 5000)))
DEBUG = _env_flag("APP_DEBUG", _env_flag("FLASK_DEBUG", False))
LOCAL_SESSION_SECRET_PATH = PROJECT_ROOT / ".flask-session-secret"

MONGO_URI = _env("MONGO_URI", "")
MONGO_DB_NAME = _env("MONGO_DB_NAME", "brand_review_analysis") or "brand_review_analysis"
MONGO_REVIEWS_COLLECTION = _env("MONGO_REVIEWS_COLLECTION", "processed_reviews") or "processed_reviews"
MONGO_PREDICTIONS_COLLECTION = _env("MONGO_PREDICTIONS_COLLECTION", "review_predictions") or "review_predictions"
MONGO_REALTIME_REVIEWS_COLLECTION = _env("MONGO_REALTIME_REVIEWS_COLLECTION", "realtime_reviews") or "realtime_reviews"
MONGO_CONNECT_TIMEOUT_MS = _env_int("MONGO_CONNECT_TIMEOUT_MS", 2000)

DEFAULT_KAFKA_BOOTSTRAP_SERVERS = _env("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DASHBOARD_ADMIN_EMAIL = _env("DASHBOARD_ADMIN_EMAIL", "admin@brandpulse.ai") or "admin@brandpulse.ai"
DASHBOARD_ADMIN_PASSWORD = _env("DASHBOARD_ADMIN_PASSWORD", "")
ALLOWED_CORS_ORIGINS = _split_csv_env("ALLOWED_CORS_ORIGINS") or DEFAULT_ALLOWED_CORS_ORIGINS
SESSION_COOKIE_SECURE = _env_flag("SESSION_COOKIE_SECURE", False)
FRONTEND_API_BASE_URL = _first_env("FRONTEND_API_BASE_URL", "API_BASE_URL").rstrip("/")


def load_or_create_local_secret(path: Path) -> str:
    try:
        existing = path.read_text(encoding="utf-8").strip()
    except OSError:
        existing = ""
    if existing:
        return existing
    generated = secrets.token_urlsafe(32)
    try:
        path.write_text(generated, encoding="utf-8")
    except OSError:
        return generated
    return generated


def resolve_secret_key(secret_path: Path | None = None) -> str:
    configured = _env("SECRET_KEY", "")
    if configured and configured.casefold() not in INSECURE_SECRET_KEY_VALUES:
        return configured
    return load_or_create_local_secret(secret_path or LOCAL_SESSION_SECRET_PATH)


SECRET_KEY = resolve_secret_key()


def resolve_runtime_server_settings() -> dict[str, str | int | bool]:
    host = _first_env("APP_HOST", "FLASK_RUN_HOST") or "0.0.0.0"
    port = _env_int("APP_PORT", _env_int("PORT", _env_int("FLASK_RUN_PORT", 5000)))
    debug = _env_flag("APP_DEBUG", _env_flag("FLASK_DEBUG", False))
    return {"host": host, "port": port, "debug": debug}


def resolve_allowed_cors_origins() -> tuple[str, ...]:
    return _split_csv_env("ALLOWED_CORS_ORIGINS") or DEFAULT_ALLOWED_CORS_ORIGINS
