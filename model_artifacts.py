from __future__ import annotations

from pathlib import Path

import joblib

from backend.config import MODEL_PATH, VECTORIZER_PATH

_ARTIFACT_CACHE = {
    "signature": None,
    "model": None,
    "vectorizer": None,
}


def _artifact_signature(path: Path) -> tuple[int, int]:
    stats = path.stat()
    return int(stats.st_mtime_ns), int(stats.st_size)


def load_model_artifacts():
    if not MODEL_PATH.exists() or not VECTORIZER_PATH.exists():
        raise FileNotFoundError("Model artifacts are missing. Run training first.")
    signature = (_artifact_signature(MODEL_PATH), _artifact_signature(VECTORIZER_PATH))
    if _ARTIFACT_CACHE["signature"] != signature:
        _ARTIFACT_CACHE["model"] = joblib.load(MODEL_PATH)
        _ARTIFACT_CACHE["vectorizer"] = joblib.load(VECTORIZER_PATH)
        _ARTIFACT_CACHE["signature"] = signature
    return _ARTIFACT_CACHE["model"], _ARTIFACT_CACHE["vectorizer"]
