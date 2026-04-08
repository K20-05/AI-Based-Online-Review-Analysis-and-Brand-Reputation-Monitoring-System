from __future__ import annotations

import math

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score


def build_language_evaluation_frame(
    y_true,
    y_pred,
    source_languages,
) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "source_language": pd.Series(source_languages, dtype="string").fillna("unknown"),
            "y_true": pd.Series(y_true, dtype="string"),
            "y_pred": pd.Series(y_pred, dtype="string"),
        }
    )
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "source_language",
                "support",
                "accuracy",
                "macro_f1",
                "positive_rate",
                "neutral_rate",
                "negative_rate",
            ]
        )

    rows = []
    for language, group in frame.groupby("source_language", sort=True):
        support = int(len(group))
        rows.append(
            {
                "source_language": str(language),
                "support": support,
                "accuracy": float(accuracy_score(group["y_true"], group["y_pred"])) if support else 0.0,
                "macro_f1": float(f1_score(group["y_true"], group["y_pred"], average="macro", zero_division=0))
                if support
                else 0.0,
                "positive_rate": float((group["y_pred"] == "Positive").mean()) if support else 0.0,
                "neutral_rate": float((group["y_pred"] == "Neutral").mean()) if support else 0.0,
                "negative_rate": float((group["y_pred"] == "Negative").mean()) if support else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values(by=["support", "source_language"], ascending=[False, True]).reset_index(drop=True)


def expected_calibration_error(y_true, y_probabilities, labels, bins: int = 10) -> float:
    calibration = build_calibration_frame(y_true, y_probabilities, labels, bins=bins)
    if calibration.empty:
        return 0.0
    total = float(calibration["sample_count"].sum()) or 1.0
    weighted_gap = (calibration["sample_count"] * calibration["gap"]).sum() / total
    return float(weighted_gap)


def build_calibration_frame(y_true, y_probabilities, labels, bins: int = 10) -> pd.DataFrame:
    labels = [str(label) for label in labels]
    y_true_series = pd.Series(y_true, dtype="string")
    probability_frame = pd.DataFrame(y_probabilities, columns=labels)
    if probability_frame.empty:
        return pd.DataFrame(columns=["bin_index", "bin_start", "bin_end", "sample_count", "avg_confidence", "accuracy", "gap"])

    predicted_labels = probability_frame.idxmax(axis=1)
    max_confidence = probability_frame.max(axis=1)
    correctness = (predicted_labels.astype("string") == y_true_series).astype(float)

    bin_ids = (max_confidence * bins).apply(math.floor).clip(lower=0, upper=bins - 1)
    working = pd.DataFrame(
        {
            "bin_index": bin_ids.astype(int),
            "confidence": max_confidence.astype(float),
            "correct": correctness.astype(float),
        }
    )

    rows = []
    for bin_index, group in working.groupby("bin_index", sort=True):
        avg_confidence = float(group["confidence"].mean())
        accuracy = float(group["correct"].mean())
        rows.append(
            {
                "bin_index": int(bin_index),
                "bin_start": round(int(bin_index) / bins, 4),
                "bin_end": round((int(bin_index) + 1) / bins, 4),
                "sample_count": int(len(group)),
                "avg_confidence": avg_confidence,
                "accuracy": accuracy,
                "gap": abs(avg_confidence - accuracy),
            }
        )
    return pd.DataFrame(rows).sort_values("bin_index").reset_index(drop=True)
