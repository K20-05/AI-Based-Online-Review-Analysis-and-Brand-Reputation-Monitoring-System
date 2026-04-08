from __future__ import annotations

from datetime import datetime, UTC
import os
from pathlib import Path
import sys

from flask import Flask, jsonify, render_template, request, send_file, session
from flask_cors import CORS
import pandas as pd
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.brand_score import calculate_brand_score
from backend.config import (
    ALLOWED_CORS_ORIGINS,
    BRAND_REPUTATION_BY_BRAND_PATH,
    DASHBOARD_ADMIN_EMAIL,
    DASHBOARD_ADMIN_PASSWORD,
    FRONTEND_DIR,
    LOGIN_ILLUSTRATION_PATH,
    MODEL_METRICS_PATH,
    MODEL_PATH,
    MODEL_REPORT_PATH,
    PREDICTIONS_PATH,
    REALTIME_REVIEWS_PATH,
    resolve_runtime_server_settings,
    SECRET_KEY,
    SESSION_COOKIE_SECURE,
    USER_STORE_PATH,
    VECTORIZER_PATH,
    is_insecure_admin_password,
)
from backend.database import mongo_enabled
from backend import auth_support, dashboard_data
from backend.admin_routes import create_admin_blueprint
from backend.auth_routes import create_auth_blueprint
from backend.core_routes import create_core_blueprint
from backend.dashboard_routes import create_dashboard_blueprint
from backend.feature_extraction import build_feature_dataset
from backend.model_training import train_models
from backend.connector_scheduler import ensure_scheduler_started, scheduler_status, update_scheduler_config
from backend.connectors import list_connectors, poll_connector
from backend.model_artifacts import load_model_artifacts
from backend.predict import predict_dataset
from backend.prediction_service import parse_predict_payload, predict_batch_reviews, predict_single_review
from backend.realtime_reviews import ingest_realtime_reviews, latest_realtime_reviews, realtime_review_summary
from backend.preprocessing import preprocess_reviews
from backend.visualization import generate_visualizations

app = Flask(
    __name__,
    static_folder=str(FRONTEND_DIR),
    static_url_path="",
    template_folder=str(FRONTEND_DIR),
)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
    SEND_FILE_MAX_AGE_DEFAULT=0,
)
CORS(app, supports_credentials=True, origins=list(ALLOWED_CORS_ORIGINS))

_USER_STORE_CACHE = auth_support.USER_STORE_CACHE

