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


def _decision_details_from_probability_row(probabilities, labels) -> dict:
    label_prob = {str(label): float(prob) for label, prob in zip(labels, probabilities)}
    ranked = sorted(label_prob.items(), key=lambda item: item[1], reverse=True)
    best_label, best_prob = ranked[0]
    second_prob = ranked[1][1] if len(ranked) > 1 else 0.0
    pos_prob = label_prob.get("Positive", 0.0)
    neg_prob = label_prob.get("Negative", 0.0)
    neu_prob = label_prob.get("Neutral", 0.0)

    predicted_sentiment = best_label
    decision_confidence = best_prob
    neutral_guard_reason = None

    if best_prob < LOW_CONFIDENCE_THRESHOLD:
        predicted_sentiment = "Neutral"
        neutral_guard_reason = "low_confidence"
        severity = min(1.0, max(0.0, (LOW_CONFIDENCE_THRESHOLD - best_prob) / LOW_CONFIDENCE_THRESHOLD))
        decision_confidence = 0.52 + (0.16 * severity)
    elif abs(pos_prob - neg_prob) < POS_NEG_GAP_THRESHOLD:
        predicted_sentiment = "Neutral"
        neutral_guard_reason = "pos_neg_ambiguous"
        closeness = 1.0 - (abs(pos_prob - neg_prob) / POS_NEG_GAP_THRESHOLD)
        decision_confidence = max(neu_prob, 0.56 + (0.18 * closeness))
    elif neu_prob >= 0.35 and best_prob < 0.65:
        predicted_sentiment = "Neutral"
        neutral_guard_reason = "neutral_probability_guard"
        strength = min(1.0, max(0.0, (neu_prob - 0.35) / 0.30))
        decision_confidence = max(neu_prob, 0.58 + (0.18 * strength))

    return {
        "predicted_sentiment": predicted_sentiment,
        "raw_predicted_sentiment": best_label,
        "class_probabilities": label_prob,
        "raw_model_confidence": best_prob,
        "decision_confidence": min(max(float(decision_confidence), 0.0), 0.995),
        "neutral_guard_reason": neutral_guard_reason,
        "probability_margin": max(0.0, best_prob - second_prob),
    }


def predict_with_confidence_details(model, text_matrix) -> list[dict]:
    if not hasattr(model, "predict_proba") or not hasattr(model, "classes_"):
        predictions = model.predict(text_matrix).tolist()
        return [
            {
                "predicted_sentiment": str(label),
                "raw_predicted_sentiment": str(label),
                "class_probabilities": {},
                "raw_model_confidence": None,
                "decision_confidence": None,
                "neutral_guard_reason": None,
                "probability_margin": None,
            }
            for label in predictions
        ]

    probabilities = model.predict_proba(text_matrix)
    labels = list(model.classes_)
    return [_decision_details_from_probability_row(row, labels) for row in probabilities]


def calibrate_prediction_confidence(
    decision_confidence: float | None,
    cleaned_review: str,
    translation_applied: bool = False,
    language_confidence: float | None = None,
    sentiment_adjustment_reason: str | None = None,
    normalized_review: str | None = None,
) -> float | None:
    if decision_confidence is None:
        return None

    confidence = float(decision_confidence)
    cleaned_token_count = len(str(cleaned_review or "").split())
    normalized_token_count = len(str(normalized_review or "").split())
    token_count = max(cleaned_token_count, normalized_token_count)

    if translation_applied and language_confidence is not None:
        model_weight = 0.78 if token_count >= 2 else 0.72
        confidence = (confidence * model_weight) + (float(language_confidence) * (1.0 - model_weight))

    if token_count <= 1:
        confidence -= 0.12 if translation_applied else 0.08
    elif token_count == 2:
        confidence -= 0.06 if translation_applied else 0.03


    if sentiment_adjustment_reason:
        confidence = max(confidence, 0.60)
        confidence = min(confidence, 0.78 if translation_applied else 0.82)

    return round(min(max(confidence, 0.0), 0.995), 4)


def predict_with_neutral_guard(model, text_matrix) -> list[str]:
    """
    Predict sentiment using model probabilities.
    If confidence is low, or Positive and Negative are too close,
    force prediction to Neutral.
    """
    return [item["predicted_sentiment"] for item in predict_with_confidence_details(model, text_matrix)]


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
        "source_language",
        "language_confidence",
        "multilingual_strategy",
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
