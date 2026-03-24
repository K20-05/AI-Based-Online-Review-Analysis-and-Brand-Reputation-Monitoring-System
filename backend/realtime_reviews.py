from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
import sys
import uuid

import pandas as pd
from pandas.errors import EmptyDataError

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import REALTIME_REVIEWS_PATH
from backend.database import append_realtime_reviews
from backend.model_artifacts import load_model_artifacts
from backend.multilingual import apply_multilingual_sentiment_guard, normalize_multilingual_text
from backend.predict import calibrate_prediction_confidence, predict_with_confidence_details
from backend.preprocessing import clean_text

REALTIME_COLUMNS = [
    "review_id",
    "review_text",
    "cleaned_review",
    "normalized_review",
    "platform",
    "brand",
    "rating",
    "source_language",
    "source_language_label",
    "language_confidence",
    "translation_applied",
    "multilingual_strategy",
    "predicted_sentiment",
    "prediction_confidence",
    "ingested_at",
    "review_date",
    "source_type",
]

def load_realtime_reviews() -> pd.DataFrame:
    if not REALTIME_REVIEWS_PATH.exists():
        return pd.DataFrame(columns=REALTIME_COLUMNS)
    try:
        df = pd.read_csv(REALTIME_REVIEWS_PATH, low_memory=False)
    except EmptyDataError:
        return pd.DataFrame(columns=REALTIME_COLUMNS)
    for column in REALTIME_COLUMNS:
        if column not in df.columns:
            df[column] = None
    return df[REALTIME_COLUMNS].copy()


def save_realtime_reviews(df: pd.DataFrame) -> None:
    REALTIME_REVIEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(REALTIME_REVIEWS_PATH, index=False)


def _prepare_realtime_row(item: dict, index: int) -> dict:
    review_text = str(item.get("review_text", "")).strip()
    if not review_text:
        raise ValueError("review_text is required")

    platform = str(item.get("platform", "Realtime Feed")).strip() or "Realtime Feed"
    brand = str(item.get("brand", platform)).strip() or platform
    rating = item.get("rating")
    review_date = str(item.get("review_date", "")).strip() or datetime.now(UTC).date().isoformat()
    source_type = str(item.get("source_type", "realtime")).strip() or "realtime"
    review_id = str(item.get("review_id", "")).strip() or f"rt-{uuid.uuid4().hex[:12]}-{index + 1}"

    multilingual_payload = normalize_multilingual_text(review_text)
    return {
        "review_id": review_id,
        "review_text": review_text,
        "cleaned_review": clean_text(review_text),
        "normalized_review": multilingual_payload["normalized_text"],
        "platform": platform,
        "brand": brand,
        "rating": rating,
        "source_language": multilingual_payload["detected_language"],
        "source_language_label": multilingual_payload["detected_language_label"],
        "language_confidence": multilingual_payload["language_confidence"],
        "translation_applied": multilingual_payload["translation_applied"],
        "multilingual_strategy": multilingual_payload["strategy"],
        "predicted_sentiment": None,
        "prediction_confidence": None,
        "ingested_at": datetime.now(UTC).isoformat(),
        "review_date": review_date,
        "source_type": source_type,
    }


def ingest_realtime_reviews(reviews: list[dict]) -> pd.DataFrame:
    if not reviews:
        raise ValueError("reviews must contain at least one item")

    model, vectorizer = load_model_artifacts()
    prepared = [_prepare_realtime_row(item, index) for index, item in enumerate(reviews)]

    features = vectorizer.transform([row["cleaned_review"] for row in prepared])
    prediction_details = predict_with_confidence_details(model, features)

    for index, row in enumerate(prepared):
        detail = prediction_details[index]
        sentiment = str(detail["predicted_sentiment"])
        probability_map = dict(detail["class_probabilities"])
        row["predicted_sentiment"] = sentiment
        sentiment, _ = apply_multilingual_sentiment_guard(
            row["normalized_review"],
            sentiment,
            probability_map,
            row.get("rating"),
        )
        row["predicted_sentiment"] = sentiment
        row["prediction_confidence"] = calibrate_prediction_confidence(
            detail["decision_confidence"],
            row["cleaned_review"],
            bool(row["translation_applied"]),
            row["language_confidence"],
            None,
            row["normalized_review"],
        )

    new_df = pd.DataFrame(prepared, columns=REALTIME_COLUMNS)
    history_df = load_realtime_reviews()
    merged = pd.concat([new_df, history_df], ignore_index=True)
    merged = merged.drop_duplicates(subset=["review_id"], keep="first")
    save_realtime_reviews(merged)
    append_realtime_reviews(new_df)
    return new_df


def latest_realtime_reviews(limit: int = 20, brand: str = "", platform: str = "") -> list[dict]:
    df = load_realtime_reviews()
    if df.empty:
        return []

    if brand:
        df = df[df["brand"].fillna("").astype(str).str.strip().str.lower() == brand.strip().lower()]
    if platform:
        df = df[df["platform"].fillna("").astype(str).str.strip().str.lower() == platform.strip().lower()]

    df["ingested_at"] = pd.to_datetime(df["ingested_at"], errors="coerce")
    df = df.sort_values(by="ingested_at", ascending=False, na_position="last").head(limit)
    result = df.copy()
    result["ingested_at"] = result["ingested_at"].astype("string").fillna("")
    return result.where(pd.notnull(result), None).to_dict(orient="records")


def realtime_review_summary() -> dict:
    df = load_realtime_reviews()
    if df.empty:
        return {"total_reviews": 0, "platforms": [], "brands": [], "latest_ingested_at": None}

    ingested_at = pd.to_datetime(df["ingested_at"], errors="coerce")
    latest = ingested_at.max()
    return {
        "total_reviews": int(len(df)),
        "platforms": sorted({str(value) for value in df["platform"].dropna().astype(str) if str(value).strip()}),
        "brands": sorted({str(value) for value in df["brand"].dropna().astype(str) if str(value).strip()}),
        "latest_ingested_at": latest.isoformat() if pd.notna(latest) else None,
    }