API_DOCS = {
    "name": "BrandPulse AI",
    "version": "1.0",
    "base_url": "/api",
    "services": {
        "pipeline": [
            {
                "method": "POST",
                "path": "/api/preprocess",
                "summary": "Normalize and clean all raw review datasets.",
                "auth_required": True,
                "request_body": {},
                "response": {
                    "success": True,
                    "message": "Preprocessing completed",
                    "rows": 715280,
                },
                "error_responses": [
                    {"status": 401, "body": {"success": False, "error": "Authentication required"}},
                    {"status": 404, "body": {"success": False, "error": "No raw CSV files found"}},
                ],
            },
            {
                "method": "POST",
                "path": "/api/features",
                "summary": "Generate sampled feature artifacts from cleaned reviews.",
                "auth_required": True,
                "request_body": {},
                "response": {
                    "success": True,
                    "message": "Feature extraction completed",
                    "rows": 121261,
                },
                "error_responses": [
                    {"status": 401, "body": {"success": False, "error": "Authentication required"}},
                    {"status": 404, "body": {"success": False, "error": "Cleaned dataset not found. Run preprocessing first."}},
                ],
            },
            {
                "method": "POST",
                "path": "/api/train",
                "summary": "Train the sentiment model and store metrics.",
                "auth_required": True,
                "request_body": {},
                "response": {
                    "success": True,
                    "message": "Training completed",
                    "models": [
                        {
                            "model": "Logistic Regression",
                            "accuracy": 86.51,
                            "precision_macro": 0.6763,
                            "recall_macro": 0.6209,
                            "f1_macro": 0.6087,
                        }
                    ],
                },
                "error_responses": [
                    {"status": 401, "body": {"success": False, "error": "Authentication required"}},
                    {"status": 404, "body": {"success": False, "error": "Cleaned dataset not found. Run preprocessing first."}},
                ],
            },
        ],
        "prediction": [
            {
                "method": "POST",
                "path": "/api/predict",
                "summary": "Predict sentiment for a single review with Indian-language normalization.",
                "auth_required": True,
                "request_body": {
                    "review_text": "\u0921\u093f\u0932\u0940\u0935\u0930\u0940 \u092c\u0939\u0941\u0924 \u0932\u0947\u091f \u0939\u0941\u0908 \u0914\u0930 \u092a\u0948\u0915\u0947\u091c \u0921\u0948\u092e\u0947\u091c \u0925\u093e\u0964",
                    "platform": "Nykaa",
                    "brand": "Nykaa",
                    "rating": 1,
                },
                "response": {
                    "review_text": "\u0921\u093f\u0932\u0940\u0935\u0930\u0940 \u092c\u0939\u0941\u0924 \u0932\u0947\u091f \u0939\u0941\u0908 \u0914\u0930 \u092a\u0948\u0915\u0947\u091c \u0921\u0948\u092e\u0947\u091c \u0925\u093e\u0964",
                    "cleaned_review": "delivery late package damaged",
                    "source_language": "hi",
                    "source_language_label": "Hindi",
                    "translation_applied": True,
                    "rating": 1,
                    "platform": "Nykaa",
                    "brand": "Nykaa",
                    "predicted_sentiment": "Negative",
                },
                "error_responses": [
                    {"status": 400, "body": {"success": False, "error": "review_text is required"}},
                    {"status": 401, "body": {"success": False, "error": "Authentication required"}},
                    {"status": 404, "body": {"success": False, "error": "Model artifacts are missing. Run training first."}},
                ],
            },
            {
                "method": "POST",
                "path": "/api/predict/batch",
                "summary": "Predict sentiment for submitted reviews or the cleaned dataset with Indian-language normalization.",
                "auth_required": True,
                "request_body": {},
                "response": {
                    "success": True,
                    "message": "Batch prediction completed",
                    "rows": 715275,
                    "brand_score": {
                        "total_reviews": 715275,
                        "positive": 406803,
                        "neutral": 3678,
                        "negative": 304794,
                        "positive_pct": 56.87,
                        "neutral_pct": 0.51,
                        "negative_pct": 42.61,
                        "brand_reputation_score": 14.26,
                        "brand_scores": [
                            {
                                "brand": "Alibaba",
                                "total_reviews": 10000,
                                "positive_pct": 77.72,
                                "neutral_pct": 0.39,
                                "negative_pct": 21.89,
                                "brand_reputation_score": 55.82,
                            }
                        ],
                    },
                },
                "error_responses": [
                    {"status": 401, "body": {"success": False, "error": "Authentication required"}},
                    {"status": 404, "body": {"success": False, "error": "Model artifacts are missing. Run training first."}},
                ],
            },
        ],
        "scoring": [
            {
                "method": "POST",
                "path": "/api/brand-score",
                "summary": "Recalculate overall and per-brand reputation scores from predictions.",
                "auth_required": True,
                "request_body": {},
                "response": {
                    "success": True,
                    "message": "Brand scoring completed",
                    "brand_score": {
                        "total_reviews": 715275,
                        "positive": 406803,
                        "neutral": 3678,
                        "negative": 304794,
                        "positive_pct": 56.87,
                        "neutral_pct": 0.51,
                        "negative_pct": 42.61,
                        "brand_reputation_score": 14.26,
                        "brand_scores": [
                            {
                                "brand": "Alibaba",
                                "total_reviews": 10000,
                                "positive_pct": 77.72,
                                "neutral_pct": 0.39,
                                "negative_pct": 21.89,
                                "brand_reputation_score": 55.82,
                            }
                        ],
                    },
                },
                "error_responses": [
                    {"status": 401, "body": {"success": False, "error": "Authentication required"}},
                    {"status": 404, "body": {"success": False, "error": "Prediction dataset not found. Run prediction first."}},
                ],
            }
        ],
        "dashboard": [
            {"method": "GET", "path": "/api/dashboard/summary", "summary": "Get overall dashboard summary and brand scores. Add ?refresh=1 to force a live recalculation.", "auth_required": True},
            {"method": "GET", "path": "/api/dashboard/trends", "summary": "Get monthly sentiment trend data.", "auth_required": True},
            {"method": "GET", "path": "/api/dashboard/keywords", "summary": "Get top processed keywords.", "auth_required": True},
            {"method": "GET", "path": "/api/dashboard/platforms", "summary": "Get platform sentiment breakdown.", "auth_required": True},
            {"method": "GET", "path": "/api/dashboard/brands", "summary": "Get brand-level reputation rows.", "auth_required": True},
            {"method": "GET", "path": "/api/dashboard/realtime-reviews", "summary": "Get the latest ingested realtime ecommerce reviews.", "auth_required": True},
            {"method": "GET", "path": "/api/dashboard/realtime-summary", "summary": "Get realtime review storage summary.", "auth_required": True},
            {"method": "POST", "path": "/api/dashboard/refresh", "summary": "Refresh dashboard visual outputs and score files.", "auth_required": True},
        ],
        "system": [
            {"method": "GET", "path": "/api/health", "summary": "Check backend artifact readiness."},
            {
                "method": "POST",
                "path": "/api/auth/register",
                "summary": "Create a dashboard user account. Sign in separately after registration.",
                "request_body": {"name": "Aarav Singh", "email": "aarav@brandpulse.ai", "password": "secure123"},
                "response": {"success": True, "message": "Account created", "user": "aarav@brandpulse.ai"},
                "error_responses": [
                    {"status": 400, "body": {"success": False, "error": "name, email and password are required"}},
                    {"status": 409, "body": {"success": False, "error": "An account with this email already exists"}},
                ],
            },
            {
                "method": "POST",
                "path": "/api/auth/login",
                "summary": "Authenticate a dashboard user and create a session.",
                "request_body": {"email": "aarav@brandpulse.ai", "password": "secure123"},
                "response": {"success": True, "message": "Login successful", "user": "aarav@brandpulse.ai"},
                "error_responses": [
                    {"status": 400, "body": {"success": False, "error": "email and password are required"}},
                    {"status": 401, "body": {"success": False, "error": "Invalid email or password"}},
                ],
            },
            {
                "method": "POST",
                "path": "/api/auth/reset-password",
                "summary": "Reset the active user's password, or any user's password if the session belongs to an admin.",
                "auth_required": True,
                "request_body": {"email": "aarav@brandpulse.ai", "new_password": "newSecure123!"},
                "response": {"success": True, "message": "Password updated", "user": "aarav@brandpulse.ai"},
                "error_responses": [
                    {"status": 400, "body": {"success": False, "error": "email and new_password are required"}},
                    {"status": 401, "body": {"success": False, "error": "Authentication required"}},
                    {"status": 403, "body": {"success": False, "error": "You can only reset your own password"}},
                    {"status": 404, "body": {"success": False, "error": "No account found for this email"}},
                ],
            },
            {
                "method": "POST",
                "path": "/api/auth/logout",
                "summary": "Clear the current dashboard session.",
                "auth_required": False,
                "request_body": {},
                "response": {"success": True, "message": "Logout successful"},
            },
            {
                "method": "GET",
                "path": "/api/auth/session",
                "summary": "Read the current dashboard session state.",
                "auth_required": False,
                "response": {"authenticated": True, "user": "admin@brandpulse.ai"},
            },
            {"method": "GET", "path": "/api/docs", "summary": "Read API contract and examples."},
            {"method": "GET", "path": "/api/openapi.json", "summary": "Read API contract in machine-friendly JSON."},
            {
                "method": "POST",
                "path": "/api/reviews/realtime",
                "summary": "Ingest one or more realtime ecommerce reviews, predict sentiment immediately, and persist them.",
                "auth_required": True,
                "request_body": {
                    "reviews": [
                        {
                            "review_text": "Delivery was late and the refund is still pending.",
                            "platform": "Flipkart",
                            "brand": "Flipkart",
                            "rating": 1,
                            "source_type": "api",
                        }
                    ]
                },
            },
            {"method": "GET", "path": "/api/connectors", "summary": "List available realtime review connectors.", "auth_required": True},
            {
                "method": "POST",
                "path": "/api/connectors/poll",
                "summary": "Poll a configured connector and ingest fetched reviews into realtime storage.",
                "auth_required": True,
                "request_body": {
                    "connector": "mock_marketplace",
                    "limit": 10,
                    "reset_cursor": False,
                    "options": {"platform": "Demo Store", "brand": "Demo Store"},
                },
            },
            {
                "method": "POST",
                "path": "/api/connectors/poll",
                "summary": "Poll a Kafka topic and ingest JSON review messages into realtime storage.",
                "auth_required": True,
                "request_body": {
                    "connector": "kafka_topic",
                    "limit": 10,
                    "reset_cursor": False,
                    "options": {
                        "bootstrap_servers": "localhost:9092",
                        "topic": "brandpulse.reviews",
                        "group_id": "brandpulse-realtime",
                        "platform": "Nykaa",
                        "brand": "Nykaa",
                        "auto_offset_reset": "latest",
                    },
                },
            },
            {"method": "GET", "path": "/api/connectors/scheduler", "summary": "Read automatic connector polling scheduler status.", "auth_required": True},
            {
                "method": "POST",
                "path": "/api/connectors/scheduler",
                "summary": "Update automatic connector polling scheduler configuration.",
                "auth_required": True,
                "request_body": {
                    "enabled": True,
                    "connector": "mock_marketplace",
                    "interval_seconds": 15,
                    "limit": 1,
                    "reset_cursor_on_start": False,
                    "options": {"platform": "Auto Demo Store", "brand": "Auto Demo Store"},
                },
            },
        ],
    },
}

