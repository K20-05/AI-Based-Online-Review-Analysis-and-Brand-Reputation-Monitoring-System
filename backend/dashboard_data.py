from __future__ import annotations

from collections import Counter
from functools import lru_cache
import json
from pathlib import Path
import re

import pandas as pd

from backend.brand_score import calculate_brand_score, scoring_frame
from backend.config import BRAND_SCORE_PATH, PREDICTIONS_PATH, REALTIME_REVIEWS_PATH


def normalize_brand_key(value: str) -> str:
    return re.sub(r"[_\s]+", " ", str(value or "")).strip().casefold()


@lru_cache(maxsize=1)
def _prediction_frame_cached(cache_key: tuple) -> pd.DataFrame:
    return scoring_frame()


def predictions_cache_key() -> tuple:
    if not PREDICTIONS_PATH.exists():
        raise FileNotFoundError("Prediction dataset not found. Run prediction first.")
    prediction_stats = PREDICTIONS_PATH.stat()
    if REALTIME_REVIEWS_PATH.exists():
        realtime_stats = REALTIME_REVIEWS_PATH.stat()
        realtime_signature = (
            str(REALTIME_REVIEWS_PATH.resolve()),
            int(realtime_stats.st_mtime_ns),
            int(realtime_stats.st_size),
        )
    else:
        realtime_signature = ("", 0, 0)
    return (
        str(PREDICTIONS_PATH.resolve()),
        int(prediction_stats.st_mtime_ns),
        int(prediction_stats.st_size),
        *realtime_signature,
    )


def prediction_frame() -> pd.DataFrame:
    return _prediction_frame_cached(predictions_cache_key()).copy()


def brand_score_is_stale() -> bool:
    if not BRAND_SCORE_PATH.exists():
        return True

    brand_score_mtime = BRAND_SCORE_PATH.stat().st_mtime_ns
    for dependency_path in (PREDICTIONS_PATH, REALTIME_REVIEWS_PATH):
        if dependency_path.exists() and dependency_path.stat().st_mtime_ns > brand_score_mtime:
            return True
    return False


