from __future__ import annotations

from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import FEATURE_DATASET_PATH, LEGACY_MATRIX_PATH, LEGACY_VECTORIZER_PATH, TRAINING_SAMPLE_LIMIT_PER_DATASET
from backend.preprocessing import label_from_rating, load_cleaned_reviews, sample_reviews_per_dataset


def build_feature_dataset() -> pd.DataFrame:
    df = load_cleaned_reviews()
    print(f"Total cleaned rows loaded: {len(df)}", flush=True)

    df = sample_reviews_per_dataset(df, TRAINING_SAMPLE_LIMIT_PER_DATASET)
    print(f"Feature rows used: {len(df)}", flush=True)
    print(f"Limit per dataset: {TRAINING_SAMPLE_LIMIT_PER_DATASET}", flush=True)

    if "source_file" in df.columns:
        print("\nFeature samples per dataset:", flush=True)
        print(df["source_file"].value_counts().sort_index().to_string(), flush=True)

    df["review_length"] = df["cleaned_review"].str.len()
    df["token_count"] = df["cleaned_review"].str.split().str.len()
    df["sentiment_label"] = df["rating"].apply(label_from_rating)

    print("\nBuilding TF-IDF matrix...", flush=True)
    tfidf = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        min_df=2,
        dtype=np.float32,
    )
    matrix = tfidf.fit_transform(df["cleaned_review"])

    feature_df = df[
        [
            column
            for column in [
                "review_id",
                "platform",
                "brand",
                "source_file",
                "review_length",
                "token_count",
                "sentiment_label",
            ]
            if column in df.columns
        ]
    ].copy()
    feature_df["tfidf_feature_count"] = matrix.shape[1]
    feature_df["tfidf_non_zero_terms"] = matrix.getnnz(axis=1)
    feature_df.to_csv(FEATURE_DATASET_PATH, index=False)

    joblib.dump(matrix, LEGACY_MATRIX_PATH, compress=3)
    joblib.dump(tfidf, LEGACY_VECTORIZER_PATH, compress=3)

    print(f"\nSaved feature dataset: {FEATURE_DATASET_PATH}", flush=True)
    print(f"TF-IDF feature count: {matrix.shape[1]}", flush=True)
    print(f"Saved matrix: {LEGACY_MATRIX_PATH}", flush=True)
    print(f"Saved vectorizer: {LEGACY_VECTORIZER_PATH}", flush=True)

    return feature_df


def main():
    build_feature_dataset()


if __name__ == "__main__":
    main()
