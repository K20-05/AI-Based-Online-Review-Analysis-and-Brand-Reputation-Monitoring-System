from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

import matplotlib.pyplot as plt
import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.paths import (
    KEYWORD_FREQUENCY_PATH,
    PLATFORM_DISTRIBUTION_PATH,
    PREDICTIONS_PATH,
    REVIEW_TRENDS_CHART_PATH,
    SENTIMENT_DISTRIBUTION_PATH,
)


def load_predictions() -> pd.DataFrame:
    return pd.read_csv(
        PREDICTIONS_PATH,
        dtype={"review_id": "string", "platform": "string", "brand": "string"},
        low_memory=False,
    )


def generate_visualizations(df: pd.DataFrame | None = None) -> None:
    if df is None:
        df = load_predictions()

    sentiment_counts = df["predicted_sentiment"].value_counts().reindex(
        ["Positive", "Neutral", "Negative"], fill_value=0
    )
    plt.figure(figsize=(7, 4.5))
    plt.bar(sentiment_counts.index, sentiment_counts.values, color=["#2a9d8f", "#e9c46a", "#e76f51"])
    plt.title("Sentiment Distribution")
    plt.xlabel("Sentiment")
    plt.ylabel("Reviews")
    plt.tight_layout()
    plt.savefig(SENTIMENT_DISTRIBUTION_PATH, dpi=300)
    plt.close()

    trend_df = df.copy()
    trend_df["review_date"] = pd.to_datetime(trend_df.get("review_date"), errors="coerce")
    trend_df = trend_df.dropna(subset=["review_date"])
    if not trend_df.empty:
        trend_df["review_month"] = trend_df["review_date"].dt.to_period("M").astype(str)
        grouped = (
            trend_df.groupby(["review_month", "predicted_sentiment"])
            .size()
            .unstack(fill_value=0)
            .sort_index()
        )
        grouped = grouped.reindex(columns=["Positive", "Neutral", "Negative"], fill_value=0)
        plt.figure(figsize=(9, 4.8))
        for label, color in [("Positive", "#2a9d8f"), ("Neutral", "#e9c46a"), ("Negative", "#e76f51")]:
            plt.plot(grouped.index, grouped[label], marker="o", linewidth=2, label=label, color=color)
        plt.title("Review Trend Over Time")
        plt.xlabel("Month")
        plt.ylabel("Reviews")
        plt.xticks(rotation=45, ha="right")
        plt.legend()
        plt.tight_layout()
        plt.savefig(REVIEW_TRENDS_CHART_PATH, dpi=300)
        plt.close()

    tokens = []
    for text in df.get("cleaned_review", pd.Series(dtype=str)).fillna("").astype(str):
        tokens.extend(re.findall(r"\b[a-z]{3,}\b", text.lower()))
    top_keywords = Counter(tokens).most_common(12)
    if top_keywords:
        labels, values = zip(*top_keywords)
        plt.figure(figsize=(10, 4.8))
        plt.bar(labels, values, color="#457b9d")
        plt.title("Keyword Frequency")
        plt.xlabel("Keyword")
        plt.ylabel("Frequency")
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        plt.savefig(KEYWORD_FREQUENCY_PATH, dpi=300)
        plt.close()

    if "platform" in df.columns:
        platform_counts = df["platform"].value_counts().head(10)
        plt.figure(figsize=(8, 4.8))
        plt.bar(platform_counts.index, platform_counts.values, color="#6d597a")
        plt.title("Platform Distribution")
        plt.xlabel("Platform")
        plt.ylabel("Reviews")
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        plt.savefig(PLATFORM_DISTRIBUTION_PATH, dpi=300)
        plt.close()


def main():
    generate_visualizations()


if __name__ == "__main__":
    main()
