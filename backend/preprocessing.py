from __future__ import annotations

from pathlib import Path
import re
import sys
from urllib.parse import urlparse

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import (
    CLEANED_DATA_PATH,
    DATASET_DIR,
    LEGACY_RAW_DATA_DIR,
    RAW_DATA_DIR,
    RAW_DATA_EXCLUSIONS,
)
from backend.database import write_processed_reviews
from backend.multilingual import normalize_multilingual_text

try:
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
except ImportError:
    ENGLISH_STOP_WORDS = {
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
        "has", "have", "he", "i", "in", "is", "it", "its", "me", "my", "of",
        "on", "or", "our", "she", "so", "that", "the", "their", "them", "they",
        "this", "to", "was", "we", "were", "with", "you", "your",
    }

OUTPUT_COLUMNS = [
    "review_id",
    "rating",
    "review_date",
    "platform",
    "brand",
    "source_file",
    "source_language",
    "language_confidence",
    "multilingual_strategy",
    "cleaned_review",
]
SCHEMA_MAP = {
    "id": "review_id",
    "review.id": "review_id",
    "Review.id": "review_id",
    "reviewId": "review_id",
    "review.text": "review_text",
    "Review.text": "review_text",
    "Review": "review_text",
    "reviews.text": "review_text",
    "content": "review_text",
    "Review.rating": "rating",
    "Rate": "rating",
    "reviews.rating": "rating",
    "score": "rating",
    "review.date": "review_date",
    "Review.date": "review_date",
    "reviews.date": "review_date",
    "at": "review_date",
    "source": "platform",
    "reviews.sourceURLs": "platform",
    "appName": "platform",
}
NEGATION_TOKENS = {"no", "nor", "not", "never"}
STOP_WORDS = {word for word in ENGLISH_STOP_WORDS if word not in NEGATION_TOKENS}
CSV_ENCODINGS = ("utf-8", "utf-8-sig", "utf-16", "latin-1")


def raw_csv_files() -> list[Path]:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    candidates: list[Path] = []
    seen: set[Path] = set()
    search_plan = (
        (RAW_DATA_DIR, True),
        (LEGACY_RAW_DATA_DIR, True),
        (DATASET_DIR, False),
    )

    for directory, recursive in search_plan:
        if not directory.exists():
            continue
        iterator = directory.rglob("*.csv") if recursive else directory.glob("*.csv")
        for path in iterator:
            resolved = path.resolve()
            if path.name in RAW_DATA_EXCLUSIONS or resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(path)

    return sorted(candidates)


def parse_review_date(value):
    if pd.isna(value) or not str(value).strip():
        return None
    text = str(value).strip()
    if text.isdigit():
        try:
            return pd.to_datetime(int(text), unit="ms", errors="coerce")
        except (OverflowError, ValueError):
            pass
    return pd.to_datetime(text, errors="coerce")


def format_review_dates(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values.apply(parse_review_date), errors="coerce")
    return parsed.dt.strftime("%Y-%m-%d").fillna("Unknown")


def label_from_rating(rating: float) -> str:
    return "Negative" if rating <= 2 else "Neutral" if rating == 3 else "Positive"


def clean_text(text: str) -> str:
    multilingual_payload = normalize_multilingual_text(text)
    tokens = multilingual_payload["normalized_text"].split()
    return " ".join(token for token in tokens if token not in STOP_WORDS)


def normalize_platform(value: str, fallback: str = "Unknown") -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return fallback
    if "://" not in text and "." not in text:
        return text
    host = (urlparse(text if "://" in text else f"https://{text}").netloc or text).lower().split("/")[0]
    host = re.sub(r"^www\.", "", host)
    parts = [part for part in host.split(".") if part]
    return parts[-2] if len(parts) >= 2 else (parts[0] if parts else fallback)


def normalize_brand(value: str, fallback: str) -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return fallback
    return text


def read_csv_with_fallback(path: Path) -> pd.DataFrame:
    last_error = None
    for encoding in CSV_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as error:
            last_error = error
    raise ValueError(f"Unable to read {path.name} with supported encodings {CSV_ENCODINGS}") from last_error


