from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sys

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import joblib
import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.brand_score import calculate_brand_score
from backend.config import (
    BRAND_SCORE_PATH,
    FRONTEND_DIR,
    MODEL_PATH,
    MODEL_REPORT_PATH,
    PREDICTIONS_PATH,
    VECTORIZER_PATH,
)
from backend.model_training import train_models
from backend.predict import predict_dataset
from backend.preprocessing import clean_text, preprocess_reviews
from backend.visualization import generate_visualizations

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app)


@app.errorhandler(FileNotFoundError)
def handle_missing_file(error):
    return jsonify({"error": str(error)}), 404


@app.errorhandler(ValueError)
def handle_value_error(error):
    return jsonify({"error": str(error)}), 400


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    return jsonify({"error": str(error)}), 500

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


@app.post("/api/preprocess")
def preprocess_endpoint():
    df = preprocess_reviews()
    return jsonify({"rows": int(len(df)), "message": "Preprocessing completed"})


@app.post("/api/train")
def train_endpoint():
    metrics = train_models()
    return jsonify({"message": "Training completed", "models": metrics.to_dict(orient="records")})


@app.post("/api/predict")
def predict_single():
    payload = request.get_json(force=True, silent=False) or {}
    review_text = payload.get("review_text", "")
    rating = payload.get("rating")
    platform = payload.get("platform", "Manual Input")
    brand = payload.get("brand", platform)

    if not review_text.strip():
        return jsonify({"error": "review_text is required"}), 400

    model, vectorizer = load_artifacts()
    cleaned_review = clean_text(review_text)
    predicted_sentiment = model.predict(vectorizer.transform([cleaned_review]))[0]

    return jsonify(
        {
            "review_text": review_text,
            "cleaned_review": cleaned_review,
            "rating": rating,
            "platform": platform,
            "brand": brand,
            "predicted_sentiment": predicted_sentiment,
        }
    )


@app.post("/api/predict/batch")
def predict_batch():
    df = predict_dataset()
    score = calculate_brand_score()
    return jsonify(
        {
            "message": "Batch prediction completed",
            "rows": int(len(df)),
            "brand_score": score,
        }
    )


@app.get("/api/dashboard/summary")
def dashboard_summary():
    payload = calculate_brand_score()
    if BRAND_SCORE_PATH.exists():
        payload = json.loads(BRAND_SCORE_PATH.read_text(encoding="utf-8"))
    return jsonify(payload)


@app.get("/api/dashboard/trends")
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
def dashboard_keywords():
    df = prediction_frame()
    tokens = []
    for text in df.get("cleaned_review", pd.Series(dtype=str)).fillna("").astype(str):
        tokens.extend(re.findall(r"\b[a-z]{3,}\b", text.lower()))
    keywords = [{"word": word, "count": count} for word, count in Counter(tokens).most_common(12)]
    return jsonify({"keywords": keywords})


@app.get("/api/dashboard/platforms")
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
def dashboard_refresh():
    df = prediction_frame()
    generate_visualizations(df)
    score = calculate_brand_score()
    return jsonify({"message": "Dashboard refreshed", "brand_score": score})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
