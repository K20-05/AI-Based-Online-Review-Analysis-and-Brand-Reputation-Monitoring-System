from pathlib import Path
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
MODEL_PATH = DATASET_DIR / "sentiment_model.pkl"
VECTORIZER_PATH = DATASET_DIR / "tfidf_vectorizer.pkl"
PREDICTIONS_PATH = DATASET_DIR / "final_predictions.csv"
UI_PATH = BASE_DIR / "ui" / "index.html"


class ReviewInput(BaseModel):
    review_text: str = Field(..., min_length=1)
    rating: Optional[float] = Field(default=None, ge=1.0, le=5.0)
    review_date: Optional[str] = None
    platform: Optional[str] = None
    review_id: Optional[Union[int, str]] = None


class BatchPredictRequest(BaseModel):
    reviews: List[ReviewInput] = Field(..., min_length=1)
    save_to_dataset: bool = False


app = FastAPI(
    title="Brand Review Analysis API",
    version="1.3.0",
    description="Backend interface for sentiment prediction and brand reputation scoring.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def load_artifacts():
    if not MODEL_PATH.exists() or not VECTORIZER_PATH.exists():
        missing = []
        if not MODEL_PATH.exists():
            missing.append(str(MODEL_PATH))
        if not VECTORIZER_PATH.exists():
            missing.append(str(VECTORIZER_PATH))
        raise FileNotFoundError(
            "Missing model artifacts. Train model first. Missing: " + ", ".join(missing)
        )

    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)
    return model, vectorizer


def clean_text(text: Any) -> str:
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def rating_to_sentiment(rating: Optional[float]) -> Optional[str]:
    if rating is None:
        return None
    if rating <= 2:
        return "Negative"
    if rating == 3:
        return "Neutral"
    if rating >= 4:
        return "Positive"
    return None


def rating_prior(rating: Optional[float]) -> Optional[Dict[str, float]]:
    if rating is None:
        return None
    if rating <= 2:
        return {"Negative": 0.80, "Neutral": 0.15, "Positive": 0.05}
    if rating == 3:
        return {"Negative": 0.10, "Neutral": 0.80, "Positive": 0.10}
    return {"Negative": 0.05, "Neutral": 0.15, "Positive": 0.80}


def blend_probabilities(
    class_probabilities: Dict[str, float], rating: Optional[float], text_weight: float = 0.6
) -> Dict[str, float]:
    prior = rating_prior(rating)
    if prior is None:
        return class_probabilities

    rating_weight = 1.0 - text_weight
    blended = {}
    for label in ["Negative", "Neutral", "Positive"]:
        blended[label] = round(
            (text_weight * class_probabilities.get(label, 0.0))
            + (rating_weight * prior.get(label, 0.0)),
            4,
        )

    total = sum(blended.values())
    if total > 0:
        blended = {k: round(v / total, 4) for k, v in blended.items()}

    return blended


def clean_platform(value: Optional[str]) -> str:
    if value is None:
        return "Unknown"
    text = str(value).lower()
    if "amazon" in text:
        return "Amazon"
    if "flipkart" in text:
        return "Flipkart"
    if "myntra" in text:
        return "Myntra"
    return "Other"


def compute_brand_metrics(predicted_sentiments: List[str]) -> Dict[str, Any]:
    total = len(predicted_sentiments)
    if total == 0:
        return {
            "total_reviews": 0,
            "counts": {"Positive": 0, "Neutral": 0, "Negative": 0},
            "percentages": {"Positive": 0.0, "Neutral": 0.0, "Negative": 0.0},
            "brand_reputation_score": 0.0,
        }

    positive = sum(1 for s in predicted_sentiments if s == "Positive")
    neutral = sum(1 for s in predicted_sentiments if s == "Neutral")
    negative = sum(1 for s in predicted_sentiments if s == "Negative")

    return {
        "total_reviews": total,
        "counts": {"Positive": positive, "Neutral": neutral, "Negative": negative},
        "percentages": {
            "Positive": round((positive / total) * 100, 2),
            "Neutral": round((neutral / total) * 100, 2),
            "Negative": round((negative / total) * 100, 2),
        },
        "brand_reputation_score": round(((positive - negative) / total) * 100, 2),
    }


