from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import (
    MONGO_DB_NAME,
    MONGO_CONNECT_TIMEOUT_MS,
    MONGO_PREDICTIONS_COLLECTION,
    MONGO_REALTIME_REVIEWS_COLLECTION,
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
    return MongoClient is not None and bool(str(MONGO_URI).strip())


def format_mongo_error(error: Exception) -> str:
    text = str(error)
    if "Authentication failed" in text or "bad auth" in text.lower():
        return "MongoDB authentication failed. Check the Atlas username and password."
    if "No servers found yet" in text or "localhost:27017" in text:
        return "MongoDB connection failed. Check that the configured server is reachable."
    if "SSL handshake failed" in text:
        return "MongoDB TLS handshake failed. Check Atlas network and TLS compatibility."
    return "MongoDB operation failed."


def get_database():
    if not mongo_enabled():
        return None
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=MONGO_CONNECT_TIMEOUT_MS)
    return client[MONGO_DB_NAME]


def write_dataframe(df: pd.DataFrame, collection_name: str, replace: bool = True) -> bool:
    if not mongo_enabled() or df.empty:
        return False
    try:
        database = get_database()
        if database is None:
            return False
        collection = database[collection_name]
        if replace:
            collection.delete_many({})
        records = df.where(pd.notnull(df), None).to_dict(orient="records")
        if records:
            collection.insert_many(records)
        return True
    except PyMongoError as error:
        print(f"MongoDB write failed for {collection_name}: {format_mongo_error(error)}")
        return False


def read_dataframe(collection_name: str) -> pd.DataFrame:
    if not mongo_enabled():
        return pd.DataFrame()
    try:
        database = get_database()
        if database is None:
            return pd.DataFrame()
        collection = database[collection_name]
        return pd.DataFrame(list(collection.find({}, {"_id": 0})))
    except PyMongoError as error:
        print(f"MongoDB read failed for {collection_name}: {format_mongo_error(error)}")
        return pd.DataFrame()


def write_processed_reviews(df: pd.DataFrame, replace: bool = True) -> bool:
    return write_dataframe(df, MONGO_REVIEWS_COLLECTION, replace=replace)


def write_predictions(df: pd.DataFrame, replace: bool = True) -> bool:
    return write_dataframe(df, MONGO_PREDICTIONS_COLLECTION, replace=replace)


def append_dataframe(df: pd.DataFrame, collection_name: str) -> bool:
    return write_dataframe(df, collection_name, replace=False)


def append_realtime_reviews(df: pd.DataFrame) -> bool:
    return append_dataframe(df, MONGO_REALTIME_REVIEWS_COLLECTION)
