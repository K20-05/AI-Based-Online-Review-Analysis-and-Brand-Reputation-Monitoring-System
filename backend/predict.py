from __future__ import annotations

from pathlib import Path
import sys

import joblib
import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import MODEL_PATH, PREDICTIONS_PATH, VECTORIZER_PATH
from backend.database import write_predictions
from backend.preprocessing import label_from_rating, load_cleaned_reviews
from backend.visualization import generate_visualizations


# Tune these if needed after testing
LOW_CONFIDENCE_THRESHOLD = 0.55
POS_NEG_GAP_THRESHOLD = 0.15


def predict_with_neutral_guard(model, text_matrix) -> list[str]:
    """
    Predict sentiment using model probabilities.
    If confidence is low, or Positive and Negative are too close,
    force prediction to Neutral.
    """
    if not hasattr(model, "predict_proba"):
        return model.predict(text_matrix).tolist()

    probs = model.predict_proba(text_matrix)
    labels = list(model.classes_)

    predictions = []

    for p in probs:
        label_prob = {label: prob for label, prob in zip(labels, p)}

        pos_prob = label_prob.get("Positive", 0.0)
        neg_prob = label_prob.get("Negative", 0.0)
        neu_prob = label_prob.get("Neutral", 0.0)

        max_prob = max(p)
        best_label = labels[p.argmax()]

        # Rule 1: if model is not confident, mark Neutral
        if max_prob < LOW_CONFIDENCE_THRESHOLD:
            predictions.append("Neutral")
            continue

        # Rule 2: if Positive and Negative are very close, mark Neutral
        if abs(pos_prob - neg_prob) < POS_NEG_GAP_THRESHOLD:
            predictions.append("Neutral")
            continue

        # Rule 3: if Neutral itself is reasonably strong, prefer Neutral
        if neu_prob >= 0.35 and max_prob < 0.65:
            predictions.append("Neutral")
            continue

        predictions.append(best_label)

    return predictions


def predict_dataset(save_to_mongo: bool = True) -> pd.DataFrame:
    df = load_cleaned_reviews()

    # Ground-truth style label from rating for comparison/reference
    df["sentiment_label"] = df["rating"].apply(label_from_rating)

    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)

    text_matrix = vectorizer.transform(df["cleaned_review"].fillna("").astype(str))

    # Improved prediction logic
    df["predicted_sentiment"] = predict_with_neutral_guard(model, text_matrix)

    columns = [
        "review_id",
        "review_date",
        "platform",
        "brand",
        "rating",
        "cleaned_review",
        "sentiment_label",
        "predicted_sentiment",
        "source_file",
    ]

    result_df = df[[column for column in columns if column in df.columns]].copy()
    result_df.to_csv(PREDICTIONS_PATH, index=False)

    mongo_saved = write_predictions(result_df, replace=True) if save_to_mongo else False
    generate_visualizations(result_df)

    print(f"Saved predictions: {PREDICTIONS_PATH}")
    print(f"MongoDB saved: {mongo_saved}")
    return result_df


def main():
    predict_dataset()


if __name__ == "__main__":
    main()