@app.errorhandler(FileNotFoundError)
def handle_missing_file(error):
    return jsonify({"success": False, "error": str(error)}), 404


@app.errorhandler(ValueError)
def handle_value_error(error):
    return jsonify({"success": False, "error": str(error)}), 400


@app.errorhandler(HTTPException)
def handle_http_exception(error):
    return jsonify({"success": False, "error": error.description}), error.code


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500


def json_success(message: str, **data):
    payload = {"success": True, "message": message}
    payload.update(data)
    return jsonify(payload)


def json_error(message: str, status_code: int = 400):
    return jsonify({"success": False, "error": message}), status_code


def session_user_email() -> str | None:
    return auth_support.session_user_email()


def current_user() -> str | None:
    return auth_support.current_user(current_user_record)


def current_user_record() -> dict | None:
    return auth_support.current_user_record(find_user)


def current_user_role() -> str:
    return auth_support.current_user_role(current_user_record)


def can_seed_dashboard_admin() -> bool:
    return auth_support.can_seed_dashboard_admin(
        DASHBOARD_ADMIN_EMAIL,
        DASHBOARD_ADMIN_PASSWORD,
        is_insecure_admin_password,
        validate_password_strength,
    )


def user_store_signature() -> tuple[str, int, int]:
    return auth_support.user_store_signature(USER_STORE_PATH)