def dashboard_brand_payload(refresh: bool = False) -> dict:
    if refresh or brand_score_is_stale():
        return calculate_brand_score()
    try:
        return json.loads(BRAND_SCORE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return calculate_brand_score()


@lru_cache(maxsize=1)
def _trend_counts_cached(cache_key: tuple[str, int, int]) -> pd.DataFrame:
    df = _prediction_frame_cached(cache_key)
    required = {"brand", "review_date", "predicted_sentiment"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=["brand_key", "period", "sentiment", "count"])

    review_dates = pd.to_datetime(df["review_date"], errors="coerce")
    valid_mask = review_dates.notna()
    if not valid_mask.any():
        return pd.DataFrame(columns=["brand_key", "period", "sentiment", "count"])

    compact = pd.DataFrame(
        {
            "brand_key": df.loc[valid_mask, "brand"].fillna("").astype(str).map(normalize_brand_key),
            "period": review_dates.loc[valid_mask].dt.to_period("M").astype(str),
            "sentiment": df.loc[valid_mask, "predicted_sentiment"].fillna("").astype(str),
        }
    )
    return (
        compact.groupby(["brand_key", "period", "sentiment"])
        .size()
        .rename("count")
        .reset_index()
    )


def trend_counts_frame() -> pd.DataFrame:
    return _trend_counts_cached(predictions_cache_key())


@lru_cache(maxsize=1)
def _trend_brand_availability_cached(cache_key: tuple[str, int, int]) -> dict[str, bool]:
    grouped = _trend_counts_cached(cache_key)
    if grouped.empty:
        return {}
    keys = grouped["brand_key"].dropna().astype(str).unique().tolist()
    return {key: True for key in keys}


def trend_brand_availability() -> dict[str, bool]:
    return _trend_brand_availability_cached(predictions_cache_key())


def review_samples(
    sentiment: str,
    brand: str = "",
    months: str = "all",
    limit: int = 5,
) -> list[dict]:
    df = prediction_frame()
    if "predicted_sentiment" not in df.columns:
        return []

    sentiment_value = str(sentiment or "").strip()
    if not sentiment_value:
        return []

    working = df[df["predicted_sentiment"].fillna("").astype(str) == sentiment_value].copy()
    if working.empty:
        return []

    if brand:
        brand_key = normalize_brand_key(brand)
        working = working[
            working["brand"].fillna("").astype(str).map(normalize_brand_key) == brand_key
        ].copy()
        if working.empty:
            return []

    parsed_dates = pd.to_datetime(working.get("review_date"), errors="coerce")
    months_value = str(months or "all").strip().lower()
    if months_value != "all" and months_value.isdigit() and parsed_dates.notna().any():
        month_count = max(1, int(months_value))
        latest = parsed_dates.max()
        cutoff = latest - pd.DateOffset(months=month_count - 1)
        working = working[parsed_dates >= cutoff].copy()

    source_series = working.get("review_text")
    if source_series is None:
        source_series = working.get("cleaned_review")
    if source_series is None:
        return []

    working["display_review"] = source_series.fillna("").astype(str).str.strip()
    working = working[working["display_review"] != ""].copy()
    if working.empty:
        return []

    working["parsed_review_date"] = pd.to_datetime(working.get("review_date"), errors="coerce")
    working = working.sort_values(by="parsed_review_date", ascending=False, na_position="last").head(limit)

    return [
        {
            "review_text": str(row.get("display_review", "")),
            "review_date": str(row.get("review_date", "Unknown") or "Unknown"),
            "brand": str(row.get("brand", "Unknown") or "Unknown"),
            "platform": str(row.get("platform", "Unknown") or "Unknown"),
            "rating": None if pd.isna(row.get("rating")) else row.get("rating"),
            "sentiment": str(row.get("predicted_sentiment", sentiment_value)),
        }
        for _, row in working.iterrows()
    ]


def random_brand_review(brand: str = "") -> dict | None:
    df = prediction_frame()
    source_series = df.get("review_text")
    if source_series is None:
        source_series = df.get("cleaned_review")
    if source_series is None:
        return None

    working = df.copy()
    normalized_brand = normalize_brand_key(brand)
    if normalized_brand:
        brand_filtered = working[
            working.get("brand", pd.Series(dtype="string")).fillna("").astype(str).map(normalize_brand_key) == normalized_brand
        ].copy()
        if not brand_filtered.empty:
            working = brand_filtered
        else:
            return random_brand_review("")

    working["display_review"] = source_series.fillna("").astype(str).str.strip()
    working = working[working["display_review"] != ""].copy()
    if working.empty:
        if normalized_brand:
            return random_brand_review("")
        return None

    sample = working.sample(n=1).iloc[0]
    rating = sample.get("rating")
    if pd.isna(rating):
        rating = None
    elif hasattr(rating, "item"):
        rating = rating.item()
    return {
        "review_text": str(sample.get("display_review", "")),
        "brand": str(sample.get("brand", "") or ""),
        "platform": str(sample.get("platform", "") or ""),
        "review_date": str(sample.get("review_date", "") or ""),
        "rating": rating,
        "predicted_sentiment": str(sample.get("predicted_sentiment", "") or ""),
    }


@lru_cache(maxsize=64)
def _keyword_source_frame_cached(cache_key: tuple[str, int, int]) -> pd.DataFrame:
    df = _prediction_frame_cached(cache_key)
    if "cleaned_review" not in df.columns:
        return pd.DataFrame(columns=["brand_key", "sentiment", "review_date", "cleaned_review"])
    return pd.DataFrame(
        {
            "brand_key": df.get("brand", pd.Series(dtype="string")).fillna("").astype(str).map(normalize_brand_key),
            "sentiment": df.get("predicted_sentiment", pd.Series(dtype="string")).fillna("").astype(str),
            "review_date": pd.to_datetime(df.get("review_date"), errors="coerce"),
            "cleaned_review": df.get("cleaned_review", pd.Series(dtype="string")).fillna("").astype(str),
        }
    )


@lru_cache(maxsize=64)
def _dashboard_keywords_cached(
    cache_key: tuple[str, int, int],
    brand: str = "",
    months: str = "all",
    sentiment: str = "",
) -> list[dict]:
    working = _keyword_source_frame_cached(cache_key)
    if working.empty:
        return []

    normalized_brand = normalize_brand_key(brand)
    if normalized_brand:
        working = working[working["brand_key"] == normalized_brand]
        if working.empty:
            return []

    sentiment_value = str(sentiment or "").strip()
    if sentiment_value:
        working = working[working["sentiment"] == sentiment_value]
        if working.empty:
            return []

    months_value = str(months or "all").strip().lower()
    parsed_dates = working["review_date"]
    if months_value != "all" and months_value.isdigit() and parsed_dates.notna().any():
        month_count = max(1, int(months_value))
        latest = parsed_dates.max()
        cutoff = latest - pd.DateOffset(months=month_count - 1)
        working = working[parsed_dates >= cutoff]
        if working.empty:
            return []

    tokens = []
    for text in working["cleaned_review"]:
        tokens.extend(re.findall(r"\b[a-z]{3,}\b", text.lower()))
    return [{"word": word, "count": count} for word, count in Counter(tokens).most_common(12)]


def dashboard_keywords_payload(brand: str = "", months: str = "all", sentiment: str = "") -> list[dict]:
    return _dashboard_keywords_cached(predictions_cache_key(), brand, months, sentiment)


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
    raise KeyError(f"Unknown brand: {brand_name}")


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
    if score < 10:
        cons.append("Brand reputation score is weak")
    if positive_pct < 50:
        cons.append("Positive sentiment is below majority")
    if total_reviews < 1000:
        cons.append("Smaller review base reduces confidence")

    if not pros:
        pros.append("No standout strengths detected")
    if not cons:
        cons.append("No major weaknesses detected")

    if risk["level"] == "high":
        recommendation = "Prioritize service recovery, complaint resolution, and root-cause analysis."
    elif risk["level"] == "medium":
        recommendation = "Monitor complaint clusters closely and improve weak touchpoints before sentiment drops further."
    else:
        recommendation = "Maintain current service quality and continue proactive monitoring."

    return {
        "metrics": row,
        "risk": risk,
        "pros": pros[:4],
        "cons": cons[:4],
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


def platform_breakdown() -> list[dict]:
    df = prediction_frame()
    grouped = (
        df.groupby(["platform", "predicted_sentiment"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    return grouped.to_dict(orient="records")
