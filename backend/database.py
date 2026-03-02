from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import (
    MONGO_DB_NAME,
    MONGO_PREDICTIONS_COLLECTION,
    MONGO_REVIEWS_COLLECTION,
    MONGO_URI,
)

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except ImportError:  # pragma: no cover
    MongoClient = None
    PyMongoError = Exception


def mongo_enabled() -> bool:
    return MongoClient is not None


def get_database():
    if not mongo_enabled():
        return None
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    return client[MONGO_DB_NAME]


def write_dataframe(df: pd.DataFrame, collection_name: str, replace: bool = True) -> bool:
    if not mongo_enabled() or df.empty:
        return False
    try:
        collection = get_database()[collection_name]
        if replace:
            collection.delete_many({})
        records = df.where(pd.notnull(df), None).to_dict(orient="records")
        if records:
            collection.insert_many(records)
        return True
    except PyMongoError:
        return False


def read_dataframe(collection_name: str) -> pd.DataFrame:
    if not mongo_enabled():
        return pd.DataFrame()
    try:
        collection = get_database()[collection_name]
        return pd.DataFrame(list(collection.find({}, {"_id": 0})))
    except PyMongoError:
        return pd.DataFrame()


def write_processed_reviews(df: pd.DataFrame, replace: bool = True) -> bool:
    return write_dataframe(df, MONGO_REVIEWS_COLLECTION, replace=replace)


def write_predictions(df: pd.DataFrame, replace: bool = True) -> bool:
    return write_dataframe(df, MONGO_PREDICTIONS_COLLECTION, replace=replace)