def _clone_users(users: list[dict]) -> list[dict]:
    return auth_support.clone_users(users)


def _user_index(users: list[dict]) -> dict[str, dict]:
    return auth_support.user_index(users)


def _update_user_store_cache(users: list[dict], signature: tuple[str, int, int] | None = None) -> None:
    auth_support.update_user_store_cache(users, USER_STORE_PATH, signature)


def _cached_user_store_snapshot(force_reload: bool = False) -> dict:
    return auth_support.cached_user_store_snapshot(USER_STORE_PATH, force_reload=force_reload)


def load_user_store() -> list[dict]:
    return auth_support.load_user_store(
        USER_STORE_PATH,
        DASHBOARD_ADMIN_EMAIL,
        DASHBOARD_ADMIN_PASSWORD,
        generate_password_hash,
        is_insecure_admin_password,
        validate_password_strength,
    )


def save_user_store(users: list[dict]) -> None:
    auth_support.save_user_store(users, USER_STORE_PATH)


def find_user(email: str) -> dict | None:
    return auth_support.find_user(email, load_user_store)


def serialize_user(user: dict | None) -> dict | None:
    return auth_support.serialize_user(user)


def normalize_public_role(role: str | None) -> str:
    return auth_support.normalize_public_role(role)


def validate_password_strength(password: str) -> str | None:
    return auth_support.validate_password_strength(password)


require_auth = auth_support.build_require_auth(current_user_record, json_error)
require_roles = auth_support.build_require_roles(current_user_record, current_user_role, json_error)


app.register_blueprint(
    create_auth_blueprint(
        {
            "jsonify": jsonify,
            "render_template": render_template,
            "request": request,
            "session": session,
            "UTC": UTC,
            "datetime": datetime,
            "check_password_hash": check_password_hash,
            "generate_password_hash": generate_password_hash,
            "json_success": json_success,
            "json_error": json_error,
            "load_user_store": load_user_store,
            "save_user_store": save_user_store,
            "find_user": find_user,
            "current_user": current_user,
            "current_user_record": current_user_record,
            "current_user_role": current_user_role,
            "serialize_user": serialize_user,
            "normalize_public_role": normalize_public_role,
            "validate_password_strength": validate_password_strength,
            "require_auth": require_auth,
        }
    )
)

