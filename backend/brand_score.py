from __future__ import annotations

import json
from functools import lru_cache
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
from backend.realtime_reviews import load_realtime_reviews

PREDICTIONS_FRAME_CACHE_PATH = PREDICTIONS_PATH.with_name(f"{PREDICTIONS_PATH.stem}_dashboard_cache.pkl")
PREDICTIONS_REQUIRED_COLUMNS = (
    "review_id",
    "review_date",
    "platform",
    "brand",
    "rating",
    "cleaned_review",
    "predicted_sentiment",
)
PREDICTIONS_DTYPES = {
    "review_id": "string",
    "review_date": "string",
    "platform": "string",
    "brand": "string",
    "cleaned_review": "string",
    "predicted_sentiment": "string",
}


def parse_review_dates(series: pd.Series) -> pd.Series:
    cleaned = series.fillna("").astype(str).str.strip().replace({"Unknown": "", "unknown": ""})
    return pd.to_datetime(cleaned, format="%Y-%m-%d", errors="coerce")


def prediction_file_signature() -> tuple[str, int, int]:
    stats = PREDICTIONS_PATH.stat()
    return (
        str(PREDICTIONS_PATH.resolve()),
        int(stats.st_mtime_ns),
        int(stats.st_size),
    )


def _cache_file_is_current(source_mtime_ns: int) -> bool:
    return PREDICTIONS_FRAME_CACHE_PATH.exists() and PREDICTIONS_FRAME_CACHE_PATH.stat().st_mtime_ns >= source_mtime_ns


def _prediction_usecols() -> list[str]:
    available_columns = pd.read_csv(PREDICTIONS_PATH, nrows=0).columns.tolist()
    return [column for column in PREDICTIONS_REQUIRED_COLUMNS if column in available_columns]


def _read_base_predictions_from_csv() -> pd.DataFrame:
    usecols = _prediction_usecols()
    dtype_map = {column: dtype for column, dtype in PREDICTIONS_DTYPES.items() if column in usecols}
    return pd.read_csv(
        PREDICTIONS_PATH,
        usecols=usecols,
        dtype=dtype_map,
        low_memory=False,
    )


@lru_cache(maxsize=1)
def _load_base_predictions_frame_cached(signature: tuple[str, int, int]) -> pd.DataFrame:
    _, source_mtime_ns, _ = signature
    if _cache_file_is_current(source_mtime_ns):
        try:
            return pd.read_pickle(PREDICTIONS_FRAME_CACHE_PATH)
        except Exception:
            pass

    frame = _read_base_predictions_from_csv()
    try:
        frame.to_pickle(PREDICTIONS_FRAME_CACHE_PATH)
    except Exception:
        pass
    return frame


def load_base_predictions_frame() -> pd.DataFrame:
    return _load_base_predictions_frame_cached(prediction_file_signature()).copy(deep=False)


def merge_scoring_sources(base_df: pd.DataFrame, realtime_df: pd.DataFrame) -> pd.DataFrame:
    if realtime_df.empty:
        return base_df

    realtime_df = realtime_df.copy()
    if "source_file" not in realtime_df.columns:
        realtime_df["source_file"] = realtime_df.get("source_type", "realtime")
    if "sentiment_label" not in realtime_df.columns:
        realtime_df["sentiment_label"] = None

    preferred_columns = list(dict.fromkeys([*base_df.columns.tolist(), *realtime_df.columns.tolist()]))
    base_df = base_df.reindex(columns=preferred_columns)
    realtime_df = realtime_df.reindex(columns=preferred_columns)
    merged = pd.concat([base_df, realtime_df], ignore_index=True)
    if "review_id" in merged.columns:
        merged = merged.drop_duplicates(subset=["review_id"], keep="last")
    return merged


