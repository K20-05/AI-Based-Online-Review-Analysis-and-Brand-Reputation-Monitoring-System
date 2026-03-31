from __future__ import annotations

from datetime import datetime, UTC
from functools import wraps
import json
import os
from pathlib import Path
import re
import sys

from flask import Flask, jsonify, request, send_file, send_from_directory, session
from flask_cors import CORS
import pandas as pd
from werkzeug.security import check_password_hash, generate_password_hash

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.brand_score import calculate_brand_score
from backend.config import (
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
    SECRET_KEY,
    USER_STORE_PATH,
    VECTORIZER_PATH,
)
from backend.database import mongo_enabled
from backend import dashboard_data
from backend.admin_routes import create_admin_blueprint
from backend.auth_routes import create_auth_blueprint
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

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
app.config["SECRET_KEY"] = SECRET_KEY
CORS(app, supports_credentials=True)

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
                "summary": "Create a dashboard user account and start a session.",
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


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    return jsonify({"success": False, "error": str(error)}), 500


def json_success(message: str, **data):
    payload = {"success": True, "message": message}
    payload.update(data)
    return jsonify(payload)


def json_error(message: str, status_code: int = 400):
    return jsonify({"success": False, "error": message}), status_code


def session_user_email() -> str | None:
    email = str(session.get("user_email", "")).strip().lower()
    return email or None


def current_user() -> str | None:
    user = current_user_record()
    if not user:
        return None
    return str(user.get("email", "")).strip().lower() or None


def current_user_record() -> dict | None:
    user_email = session_user_email()
    if not user_email:
        return None
    user = find_user(user_email)
    if user:
        return user
    session.pop("user_email", None)
    return None


def current_user_role() -> str:
    user = current_user_record()
    if not user:
        return ""
    normalized = str(user.get("role", "")).strip().lower()
    if normalized == "user":
        return "analyst"
    return normalized