def build_prediction_rows(reviews: List[ReviewInput]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for review in reviews:
        rows.append(
            {
                "review_id": review.review_id,
                "rating": review.rating,
                "review_date": review.review_date,
                "platform": clean_platform(review.platform),
                "review_text": review.review_text,
                "cleaned_review": clean_text(review.review_text),
                "sentiment": rating_to_sentiment(review.rating),
            }
        )
    return rows


@app.get("/")
def ui_home():
    if UI_PATH.exists():
        return FileResponse(UI_PATH)
    return {"message": "Brand Review Analysis API is running."}


@app.get("/api")
def api_info():
    return {
        "message": "Brand Review Analysis API is running.",
        "endpoints": ["/health", "/predict", "/predict/batch", "/brand-score", "/docs"],
    }


@app.get("/health")
def health():
    return {
        "status": "ok" if MODEL_PATH.exists() and VECTORIZER_PATH.exists() else "degraded",
        "model_exists": MODEL_PATH.exists(),
        "vectorizer_exists": VECTORIZER_PATH.exists(),
    }


@app.post("/predict")
def predict(review: ReviewInput):
    try:
        model, vectorizer = load_artifacts()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    cleaned = clean_text(review.review_text)
    features = vectorizer.transform([cleaned])
    base_pred = model.predict(features)[0]

    if not hasattr(model, "predict_proba"):
        class_probs = {base_pred: 1.0}
    else:
        probs = model.predict_proba(features)[0]
        class_probs = {cls: round(float(probs[i]), 4) for i, cls in enumerate(model.classes_)}

    blended_probs = blend_probabilities(class_probs, review.rating, text_weight=0.6)
    final_pred = max(blended_probs, key=blended_probs.get)

    expected = rating_to_sentiment(review.rating)

    return {
        "review_text": review.review_text,
        "cleaned_review": cleaned,
        "predicted_sentiment": base_pred,
        "prediction_confidence": class_probs.get(base_pred),
        "class_probabilities": class_probs,
        "final_sentiment": final_pred,
        "final_class_probabilities": blended_probs,
        "expected_sentiment_from_rating": expected,
        "is_mismatch_with_rating": (expected is not None and final_pred != expected),
        "platform": clean_platform(review.platform),
    }


@app.post("/predict/batch")
def predict_batch(payload: BatchPredictRequest):
    try:
        model, vectorizer = load_artifacts()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    rows = build_prediction_rows(payload.reviews)
    df = pd.DataFrame(rows)

    features = vectorizer.transform(df["cleaned_review"])
    base_preds = model.predict(features)
    df["predicted_sentiment"] = base_preds

    probs = model.predict_proba(features)
    class_labels = list(model.classes_)

    prob_maps = []
    final_prob_maps = []
    final_preds = []
    confidences = []

    for i, row in df.iterrows():
        base_map = {cls: round(float(probs[i][j]), 4) for j, cls in enumerate(class_labels)}
        prob_maps.append(base_map)
        confidences.append(base_map.get(row["predicted_sentiment"]))

        merged = blend_probabilities(base_map, row["rating"], text_weight=0.6)
        final_prob_maps.append(merged)
        final_preds.append(max(merged, key=merged.get))

    df["prediction_confidence"] = confidences
    df["class_probabilities"] = prob_maps
    df["final_class_probabilities"] = final_prob_maps
    df["final_sentiment"] = final_preds
    df["is_mismatch_with_rating"] = df.apply(
        lambda row: bool(row["sentiment"] and row["final_sentiment"] != row["sentiment"]), axis=1
    )

    if payload.save_to_dataset:
        output_columns = [
            "review_id",
            "rating",
            "review_date",
            "platform",
            "cleaned_review",
            "sentiment",
            "predicted_sentiment",
            "final_sentiment",
            "prediction_confidence",
            "is_mismatch_with_rating",
        ]
        df[output_columns].to_csv(PREDICTIONS_PATH, index=False)

    metrics = compute_brand_metrics(df["final_sentiment"].tolist())

    return {
        "metrics": metrics,
        "saved_to": str(PREDICTIONS_PATH) if payload.save_to_dataset else None,
        "predictions": df[
            [
                "review_id",
                "rating",
                "review_date",
                "platform",
                "cleaned_review",
                "sentiment",
                "predicted_sentiment",
                "final_sentiment",
                "prediction_confidence",
                "class_probabilities",
                "final_class_probabilities",
                "is_mismatch_with_rating",
            ]
        ].fillna("").to_dict(orient="records"),
    }


@app.get("/brand-score")
def brand_score_from_saved_predictions():
    if not PREDICTIONS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail=f"{PREDICTIONS_PATH} not found. Run /predict/batch with save_to_dataset=true first.",
        )

    df = pd.read_csv(PREDICTIONS_PATH)
    sentiment_col = "final_sentiment" if "final_sentiment" in df.columns else "predicted_sentiment"
    if sentiment_col not in df.columns:
        raise HTTPException(status_code=400, detail="No sentiment column found in final_predictions.csv")

    return compute_brand_metrics(df[sentiment_col].astype(str).tolist())
