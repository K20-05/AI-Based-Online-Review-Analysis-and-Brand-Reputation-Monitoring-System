from __future__ import annotations

from typing import Callable

import pandas as pd

from backend.aspect_analysis import analyze_review_aspects, summarize_batch_aspects
from backend.brand_score import summarize_sentiment_counts
from backend.multilingual import apply_multilingual_sentiment_guard, normalize_multilingual_text
from backend.predict import calibrate_prediction_confidence, predict_with_confidence_details
from backend.preprocessing import clean_text, label_from_rating


def parse_predict_payload(payload: dict) -> dict:
    review_text = str(payload.get("review_text", "")).strip()
    if not review_text:
        raise ValueError("review_text is required")

    platform = str(payload.get("platform", "Manual Input")).strip() or "Manual Input"
    brand = str(payload.get("brand", platform)).strip() or platform
    rating = payload.get("rating")
    return {
        "review_text": review_text,
        "platform": platform,
        "brand": brand,
        "rating": rating,
    }


def build_multilingual_review_payload(review_text: str) -> dict:
    multilingual_payload = normalize_multilingual_text(review_text)
    cleaned_review = clean_text(review_text)
    return {
        "cleaned_review": cleaned_review,
        "source_language": multilingual_payload["detected_language"],
        "source_language_label": multilingual_payload["detected_language_label"],
        "language_confidence": multilingual_payload["language_confidence"],
        "translation_applied": multilingual_payload["translation_applied"],
        "multilingual_strategy": multilingual_payload["strategy"],
        "normalized_review": multilingual_payload["normalized_text"],
    }


def predict_single_review(
    request_data: dict,
    load_artifacts: Callable[[], tuple],
) -> dict:
    model, vectorizer = load_artifacts()
    multilingual_review = build_multilingual_review_payload(request_data["review_text"])
    features = vectorizer.transform([multilingual_review["cleaned_review"]])
    prediction_detail = predict_with_confidence_details(model, features)[0]
    predicted_sentiment = str(prediction_detail["predicted_sentiment"])
    raw_predicted_sentiment = str(prediction_detail["raw_predicted_sentiment"])
    class_probabilities = dict(prediction_detail["class_probabilities"])
    raw_model_confidence = prediction_detail["raw_model_confidence"]
    decision_confidence = prediction_detail["decision_confidence"]
    neutral_guard_reason = prediction_detail["neutral_guard_reason"]

    predicted_sentiment, sentiment_adjustment_reason = apply_multilingual_sentiment_guard(
        multilingual_review["normalized_review"],
        predicted_sentiment,
        class_probabilities,
        request_data["rating"],
    )
    prediction_confidence = calibrate_prediction_confidence(
        decision_confidence,
        multilingual_review["cleaned_review"],
        bool(multilingual_review["translation_applied"]),
        multilingual_review["language_confidence"],
        sentiment_adjustment_reason,
        multilingual_review["normalized_review"],
    )
    aspect_payload = analyze_review_aspects(
        request_data["review_text"],
        predicted_sentiment,
        multilingual_review["normalized_review"],
    )
    expected_sentiment = label_from_rating(request_data["rating"]) if request_data["rating"] is not None else None

    return {
        "review_text": request_data["review_text"],
        "cleaned_review": multilingual_review["cleaned_review"],
        "normalized_review": multilingual_review["normalized_review"],
        "source_language": multilingual_review["source_language"],
        "source_language_label": multilingual_review["source_language_label"],
        "language_confidence": multilingual_review["language_confidence"],
        "translation_applied": multilingual_review["translation_applied"],
        "multilingual_strategy": multilingual_review["multilingual_strategy"],
        "rating": request_data["rating"],
        "platform": request_data["platform"],
        "brand": request_data["brand"],
        "predicted_sentiment": predicted_sentiment,
        "raw_predicted_sentiment": raw_predicted_sentiment,
        "class_probabilities": class_probabilities,
        "raw_model_confidence": raw_model_confidence,
        "decision_confidence": decision_confidence,
        "final_confidence": prediction_confidence,
        "prediction_confidence": prediction_confidence,
        "aspect_sentiments": aspect_payload["aspect_sentiments"],
        "aspect_summary": aspect_payload["aspect_summary"],
        "primary_aspect": aspect_payload["primary_aspect"],
        "primary_aspect_sentiment": aspect_payload["primary_aspect_sentiment"],
        "rating_expected_sentiment": expected_sentiment,
        "is_mismatch_with_rating": bool(expected_sentiment and expected_sentiment != predicted_sentiment),
        "sentiment_adjustment_reason": sentiment_adjustment_reason,
        "neutral_guard_reason": neutral_guard_reason,
    }