def normalize_frame(path: Path) -> pd.DataFrame:
    df = read_csv_with_fallback(path)
    df = df.rename(columns={col: SCHEMA_MAP[col] for col in SCHEMA_MAP if col in df.columns})
    missing = sorted({"review_text", "rating"} - set(df.columns))
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {missing}")
    if "platform" not in df.columns:
        df["platform"] = path.stem
    if "brand" not in df.columns:
        df["brand"] = df.get("platform", path.stem)
    if "review_id" not in df.columns:
        df["review_id"] = df.index.astype(str)
    if "review_date" not in df.columns:
        df["review_date"] = None
    df["source_file"] = path.stem
    df = df[["review_id", "review_text", "rating", "review_date", "platform", "brand", "source_file"]].copy()
    df["review_text"] = df["review_text"].fillna("Unknown").astype(str)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.dropna(subset=["rating"])
    df["review_date"] = format_review_dates(df["review_date"])
    df["platform"] = df["platform"].apply(lambda value: normalize_platform(value, path.stem))
    df["brand"] = df["brand"].apply(lambda value: normalize_brand(value, path.stem))
    df["source_file"] = df["source_file"].fillna(path.stem).astype(str)
    return df


def load_cleaned_reviews() -> pd.DataFrame:
    df = pd.read_csv(CLEANED_DATA_PATH, low_memory=False)
    required_columns = {"review_id", "rating", "review_date", "platform", "cleaned_review"}
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(f"{CLEANED_DATA_PATH.name} is missing required columns: {missing}")
    if "brand" not in df.columns:
        df["brand"] = df["platform"]
    if "source_file" not in df.columns:
        df["source_file"] = df["platform"]
    if "source_language" not in df.columns:
        df["source_language"] = "unknown"
    if "language_confidence" not in df.columns:
        df["language_confidence"] = 0.0
    if "multilingual_strategy" not in df.columns:
        df["multilingual_strategy"] = "legacy"
    df = df[OUTPUT_COLUMNS].copy()
    df["review_id"] = df["review_id"].astype("string")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.dropna(subset=["rating"])
    df["review_date"] = format_review_dates(df["review_date"])
    df["platform"] = df["platform"].apply(normalize_platform)
    df["brand"] = df["brand"].fillna(df["platform"]).astype(str)
    df["source_file"] = df["source_file"].fillna(df["platform"]).astype(str)
    df["source_language"] = df["source_language"].fillna("unknown").astype(str)
    df["language_confidence"] = pd.to_numeric(df["language_confidence"], errors="coerce").fillna(0.0)
    df["multilingual_strategy"] = df["multilingual_strategy"].fillna("legacy").astype(str)
    df["cleaned_review"] = df["cleaned_review"].fillna("").astype(str)
    return df[df["cleaned_review"].str.strip() != ""].copy()


def sample_reviews_per_dataset(df: pd.DataFrame, limit_per_dataset: int) -> pd.DataFrame:
    if limit_per_dataset <= 0 or "source_file" not in df.columns:
        return df.copy()

    return (
        df.groupby("source_file", group_keys=False, sort=True)
        .apply(lambda group: group.sample(n=min(len(group), limit_per_dataset), random_state=42))
        .reset_index(drop=True)
    )


def preprocess_reviews(save_to_mongo: bool = True) -> pd.DataFrame:
    files = raw_csv_files()
    if not files:
        raise FileNotFoundError(f"No raw CSV files found in {DATASET_DIR}")
    normalized_frames = []
    skipped_files = []
    for path in files:
        try:
            normalized_frames.append(normalize_frame(path))
        except ValueError as error:
            skipped_files.append(f"Skipped {path.name}: {error}")

    if not normalized_frames:
        raise ValueError(f"No valid raw review CSV files found in {DATASET_DIR}")

    df = pd.concat(normalized_frames, ignore_index=True)
    before_rows = len(df)
    multilingual_features = df["review_text"].apply(normalize_multilingual_text)
    df["source_language"] = multilingual_features.apply(lambda item: item["detected_language"])
    df["language_confidence"] = multilingual_features.apply(lambda item: item["language_confidence"])
    df["multilingual_strategy"] = multilingual_features.apply(lambda item: item["strategy"])
    df["cleaned_review"] = multilingual_features.apply(
        lambda item: " ".join(token for token in item["normalized_text"].split() if token not in STOP_WORDS)
    )
    df = df[df["cleaned_review"].str.strip() != ""].copy()
    df = df.drop_duplicates(subset=["cleaned_review", "rating", "platform"], keep="first")
    output_df = df[OUTPUT_COLUMNS].copy()
    after_rows = len(output_df)
    CLEANED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(CLEANED_DATA_PATH, index=False)
    mongo_saved = write_processed_reviews(output_df, replace=True) if save_to_mongo else False
    print(
        f"Saved cleaned dataset: {CLEANED_DATA_PATH}\n"
        f"Rows before preprocessing: {before_rows}\n"
        f"Rows after preprocessing: {after_rows}\n"
        f"MongoDB saved: {mongo_saved}"
    )
    if skipped_files:
        print("\n".join(skipped_files))
    return output_df


def main():
    preprocess_reviews()


if __name__ == "__main__":
    main()