def load_user_store() -> list[dict]:
    users = []
    if USER_STORE_PATH.exists():
        users = json.loads(USER_STORE_PATH.read_text(encoding="utf-8"))

    admin_email = DASHBOARD_ADMIN_EMAIL.strip().lower()
    if admin_email and not any(str(user.get("email", "")).strip().lower() == admin_email for user in users):
        users.append(
            {
                "name": "Administrator",
                "email": admin_email,
                "password_hash": generate_password_hash(DASHBOARD_ADMIN_PASSWORD),
                "role": "admin",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        save_user_store(users)
    return users


def save_user_store(users: list[dict]) -> None:
    USER_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_STORE_PATH.write_text(json.dumps(users, indent=2), encoding="utf-8")


def find_user(email: str) -> dict | None:
    email = email.strip().lower()
    for user in load_user_store():
        if str(user.get("email", "")).strip().lower() == email:
            return user
    return None


def serialize_user(user: dict | None) -> dict | None:
    if not user:
        return None
    normalized_role = str(user.get("role", "")).strip().lower() or "analyst"
    if normalized_role == "user":
        normalized_role = "analyst"
    return {
        "name": str(user.get("name", "")).strip() or str(user.get("email", "")).strip(),
        "email": str(user.get("email", "")).strip().lower(),
        "role": normalized_role,
    }


def normalize_public_role(role: str | None) -> str:
    normalized = str(role or "").strip().lower()
    if normalized == "marketing_staff":
        return "marketing_staff"
    if normalized in {"admin", "user"}:
        return "analyst"
    return "analyst"


def validate_password_strength(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return "Password must include at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must include at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must include at least one number"
    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password must include at least one special character"
    return None


def require_auth(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user_record():
            return json_error("Authentication required", 401)
        return view_func(*args, **kwargs)

    return wrapped


def require_roles(*roles: str):
    allowed_roles = {str(role).strip().lower() for role in roles if str(role).strip()}

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user_record():
                return json_error("Authentication required", 401)
            active_role = current_user_role()
            if active_role == "admin":
                return view_func(*args, **kwargs)
            if active_role not in allowed_roles:
                return json_error("Access denied for this role", 403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


app.register_blueprint(
    create_auth_blueprint(
        {
            "jsonify": jsonify,
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
            "review_samples": dashboard_data.review_samples,
            "random_brand_review": dashboard_data.random_brand_review,
            "dashboard_data": dashboard_data,
            "BRAND_REPUTATION_BY_BRAND_PATH": BRAND_REPUTATION_BY_BRAND_PATH,
            "latest_realtime_reviews": latest_realtime_reviews,
            "realtime_review_summary": realtime_review_summary,
        }
    )
)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "model_exists": MODEL_PATH.exists(),
            "vectorizer_exists": VECTORIZER_PATH.exists(),
            "predictions_exist": PREDICTIONS_PATH.exists(),
            "report_exists": MODEL_REPORT_PATH.exists(),
            "realtime_reviews_exist": REALTIME_REVIEWS_PATH.exists(),
            "user_store_exists": USER_STORE_PATH.exists(),
            "login_illustration_exists": LOGIN_ILLUSTRATION_PATH.exists(),
            "mongo_configured": mongo_enabled(),
        }
    )


@app.get("/api/assets/login-illustration")
def login_illustration():
    if not LOGIN_ILLUSTRATION_PATH.exists():
        raise FileNotFoundError("Login illustration not found.")
    return send_file(LOGIN_ILLUSTRATION_PATH)


@app.get("/api/docs")
def api_docs():
    return jsonify(API_DOCS)


@app.get("/api/openapi.json")
def api_openapi():
    return jsonify(API_DOCS)


@app.post("/api/preprocess")
@require_auth
@require_roles("admin", "analyst")
def preprocess_endpoint():
    df = preprocess_reviews()
    return json_success("Preprocessing completed", rows=int(len(df)))


@app.post("/api/features")
@require_auth
@require_roles("admin", "analyst")
def feature_extraction_endpoint():
    df = build_feature_dataset()

    return json_success("Feature extraction completed", rows=int(len(df)))


@app.post("/api/train")
@require_auth
@require_roles("admin", "analyst")
def train_endpoint():
    metrics = train_models()
    return json_success("Training completed", models=metrics.to_dict(orient="records"))


@app.post("/api/predict")
@require_auth
@require_roles("admin", "analyst")
def predict_single():
    payload = request.get_json(force=True, silent=False) or {}
    request_data = parse_predict_payload(payload)
    response_payload = predict_single_review(request_data, load_model_artifacts)
    return jsonify({"success": True, **response_payload})


@app.post("/api/predict/batch")
@require_auth
@require_roles("admin", "analyst")
def predict_batch():
    payload = request.get_json(force=True, silent=False) or {}
    reviews = payload.get("reviews") or []
    save_to_dataset = bool(payload.get("save_to_dataset"))

    # Fast path: predict only submitted batch rows from UI text input.
    if isinstance(reviews, list) and reviews and not save_to_dataset:
        response_payload = predict_batch_reviews(reviews, load_model_artifacts)
        return jsonify({"success": True, **response_payload})

    # Full refresh path: expensive dataset-wide rebuild (used when save_to_dataset is enabled).
    df = predict_dataset()
    score = calculate_brand_score()
    return json_success("Batch prediction completed", rows=int(len(df)), brand_score=score)


@app.post("/api/brand-score")
@require_auth
@require_roles("admin", "analyst")
def brand_score_endpoint():
    payload = calculate_brand_score()
    return json_success("Brand scoring completed", brand_score=payload)


@app.post("/api/reviews/realtime")
@require_auth
@require_roles("admin", "analyst")
def realtime_reviews_ingest():
    payload = request.get_json(force=True, silent=False) or {}
    reviews = payload.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        single = payload if payload.get("review_text") else None
        reviews = [single] if single else []
    if not reviews:
        return json_error("Provide reviews as a non-empty list or a single review_text payload")

    df = ingest_realtime_reviews(reviews)
    return jsonify(
        {
            "success": True,
            "message": "Realtime reviews ingested",
            "rows": int(len(df)),
            "results": df.where(pd.notnull(df), None).to_dict(orient="records"),
            "summary": realtime_review_summary(),
        }
    )


@app.get("/api/connectors")
@require_auth
@require_roles("admin", "analyst")
def connectors_list_endpoint():
    return jsonify({"connectors": list_connectors()})


@app.post("/api/connectors/poll")
@require_auth
@require_roles("admin", "analyst")
def connectors_poll_endpoint():
    payload = request.get_json(force=True, silent=False) or {}
    connector_name = str(payload.get("connector", "")).strip()
    if not connector_name:
        return json_error("connector is required")

    limit = max(1, min(int(payload.get("limit", 20) or 20), 100))
    options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
    reset_cursor = bool(payload.get("reset_cursor"))

    fetched = poll_connector(connector_name, limit=limit, options=options, reset_cursor=reset_cursor)
    reviews = fetched.get("reviews", [])
    if not reviews:
        return jsonify({"success": True, "message": "Connector poll completed with no new reviews", **fetched})

    ingested_df = ingest_realtime_reviews(reviews)
    return jsonify(
        {
            "success": True,
            "message": "Connector poll completed",
            **fetched,
            "ingested_rows": int(len(ingested_df)),
            "summary": realtime_review_summary(),
        }
    )


@app.get("/api/connectors/scheduler")
@require_auth
@require_roles("admin", "analyst")
def connector_scheduler_status_endpoint():
    start_background_services(app.debug)
    return jsonify(scheduler_status())


@app.post("/api/connectors/scheduler")
@require_auth
@require_roles("admin", "analyst")
def connector_scheduler_update_endpoint():
    start_background_services(app.debug)
    payload = request.get_json(force=True, silent=False) or {}
    return jsonify(
        {
            "success": True,
            "message": "Connector scheduler updated",
            **update_scheduler_config(payload),
        }
    )


def should_start_scheduler(debug_enabled: bool) -> bool:
    if not debug_enabled:
        return True
    return os.getenv("WERKZEUG_RUN_MAIN") == "true"


def start_background_services(debug_enabled: bool) -> None:
    if should_start_scheduler(debug_enabled):
        ensure_scheduler_started()


if __name__ == "__main__":
    debug_mode = True
    start_background_services(debug_mode)
    app.run(host="127.0.0.1", port=5000, debug=debug_mode)
