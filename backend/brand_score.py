from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import (
    BRAND_REPUTATION_BY_BRAND_PATH,
    BRAND_SCORE_PATH,
    PLATFORM_SUMMARY_PATH,
    PREDICTIONS_PATH,
    SENTIMENT_TRENDS_PATH,
)


def summarize_sentiment_counts(df: pd.DataFrame) -> dict:
    total = len(df)
    positive = int((df["predicted_sentiment"] == "Positive").sum())
    neutral = int((df["predicted_sentiment"] == "Neutral").sum())
    negative = int((df["predicted_sentiment"] == "Negative").sum())
    return {
        "total_reviews": total,
        "positive": positive,
        "neutral": neutral,
        "negative": negative,
        "positive_pct": round((positive / total) * 100, 2) if total else 0.0,
        "neutral_pct": round((neutral / total) * 100, 2) if total else 0.0,
        "negative_pct": round((negative / total) * 100, 2) if total else 0.0,
        "brand_reputation_score": round(((positive - negative) / total) * 100, 2) if total else 0.0,
    }


def calculate_brand_score() -> dict:
    df = pd.read_csv(
        PREDICTIONS_PATH,
        dtype={"review_id": "string", "platform": "string", "brand": "string"},
        low_memory=False,
    )
    if df.empty:
        payload = summarize_sentiment_counts(df)
        payload["brand_scores"] = []
        BRAND_SCORE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        pd.DataFrame(
            columns=[
                "brand",
                "total_reviews",
                "positive",
                "neutral",
                "negative",
                "positive_pct",
                "neutral_pct",
                "negative_pct",
                "brand_reputation_score",
            ]
        ).to_csv(BRAND_REPUTATION_BY_BRAND_PATH, index=False)
        return payload

    brand_column = "brand" if "brand" in df.columns else ("platform" if "platform" in df.columns else None)
    if brand_column is None:
        df["brand"] = "Unknown"
        brand_column = "brand"

    df[brand_column] = df[brand_column].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    payload = summarize_sentiment_counts(df)
    brand_rows = []
    for brand, group in df.groupby(brand_column, sort=True):
        row = {"brand": brand}
        row.update(summarize_sentiment_counts(group))
        brand_rows.append(row)
    payload["brand_scores"] = brand_rows
    pd.DataFrame(brand_rows).to_csv(BRAND_REPUTATION_BY_BRAND_PATH, index=False)

    trend_df = df.copy()
    trend_df["review_date"] = pd.to_datetime(trend_df["review_date"], errors="coerce")
    trend_df = trend_df.dropna(subset=["review_date"])
    if not trend_df.empty:
        trend_df["review_month"] = trend_df["review_date"].dt.to_period("M").astype(str)
        trend_summary = (
            trend_df.groupby(["review_month", "predicted_sentiment"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
        trend_summary.to_csv(SENTIMENT_TRENDS_PATH, index=False)

    if "platform" in df.columns:
        platform_summary = (
            df.groupby("platform")["predicted_sentiment"]
            .value_counts()
            .unstack(fill_value=0)
            .reset_index()
        )
        platform_summary.to_csv(PLATFORM_SUMMARY_PATH, index=False)

    BRAND_SCORE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved brand score: {BRAND_SCORE_PATH}")
    print(f"Saved brand reputation table: {BRAND_REPUTATION_BY_BRAND_PATH}")
    return payload


def main():
    payload = calculate_brand_score()
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
