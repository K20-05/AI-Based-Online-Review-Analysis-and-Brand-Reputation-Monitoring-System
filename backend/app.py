from __future__ import annotations

from collections import Counter
from datetime import datetime, UTC
from functools import wraps
import json
from pathlib import Path
import re
import sys

from flask import Flask, jsonify, request, send_file, send_from_directory, session
from flask_cors import CORS
import joblib
import pandas as pd
from werkzeug.security import check_password_hash, generate_password_hash

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.brand_score import calculate_brand_score
from backend.config import (
    BRAND_REPUTATION_BY_BRAND_PATH,
    BRAND_SCORE_PATH,
    DASHBOARD_ADMIN_EMAIL,
    DASHBOARD_ADMIN_PASSWORD,
    FRONTEND_DIR,
    MODEL_PATH,
    MODEL_REPORT_PATH,
    PREDICTIONS_PATH,
    SECRET_KEY,
    USER_STORE_PATH,
    VECTORIZER_PATH,
)
from backend.feature_extraction import build_feature_dataset
from backend.model_training import train_models
from backend.predict import predict_dataset
from backend.preprocessing import clean_text, preprocess_reviews
from backend.visualization import generate_visualizations

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
app.config["SECRET_KEY"] = SECRET_KEY
CORS(app, supports_credentials=True)
LOGIN_ILLUSTRATION_PATH = Path(r"C:\Users\ADMIN\OneDrive\Pictures\1.png!sw800")

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
                "summary": "Predict sentiment for a single review.",
                "auth_required": True,
                "request_body": {
                    "review_text": "Delivery was quick and smooth.",
                    "platform": "Amazon",
                    "brand": "Amazon",
                    "rating": 5,
                },
                "response": {
                    "review_text": "Delivery was quick and smooth.",
                    "cleaned_review": "delivery quick smooth",
                    "rating": 5,
                    "platform": "Amazon",
                    "brand": "Amazon",
                    "predicted_sentiment": "Positive",
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
                "summary": "Predict sentiment for the cleaned review dataset and refresh brand score outputs.",
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
            {"method": "GET", "path": "/api/dashboard/summary", "summary": "Get overall dashboard summary and brand scores.", "auth_required": True},
            {"method": "GET", "path": "/api/dashboard/trends", "summary": "Get monthly sentiment trend data.", "auth_required": True},
            {"method": "GET", "path": "/api/dashboard/keywords", "summary": "Get top processed keywords.", "auth_required": True},
            {"method": "GET", "path": "/api/dashboard/platforms", "summary": "Get platform sentiment breakdown.", "auth_required": True},
            {"method": "GET", "path": "/api/dashboard/brands", "summary": "Get brand-level reputation rows.", "auth_required": True},
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
                "summary": "Reset a dashboard user's password.",
                "request_body": {"email": "aarav@brandpulse.ai", "new_password": "newsecure123"},
                "response": {"success": True, "message": "Password updated", "user": "aarav@brandpulse.ai"},
                "error_responses": [
                    {"status": 400, "body": {"success": False, "error": "email and new_password are required"}},
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

def load_artifacts():
    if not MODEL_PATH.exists() or not VECTORIZER_PATH.exists():
        raise FileNotFoundError("Model artifacts are missing. Run training first.")
    return joblib.load(MODEL_PATH), joblib.load(VECTORIZER_PATH)


def prediction_frame() -> pd.DataFrame:
    if not PREDICTIONS_PATH.exists():
        raise FileNotFoundError("Prediction dataset not found. Run prediction first.")
    return pd.read_csv(
        PREDICTIONS_PATH,
        dtype={"review_id": "string", "platform": "string", "brand": "string"},
        low_memory=False,
    )


def json_success(message: str, **data):
    payload = {"success": True, "message": message}
    payload.update(data)
    return jsonify(payload)


def json_error(message: str, status_code: int = 400):
    return jsonify({"success": False, "error": message}), status_code


def dashboard_brand_payload() -> dict:
    payload = calculate_brand_score()
    if BRAND_SCORE_PATH.exists():
        payload = json.loads(BRAND_SCORE_PATH.read_text(encoding="utf-8"))
    return payload


def brand_rows() -> list[dict]:
    rows = dashboard_brand_payload().get("brand_scores", [])
    normalized = []
    for row in rows:
        normalized.append(
            {
                "brand": str(row.get("brand", "Unknown")),
                "total_reviews": int(float(row.get("total_reviews", 0) or 0)),
                "positive_pct": float(row.get("positive_pct", 0) or 0),
                "neutral_pct": float(row.get("neutral_pct", 0) or 0),
                "negative_pct": float(row.get("negative_pct", 0) or 0),
                "brand_reputation_score": float(row.get("brand_reputation_score", 0) or 0),
            }
        )
    return normalized


def find_brand_row(brand_name: str) -> dict:
    lookup = brand_name.strip().lower()
    for row in brand_rows():
        if row["brand"].strip().lower() == lookup:
            return row
    raise ValueError(f"Brand '{brand_name}' was not found")


def risk_profile(score: float, negative_pct: float) -> dict:
    if score >= 45 and negative_pct < 25:
        return {"level": "low", "label": "Low Risk"}
    if score < 10 or negative_pct >= 40:
        return {"level": "high", "label": "High Risk"}
    return {"level": "medium", "label": "Medium Risk"}


def build_brand_insights(row: dict) -> dict:
    score = float(row["brand_reputation_score"])
    negative_pct = float(row["negative_pct"])
    positive_pct = float(row["positive_pct"])
    total_reviews = int(row["total_reviews"])
    risk = risk_profile(score, negative_pct)

    pros = []
    cons = []

    if positive_pct >= 65:
        pros.append("Strong positive sentiment share")
    if score >= 40:
        pros.append("Healthy brand reputation score")
    if negative_pct <= 20:
        pros.append("Complaint pressure is relatively low")
    if total_reviews >= 5000:
        pros.append("Large review volume supports confidence")

    if negative_pct >= 35:
        cons.append("Negative sentiment is elevated")
    if score < 15:
        cons.append("Brand reputation score is weak")
    if positive_pct < 45:
        cons.append("Positive momentum is limited")
    if total_reviews < 1000:
        cons.append("Review volume is comparatively thin")

    if not pros:
        pros = ["Overall sentiment remains usable for decision-making", "Brand has a measurable baseline to improve from"]
    if not cons:
        cons = ["No major structural risk detected", "Continue monitoring for drift and service issues"]

    if score >= 45:
        why = (
            f"{row['brand']} is performing well because positive sentiment materially outweighs negative reviews, "
            "which keeps brand trust and reputation stable."
        )
        recommendation = (
            "Scale the strongest positive themes in campaigns, preserve service quality, and use testimonials to defend the lead."
        )
    elif score < 10:
        why = (
            f"{row['brand']} is high risk because negative sentiment is too close to or above the positive share, "
            "which is pulling the reputation score down."
        )
        recommendation = (
            "Prioritize complaint clusters first, fix product or service friction, and hold back aggressive promotion until negative drivers fall."
        )
    else:
        why = (
            f"{row['brand']} is in a mixed zone. Positive reviews still support the brand, "
            "but negative pressure is large enough to weaken trust."
        )
        recommendation = (
            "Address the most common complaints, strengthen support response quality, and amplify the top positive review themes."
        )

    return {
        "brand": row["brand"],
        "metrics": row,
        "risk": risk,
        "why": why,
        "pros": pros,
        "cons": cons,
        "key_insights": [
            f"Reputation score: {score:.1f}",
            f"Positive sentiment: {positive_pct:.1f}%",
            f"Negative sentiment: {negative_pct:.1f}%",
            f"Review volume: {total_reviews:,}",
        ],
        "recommendation": recommendation,
    }


def similar_brand_rows(base_row: dict, limit: int = 3) -> list[dict]:
    scored_rows = []
    for row in brand_rows():
        if row["brand"] == base_row["brand"]:
            continue
        distance = (
            abs(row["brand_reputation_score"] - base_row["brand_reputation_score"])
            + abs(row["positive_pct"] - base_row["positive_pct"]) * 0.4
            + abs(row["negative_pct"] - base_row["negative_pct"]) * 0.5
        )
        scored_rows.append(
            {
                "brand": row["brand"],
                "metrics": row,
                "risk": risk_profile(row["brand_reputation_score"], row["negative_pct"]),
                "distance": round(distance, 2),
            }
        )
    return sorted(scored_rows, key=lambda item: item["distance"])[:limit]


def current_user() -> str | None:
    return session.get("user_email")


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
        if not current_user():
            return json_error("Authentication required", 401)
        return view_func(*args, **kwargs)

    return wrapped


def parse_predict_payload(payload: dict) -> dict:
    review_text = str(payload.get("review_text", "")).strip()
    if not review_text:
        raise ValueError("review_text is required")

    platform = str(payload.get("platform", "Manual Input")).strip() or "Manual Input"
    brand = str(payload.get("brand", platform)).strip() or platform
    rating = payload.get("rating")
    return {
        "review_text": review_text,
        "platform": platform,
        "brand": brand,
        "rating": rating,
    }


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
        }
    )