app.register_blueprint(
    create_admin_blueprint(
        {
            "jsonify": jsonify,
            "request": request,
            "pd": pd,
            "UTC": UTC,
            "datetime": datetime,
            "json_success": json_success,
            "json_error": json_error,
            "load_user_store": load_user_store,
            "save_user_store": save_user_store,
            "current_user": current_user,
            "serialize_user": serialize_user,
            "normalize_public_role": normalize_public_role,
            "require_auth": require_auth,
            "require_roles": require_roles,
            "MODEL_METRICS_PATH": MODEL_METRICS_PATH,
            "DASHBOARD_ADMIN_EMAIL": DASHBOARD_ADMIN_EMAIL,
        }
    )
)

app.register_blueprint(
    create_dashboard_blueprint(
        {
            "jsonify": jsonify,
            "request": request,
            "pd": pd,
            "json_error": json_error,
            "require_auth": require_auth,
            "require_roles": require_roles,
            "prediction_frame": dashboard_data.prediction_frame,
            "calculate_brand_score": calculate_brand_score,
            "generate_visualizations": generate_visualizations,
            "dashboard_brand_payload": dashboard_data.dashboard_brand_payload,
            "trend_brand_availability": dashboard_data.trend_brand_availability,
            "normalize_brand_key": dashboard_data.normalize_brand_key,
            "build_brand_insights": dashboard_data.build_brand_insights,
            "find_brand_row": dashboard_data.find_brand_row,
            "similar_brand_rows": dashboard_data.similar_brand_rows,
            "risk_profile": dashboard_data.risk_profile,
            "trend_counts_frame": dashboard_data.trend_counts_frame,
            "dashboard_keywords_payload": dashboard_data.dashboard_keywords_payload,
            "dashboard_keyword_groups_payload": dashboard_data.dashboard_keyword_groups_payload,
            "recent_activity_reviews": dashboard_data.recent_activity_reviews,
            "review_samples": dashboard_data.review_samples,
            "random_brand_review": dashboard_data.random_brand_review,
            "dashboard_data": dashboard_data,
            "BRAND_REPUTATION_BY_BRAND_PATH": BRAND_REPUTATION_BY_BRAND_PATH,
            "latest_realtime_reviews": latest_realtime_reviews,
            "realtime_review_summary": realtime_review_summary,
        }
    )
)

app.register_blueprint(
    create_core_blueprint(
        {
            "jsonify": jsonify,
            "render_template": render_template,
            "request": request,
            "send_file": send_file,
            "pd": pd,
            "API_DOCS": API_DOCS,
            "MODEL_PATH": MODEL_PATH,
            "VECTORIZER_PATH": VECTORIZER_PATH,
            "PREDICTIONS_PATH": PREDICTIONS_PATH,
            "MODEL_REPORT_PATH": MODEL_REPORT_PATH,
            "REALTIME_REVIEWS_PATH": REALTIME_REVIEWS_PATH,
            "USER_STORE_PATH": USER_STORE_PATH,
            "LOGIN_ILLUSTRATION_PATH": LOGIN_ILLUSTRATION_PATH,
            "mongo_enabled": mongo_enabled,
            "json_success": json_success,
            "json_error": json_error,
            "require_auth": require_auth,
            "require_roles": require_roles,
            "preprocess_reviews": preprocess_reviews,
            "build_feature_dataset": build_feature_dataset,
            "train_models": train_models,
            "parse_predict_payload": parse_predict_payload,
            "predict_single_review": predict_single_review,
            "predict_batch_reviews": predict_batch_reviews,
            "load_model_artifacts": load_model_artifacts,
            "predict_dataset": predict_dataset,
            "calculate_brand_score": calculate_brand_score,
            "ingest_realtime_reviews": ingest_realtime_reviews,
            "realtime_review_summary": realtime_review_summary,
            "list_connectors": list_connectors,
            "poll_connector": poll_connector,
            "scheduler_status": scheduler_status,
            "update_scheduler_config": update_scheduler_config,
            "start_background_services": lambda debug_enabled: start_background_services(debug_enabled),
        }
    )
)


def should_start_scheduler(debug_enabled: bool) -> bool:
    if not debug_enabled:
        return True
    return os.getenv("WERKZEUG_RUN_MAIN") == "true"


def start_background_services(debug_enabled: bool) -> None:
    if should_start_scheduler(debug_enabled):
        ensure_scheduler_started()


if __name__ == "__main__":
    server_settings = resolve_runtime_server_settings()
    debug_mode = bool(server_settings["debug"])
    start_background_services(debug_mode)
    app.run(
        host=str(server_settings["host"]),
        port=int(server_settings["port"]),
        debug=debug_mode,
    )