def _prepare_batch_review(item, index: int) -> dict | None:
    if isinstance(item, dict):
        review_text = str(item.get("review_text", "")).strip()
        review_id = item.get("review_id", index + 1)
        platform = str(item.get("platform", "Manual Batch")).strip() or "Manual Batch"
        brand = str(item.get("brand", platform)).strip() or platform
        rating = item.get("rating")
    else:
        review_text = str(item).strip()
        review_id = index + 1
        platform = "Manual Batch"
        brand = "Manual Batch"
        rating = None

    if not review_text:
        return None

    multilingual_review = build_multilingual_review_payload(review_text)
    return {
        "review_id": review_id,
        "review_text": review_text,
        "cleaned_review": multilingual_review["cleaned_review"],
        "normalized_review": multilingual_review["normalized_review"],
        "source_language": multilingual_review["source_language"],
        "source_language_label": multilingual_review["source_language_label"],
        "language_confidence": multilingual_review["language_confidence"],
        "translation_applied": multilingual_review["translation_applied"],
        "multilingual_strategy": multilingual_review["multilingual_strategy"],
        "platform": platform,
        "brand": brand,
        "rating": rating,
    }


def _batch_brand_score(results: list[dict]) -> dict:
    score_df = pd.DataFrame(
        [
            {
                "brand": row["brand"],
                "predicted_sentiment": row["predicted_sentiment"],
            }
            for row in results
        ]
    )
    batch_score = summarize_sentiment_counts(score_df)
    brand_rows = []
    for brand, group in score_df.groupby("brand", sort=True):
        brand_row = {"brand": str(brand)}
        brand_row.update(summarize_sentiment_counts(group))
        brand_rows.append(brand_row)
    batch_score["brand_scores"] = brand_rows
    return batch_score


def predict_batch_reviews(
    reviews: list,
    load_artifacts: Callable[[], tuple],
) -> dict:
    prepared = []
    for index, item in enumerate(reviews):
        row = _prepare_batch_review(item, index)
        if row is not None:
            prepared.append(row)

    if not prepared:
        raise ValueError("Batch input requires at least one non-empty review_text")

    model, vectorizer = load_artifacts()
    features = vectorizer.transform([row["cleaned_review"] for row in prepared])
    prediction_details = predict_with_confidence_details(model, features)

    results = []
    for index, row in enumerate(prepared):
        detail = prediction_details[index]
        sentiment = str(detail["predicted_sentiment"])
        confidence = detail["decision_confidence"]
        probability_map = dict(detail["class_probabilities"])
        sentiment, adjustment_reason = apply_multilingual_sentiment_guard(
            row["normalized_review"],
            sentiment,
            probability_map,
            row["rating"],
        )
        confidence = calibrate_prediction_confidence(
            confidence,
            row["cleaned_review"],
            bool(row["translation_applied"]),
            row["language_confidence"],
            adjustment_reason,
            row["normalized_review"],
        )
        aspect_payload = analyze_review_aspects(
            row["review_text"],
            sentiment,
            row["normalized_review"],
        )
        expected_sentiment = label_from_rating(row["rating"]) if row["rating"] is not None else None
        results.append(
            {
                "review_id": row["review_id"],
                "review_text": row["review_text"],
                "cleaned_review": row["cleaned_review"],
                "normalized_review": row["normalized_review"],
                "source_language": row["source_language"],
                "source_language_label": row["source_language_label"],
                "language_confidence": row["language_confidence"],
                "translation_applied": row["translation_applied"],
                "multilingual_strategy": row["multilingual_strategy"],
                "platform": row["platform"],
                "brand": row["brand"],
                "rating": row["rating"],
                "predicted_sentiment": sentiment,
                "raw_predicted_sentiment": detail["raw_predicted_sentiment"],
                "class_probabilities": probability_map,
                "raw_model_confidence": detail["raw_model_confidence"],
                "decision_confidence": detail["decision_confidence"],
                "final_confidence": confidence,
                "prediction_confidence": confidence,
                "aspect_sentiments": aspect_payload["aspect_sentiments"],
                "aspect_summary": aspect_payload["aspect_summary"],
                "primary_aspect": aspect_payload["primary_aspect"],
                "primary_aspect_sentiment": aspect_payload["primary_aspect_sentiment"],
                "rating_expected_sentiment": expected_sentiment,
                "is_mismatch_with_rating": bool(expected_sentiment and expected_sentiment != sentiment),
                "sentiment_adjustment_reason": adjustment_reason,
                "neutral_guard_reason": detail["neutral_guard_reason"],
            }
        )

    return {
        "message": "Batch prediction completed",
        "rows": len(results),
        "results": results,
        "brand_score": _batch_brand_score(results),
        "aspect_summary": summarize_batch_aspects(results),
    }