@app.get("/api/assets/login-illustration")
def login_illustration():
    if not LOGIN_ILLUSTRATION_PATH.exists():
        raise FileNotFoundError("Login illustration not found.")
    return send_file(LOGIN_ILLUSTRATION_PATH)


@app.get("/api/auth/session")
def auth_session():
    user_email = current_user()
    return jsonify({"authenticated": bool(user_email), "user": user_email})


@app.post("/api/auth/register")
def auth_register():
    payload = request.get_json(force=True, silent=False) or {}
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    if not name or not email or not password:
        return json_error("name, email and password are required")
    if "@" not in email:
        return json_error("Enter a valid email address")
    password_error = validate_password_strength(password)
    if password_error:
        return json_error(password_error)
    if find_user(email):
        return json_error("An account with this email already exists", 409)

    users = load_user_store()
    users.append(
        {
            "name": name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "role": "user",
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    save_user_store(users)
    return json_success("Account created", user=email)


@app.post("/api/auth/login")
def auth_login():
    payload = request.get_json(force=True, silent=False) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    if not email or not password:
        return json_error("email and password are required")
    user = find_user(email)
    if not user or not check_password_hash(str(user.get("password_hash", "")), password):
        return json_error("Invalid email or password", 401)

    session["user_email"] = str(user.get("email", email))
    return json_success("Login successful", user=str(user.get("email", email)))


@app.post("/api/auth/reset-password")
def auth_reset_password():
    payload = request.get_json(force=True, silent=False) or {}
    email = str(payload.get("email", "")).strip().lower()
    new_password = str(payload.get("new_password", ""))

    if not email or not new_password:
        return json_error("email and new_password are required")
    password_error = validate_password_strength(new_password)
    if password_error:
        return json_error(password_error)

    users = load_user_store()
    updated = False
    for user in users:
        if str(user.get("email", "")).strip().lower() == email:
            user["password_hash"] = generate_password_hash(new_password)
            user["updated_at"] = datetime.now(UTC).isoformat()
            updated = True
            break

    if not updated:
        return json_error("No account found for this email", 404)

    save_user_store(users)
    return json_success("Password updated", user=email)


@app.post("/api/auth/logout")
def auth_logout():
    session.clear()
    return json_success("Logout successful")


@app.get("/api/docs")
def api_docs():
    return jsonify(API_DOCS)


@app.get("/api/openapi.json")
def api_openapi():
    return jsonify(API_DOCS)


@app.post("/api/preprocess")
@require_auth
def preprocess_endpoint():
    df = preprocess_reviews()
    return json_success("Preprocessing completed", rows=int(len(df)))


@app.post("/api/features")
@require_auth
def feature_extraction_endpoint():
    df = build_feature_dataset()
    return json_success("Feature extraction completed", rows=int(len(df)))


@app.post("/api/train")
@require_auth
def train_endpoint():
    metrics = train_models()
    return json_success("Training completed", models=metrics.to_dict(orient="records"))


@app.post("/api/predict")
@require_auth
def predict_single():
    payload = request.get_json(force=True, silent=False) or {}
    request_data = parse_predict_payload(payload)

    model, vectorizer = load_artifacts()
    cleaned_review = clean_text(request_data["review_text"])
    features = vectorizer.transform([cleaned_review])
    predicted_sentiment = model.predict(features)[0]
    class_probabilities = {}
    prediction_confidence = None
    if hasattr(model, "predict_proba") and hasattr(model, "classes_"):
        probabilities = model.predict_proba(features)[0]
        class_probabilities = {
            str(label): float(probability)
            for label, probability in zip(model.classes_, probabilities)
        }
        prediction_confidence = float(class_probabilities.get(str(predicted_sentiment), 0.0))

    return jsonify(
        {
            "success": True,
            "review_text": request_data["review_text"],
            "cleaned_review": cleaned_review,
            "rating": request_data["rating"],
            "platform": request_data["platform"],
            "brand": request_data["brand"],
            "predicted_sentiment": predicted_sentiment,
            "class_probabilities": class_probabilities,
            "prediction_confidence": prediction_confidence,
        }
    )


@app.post("/api/predict/batch")
@require_auth
def predict_batch():
    df = predict_dataset()
    score = calculate_brand_score()
    return json_success("Batch prediction completed", rows=int(len(df)), brand_score=score)


@app.post("/api/brand-score")
@require_auth
def brand_score_endpoint():
    payload = calculate_brand_score()
    return json_success("Brand scoring completed", brand_score=payload)


@app.get("/api/dashboard/summary")
@require_auth
def dashboard_summary():
    payload = calculate_brand_score()
    if BRAND_SCORE_PATH.exists():
        payload = json.loads(BRAND_SCORE_PATH.read_text(encoding="utf-8"))
    return jsonify(payload)


@app.get("/api/dashboard/brands")
@require_auth
def dashboard_brands():
    if BRAND_REPUTATION_BY_BRAND_PATH.exists():
        df = pd.read_csv(BRAND_REPUTATION_BY_BRAND_PATH, low_memory=False)
        return jsonify({"brands": df.to_dict(orient="records")})
    payload = calculate_brand_score()
    return jsonify({"brands": payload.get("brand_scores", [])})


@app.get("/api/dashboard/insights")
@require_auth
def dashboard_insights():
    brand = str(request.args.get("brand", "")).strip()
    if not brand:
        return json_error("brand query parameter is required")
    return jsonify(build_brand_insights(find_brand_row(brand)))


@app.get("/api/dashboard/similar")
@require_auth
def dashboard_similar():
    brand = str(request.args.get("brand", "")).strip()
    if not brand:
        return json_error("brand query parameter is required")
    limit = max(1, min(int(request.args.get("limit", 3) or 3), 10))
    row = find_brand_row(brand)
    return jsonify({"brand": row["brand"], "similar": similar_brand_rows(row, limit)})


@app.get("/api/dashboard/compare")
@require_auth
def dashboard_compare():
    brand_a = str(request.args.get("brand_a", "")).strip()
    brand_b = str(request.args.get("brand_b", "")).strip()
    if not brand_a or not brand_b:
        return json_error("brand_a and brand_b query parameters are required")

    row_a = find_brand_row(brand_a)
    row_b = find_brand_row(brand_b)
    leader = row_a if row_a["brand_reputation_score"] >= row_b["brand_reputation_score"] else row_b
    lagger = row_b if leader is row_a else row_a
    summary = (
        f"{leader['brand']} leads on reputation score, while {lagger['brand']} needs more work on negative sentiment control and trust recovery."
    )

    return jsonify(
        {
            "brand_a": row_a,
            "brand_b": row_b,
            "risk_a": risk_profile(row_a["brand_reputation_score"], row_a["negative_pct"]),
            "risk_b": risk_profile(row_b["brand_reputation_score"], row_b["negative_pct"]),
            "summary": summary,
        }
    )


@app.get("/api/dashboard/trends")
@require_auth
def dashboard_trends():
    df = prediction_frame()
    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
    df = df.dropna(subset=["review_date"])
    if df.empty:
        return jsonify({"trends": []})

    df["period"] = df["review_date"].dt.to_period("M").astype(str)
    grouped = (
        df.groupby(["period", "predicted_sentiment"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )
    trends = []
    for period, row in grouped.iterrows():
        trends.append(
            {
                "period": period,
                "Positive": int(row.get("Positive", 0)),
                "Neutral": int(row.get("Neutral", 0)),
                "Negative": int(row.get("Negative", 0)),
            }
        )
    return jsonify({"trends": trends})


@app.get("/api/dashboard/keywords")
@require_auth
def dashboard_keywords():
    df = prediction_frame()
    tokens = []
    for text in df.get("cleaned_review", pd.Series(dtype=str)).fillna("").astype(str):
        tokens.extend(re.findall(r"\b[a-z]{3,}\b", text.lower()))
    keywords = [{"word": word, "count": count} for word, count in Counter(tokens).most_common(12)]
    return jsonify({"keywords": keywords})


@app.get("/api/dashboard/platforms")
@require_auth
def dashboard_platforms():
    df = prediction_frame()
    platform_counts = (
        df.groupby(["platform", "predicted_sentiment"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
        .to_dict(orient="records")
    )
    return jsonify({"platforms": platform_counts})


@app.post("/api/dashboard/refresh")
@require_auth
def dashboard_refresh():
    df = prediction_frame()
    generate_visualizations(df)
    score = calculate_brand_score()
    return jsonify({"message": "Dashboard refreshed", "brand_score": score})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
