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


def predict_dataset(save_to_mongo: bool = True) -> pd.DataFrame:
    df = load_cleaned_reviews()
    df["sentiment_label"] = df["rating"].apply(label_from_rating)
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)

    text_matrix = vectorizer.transform(df["cleaned_review"].fillna("").astype(str))
    df["predicted_sentiment"] = model.predict(text_matrix)

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