def scoring_frame(
    base_df: pd.DataFrame | None = None,
    realtime_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if base_df is None:
        base_df = load_base_predictions_frame()
    if realtime_df is None:
        realtime_df = load_realtime_reviews()
    return merge_scoring_sources(base_df, realtime_df)


def summarize_sentiment_counts(df: pd.DataFrame) -> dict:
    total = len(df)
    positive = int((df["predicted_sentiment"] == "Positive").sum())
    neutral = int((df["predicted_sentiment"] == "Neutral").sum())
    negative = int((df["predicted_sentiment"] == "Negative").sum())

    positive_pct = round((positive / total) * 100, 2) if total else 0.0
    neutral_pct = round((neutral / total) * 100, 2) if total else 0.0
    negative_pct = round((negative / total) * 100, 2) if total else 0.0

    # Updated weighted score formula
    # Positive = +1, Neutral = +0.5, Negative = -1
    brand_reputation_score = (
        round((((positive * 1.0) + (neutral * 0.5) - (negative * 1.0)) / total) * 100, 2)
        if total
        else 0.0
    )

    return {
        "total_reviews": total,
        "positive": positive,
        "neutral": neutral,
        "negative": negative,
        "positive_pct": positive_pct,
        "neutral_pct": neutral_pct,
        "negative_pct": negative_pct,
        "brand_reputation_score": brand_reputation_score,
    }


def format_brand_score_report(payload: dict) -> str:
    brand_rows = payload.get("brand_scores", [])
    lines = [
        "",
        "=" * 78,
        "BRAND REPUTATION SUMMARY",
        "=" * 78,
        f"Total Reviews            : {payload.get('total_reviews', 0):,}",
        f"Baseline Reviews         : {payload.get('baseline_total_reviews', 0):,}",
        f"Realtime Reviews         : {payload.get('realtime_total_reviews', 0):,}",
        f"Positive Reviews         : {payload.get('positive', 0):,} ({payload.get('positive_pct', 0):.2f}%)",
        f"Neutral Reviews          : {payload.get('neutral', 0):,} ({payload.get('neutral_pct', 0):.2f}%)",
        f"Negative Reviews         : {payload.get('negative', 0):,} ({payload.get('negative_pct', 0):.2f}%)",
        f"Brand Reputation Score   : {payload.get('brand_reputation_score', 0):.2f}",
        "",
    ]

    if not brand_rows:
        lines.append("No brand-level scores available.")
        return "\n".join(lines)

    lines.extend(
        [
            "Brand-Level Breakdown",
            "-" * 78,
            f"{'Brand':<30} {'Reviews':>10} {'Positive %':>12} {'Negative %':>12} {'Score':>10}",
            "-" * 78,
        ]
    )
    for row in brand_rows:
        brand = str(row.get("brand", "Unknown"))[:30]
        lines.append(
            f"{brand:<30} "
            f"{row.get('total_reviews', 0):>10,} "
            f"{row.get('positive_pct', 0):>11.2f}% "
            f"{row.get('negative_pct', 0):>11.2f}% "
            f"{row.get('brand_reputation_score', 0):>10.2f}"
        )
    lines.append("-" * 78)
    return "\n".join(lines)


def calculate_brand_score(include_auxiliary_outputs: bool = True) -> dict:
    base_df = load_base_predictions_frame()
    realtime_df = load_realtime_reviews()
    df = scoring_frame(base_df=base_df, realtime_df=realtime_df)

    if df.empty:
        payload = summarize_sentiment_counts(df)
        payload["brand_scores"] = []
        payload["baseline_total_reviews"] = 0
        payload["realtime_total_reviews"] = 0
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

    df[brand_column] = (
        df[brand_column]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .replace("", "Unknown")
    )

    payload = summarize_sentiment_counts(df)
    payload["baseline_total_reviews"] = int(len(base_df))
    payload["realtime_total_reviews"] = int(len(realtime_df))

    brand_rows = []
    for brand, group in df.groupby(brand_column, sort=True):
        row = {"brand": brand}
        row.update(summarize_sentiment_counts(group))
        brand_rows.append(row)

    payload["brand_scores"] = brand_rows
    pd.DataFrame(brand_rows).to_csv(BRAND_REPUTATION_BY_BRAND_PATH, index=False)

    if include_auxiliary_outputs:
        trend_df = df.copy()
        if "review_date" in trend_df.columns:
            trend_df["review_date"] = parse_review_dates(trend_df["review_date"])
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
    print(format_brand_score_report(payload))


if __name__ == "__main__":
    main()
