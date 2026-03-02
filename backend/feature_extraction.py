from __future__ import annotations

from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import DATASET_DIR, FEATURE_DATASET_PATH, TRAINING_SAMPLE_LIMIT_PER_DATASET
from backend.preprocessing import label_from_rating, load_cleaned_reviews, sample_reviews_per_dataset

LEGACY_MATRIX_PATH = DATASET_DIR / "X_tfidf_legacy.pkl"
LEGACY_VECTORIZER_PATH = DATASET_DIR / "tfidf_vectorizer_legacy.pkl"


def build_feature_dataset() -> pd.DataFrame:
    df = load_cleaned_reviews()
    df = sample_reviews_per_dataset(df, TRAINING_SAMPLE_LIMIT_PER_DATASET)
    df["review_length"] = df["cleaned_review"].str.len()
    df["token_count"] = df["cleaned_review"].str.split().str.len()
    df["sentiment_label"] = df["rating"].apply(label_from_rating)

    tfidf = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=2, dtype=np.float32)
    matrix = tfidf.fit_transform(df["cleaned_review"])

    feature_df = pd.DataFrame.sparse.from_spmatrix(matrix, columns=tfidf.get_feature_names_out())
    feature_df["review_length"] = df["review_length"].values
    feature_df["token_count"] = df["token_count"].values
    feature_df["sentiment_label"] = df["sentiment_label"].values
    feature_df.to_csv(FEATURE_DATASET_PATH, index=False)

    joblib.dump(matrix, LEGACY_MATRIX_PATH)
    joblib.dump(tfidf, LEGACY_VECTORIZER_PATH)

    print(f"Saved feature dataset: {FEATURE_DATASET_PATH}")
    print(f"Feature rows used: {len(df)}")
    print(f"Saved matrix: {LEGACY_MATRIX_PATH}")
    print(f"Saved vectorizer: {LEGACY_VECTORIZER_PATH}")
    return feature_df


def main():
    build_feature_dataset()


if __name__ == "__main__":
    main()
