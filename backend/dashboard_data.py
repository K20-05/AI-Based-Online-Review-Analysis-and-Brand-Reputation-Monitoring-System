from __future__ import annotations

from collections import Counter
from functools import lru_cache
import json
import math
import re

import pandas as pd

from backend.brand_score import calculate_brand_score, scoring_frame
from backend.config import BRAND_SCORE_PATH, PREDICTIONS_PATH, REALTIME_REVIEWS_PATH

TOKEN_RE = re.compile(r"\b[a-z]{3,}\b")
KEYWORD_GROUPS_CACHE_PATH = PREDICTIONS_PATH.with_name(f"{PREDICTIONS_PATH.stem}_keyword_groups_cache.json")
REVIEW_SAMPLE_CACHE_PATH = PREDICTIONS_PATH.with_name(f"{PREDICTIONS_PATH.stem}_review_samples_cache.pkl")
KEYWORD_EXCLUSION_WORDS = {
    "app",
    "apps",
    "item",
    "items",
    "order",
    "orders",
    "product",
    "products",
    "shopping",
    "shop",
    "customer",
    "customers",
    "user",
    "users",
    "use",
    "using",
}


def normalize_brand_key(value: str) -> str:
    return re.sub(r"[_\s]+", " ", str(value or "")).strip().casefold()


def parse_review_dates(series: pd.Series) -> pd.Series:
    cleaned = series.fillna("").astype(str).str.strip().replace({"Unknown": "", "unknown": ""})
    return pd.to_datetime(cleaned, format="%Y-%m-%d", errors="coerce")


@lru_cache(maxsize=1)
def _prediction_frame_cached(cache_key: tuple) -> pd.DataFrame:
    return scoring_frame()


def predictions_cache_key() -> tuple:
    if not PREDICTIONS_PATH.exists():
        raise FileNotFoundError("Prediction dataset not found. Run prediction first.")
    prediction_stats = PREDICTIONS_PATH.stat()
    if REALTIME_REVIEWS_PATH.exists():
        realtime_stats = REALTIME_REVIEWS_PATH.stat()
        realtime_signature = (
            str(REALTIME_REVIEWS_PATH.resolve()),
            int(realtime_stats.st_mtime_ns),
            int(realtime_stats.st_size),
        )
    else:
        realtime_signature = ("", 0, 0)
    return (
        str(PREDICTIONS_PATH.resolve()),
        int(prediction_stats.st_mtime_ns),
        int(prediction_stats.st_size),
        *realtime_signature,
    )


def prediction_frame() -> pd.DataFrame:
    return _prediction_frame_cached(predictions_cache_key()).copy()


def brand_score_is_stale() -> bool:
    if not BRAND_SCORE_PATH.exists():
        return True

    brand_score_mtime = BRAND_SCORE_PATH.stat().st_mtime_ns
    for dependency_path in (PREDICTIONS_PATH, REALTIME_REVIEWS_PATH):
        if dependency_path.exists() and dependency_path.stat().st_mtime_ns > brand_score_mtime:
            return True
    return False


def dashboard_brand_payload(refresh: bool = False) -> dict:
    if refresh or brand_score_is_stale():
        return calculate_brand_score(include_auxiliary_outputs=False)
    try:
        return json.loads(BRAND_SCORE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return calculate_brand_score(include_auxiliary_outputs=False)


@lru_cache(maxsize=1)
def _trend_counts_cached(cache_key: tuple[str, int, int]) -> pd.DataFrame:
    df = _prediction_frame_cached(cache_key)
    required = {"brand", "review_date", "predicted_sentiment"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=["brand_key", "period", "sentiment", "count"])

    review_dates = parse_review_dates(df["review_date"])
    valid_mask = review_dates.notna()
    if not valid_mask.any():
        return pd.DataFrame(columns=["brand_key", "period", "sentiment", "count"])

    compact = pd.DataFrame(
        {
            "brand_key": df.loc[valid_mask, "brand"].fillna("").astype(str).map(normalize_brand_key),
            "period": review_dates.loc[valid_mask].dt.to_period("M").astype(str),
            "sentiment": df.loc[valid_mask, "predicted_sentiment"].fillna("").astype(str),
        }
    )
    return (
        compact.groupby(["brand_key", "period", "sentiment"])
        .size()
        .rename("count")
        .reset_index()
    )


def trend_counts_frame() -> pd.DataFrame:
    return _trend_counts_cached(predictions_cache_key())


@lru_cache(maxsize=1)
def _trend_brand_availability_cached(cache_key: tuple[str, int, int]) -> dict[str, bool]:
    grouped = _trend_counts_cached(cache_key)
    if grouped.empty:
        return {}
    keys = grouped["brand_key"].dropna().astype(str).unique().tolist()
    return {key: True for key in keys}


def trend_brand_availability() -> dict[str, bool]:
    return _trend_brand_availability_cached(predictions_cache_key())


@lru_cache(maxsize=1)
def _review_sample_source_frame_cached(cache_key: tuple[str, int, int]) -> pd.DataFrame:
    if REVIEW_SAMPLE_CACHE_PATH.exists():
        try:
            cached_payload = pd.read_pickle(REVIEW_SAMPLE_CACHE_PATH)
            if (
                isinstance(cached_payload, dict)
                and cached_payload.get("signature") == cache_key
                and isinstance(cached_payload.get("frame"), pd.DataFrame)
            ):
                return cached_payload["frame"]
        except Exception:
            pass

    df = _prediction_frame_cached(cache_key)
    if "predicted_sentiment" not in df.columns:
        return pd.DataFrame(
            columns=[
                "row_order",
                "brand_key",
                "platform_key",
                "sentiment",
                "parsed_review_date",
                "review_date_display",
                "display_review",
                "brand",
                "platform",
                "rating",
            ]
        )

    review_text = df.get("review_text", pd.Series(dtype="string")).fillna("").astype(str).str.strip()
    cleaned_review = df.get("cleaned_review", pd.Series(dtype="string")).fillna("").astype(str).str.strip()
    display_review = review_text.where(review_text != "", cleaned_review)
    parsed_review_date = parse_review_dates(df.get("review_date", pd.Series(dtype="string")))
    review_date_display = (
        df.get("review_date", pd.Series(dtype="string"))
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", "Unknown")
    )

    prepared = pd.DataFrame(
        {
            "row_order": pd.RangeIndex(start=0, stop=len(df), step=1),
            "brand_key": df.get("brand", pd.Series(dtype="string")).fillna("").astype(str).map(normalize_brand_key),
            "platform_key": df.get("platform", pd.Series(dtype="string")).fillna("").astype(str).map(normalize_brand_key),
            "sentiment": df.get("predicted_sentiment", pd.Series(dtype="string")).fillna("").astype(str).str.strip(),
            "parsed_review_date": parsed_review_date,
            "review_date_display": review_date_display,
            "display_review": display_review,
            "brand": df.get("brand", pd.Series(dtype="string")).fillna("Unknown").astype(str).replace("", "Unknown"),
            "platform": df.get("platform", pd.Series(dtype="string")).fillna("Unknown").astype(str).replace("", "Unknown"),
            "rating": df.get("rating", pd.Series(dtype="object")),
        }
    )
    filtered = prepared[prepared["display_review"] != ""].copy()
    try:
        pd.to_pickle({"signature": cache_key, "frame": filtered}, REVIEW_SAMPLE_CACHE_PATH)
    except Exception:
        pass
    return filtered


def recent_activity_reviews(limit: int = 5, brand: str = "", platform: str = "") -> list[dict]:
    source = _review_sample_source_frame_cached(predictions_cache_key())
    if source.empty:
        return []

    working = source.copy()
    normalized_brand = normalize_brand_key(brand)
    normalized_platform = normalize_brand_key(platform)

    if normalized_brand:
        working = working[working["brand_key"] == normalized_brand].copy()
        if working.empty:
            return []

    if normalized_platform:
        working = working[working["platform_key"] == normalized_platform].copy()
        if working.empty:
            return []

    working = working.sort_values(
        by=["parsed_review_date", "row_order"],
        ascending=[False, False],
        na_position="last",
    ).head(limit)

    def scalar_or_none(value):
        if pd.isna(value):
            return None
        return value.item() if hasattr(value, "item") else value

    rows = []
    for _, row in working.iterrows():
        parsed_date = row.get("parsed_review_date")
        activity_label = str(row.get("review_date_display", "Unknown") or "Unknown")
        rows.append(
            {
                "review_text": str(row.get("display_review", "")),
                "normalized_review": str(row.get("display_review", "")),
                "review_date": activity_label,
                "brand": str(row.get("brand", "Unknown") or "Unknown"),
                "platform": str(row.get("platform", "Unknown") or "Unknown"),
                "rating": scalar_or_none(row.get("rating")),
                "predicted_sentiment": str(row.get("sentiment", "") or "Unknown"),
                "activity_at": parsed_date.isoformat() if pd.notna(parsed_date) else "",
                "activity_label": activity_label,
                "activity_mode": "dataset",
                "source_type": "prediction_dataset",
                "translation_applied": False,
            }
        )
    return rows


def review_samples(
    sentiment: str,
    brand: str = "",
    months: str = "all",
    limit: int = 5,
) -> list[dict]:
    sentiment_value = str(sentiment or "").strip()
    if not sentiment_value:
        return []

    source = _review_sample_source_frame_cached(predictions_cache_key())
    if source.empty:
        return []

    working = source[source["sentiment"] == sentiment_value].copy()
    if working.empty:
        return []

    if brand:
        brand_key = normalize_brand_key(brand)
        working = working[working["brand_key"] == brand_key].copy()
        if working.empty:
            return []

    months_value = str(months or "all").strip().lower()
    parsed_dates = working["parsed_review_date"]
    if months_value != "all" and months_value.isdigit() and parsed_dates.notna().any():
        month_count = max(1, int(months_value))
        latest = parsed_dates.max()
        cutoff = latest - pd.DateOffset(months=month_count - 1)
        working = working[parsed_dates >= cutoff].copy()
        if working.empty:
            return []

    working = working.sort_values(by="parsed_review_date", ascending=False, na_position="last").head(limit)

    return [
        {
            "review_text": str(row.get("display_review", "")),
            "review_date": str(row.get("review_date_display", "Unknown") or "Unknown"),
            "brand": str(row.get("brand", "Unknown") or "Unknown"),
            "platform": str(row.get("platform", "Unknown") or "Unknown"),
            "rating": None if pd.isna(row.get("rating")) else row.get("rating"),
            "sentiment": str(row.get("sentiment", sentiment_value)),
        }
        for _, row in working.iterrows()
    ]


def random_brand_review(brand: str = "") -> dict | None:
    df = prediction_frame()
    source_series = df.get("review_text")
    if source_series is None:
        source_series = df.get("cleaned_review")
    if source_series is None:
        return None

    working = df.copy()
    normalized_brand = normalize_brand_key(brand)
    if normalized_brand:
        brand_filtered = working[
            working.get("brand", pd.Series(dtype="string")).fillna("").astype(str).map(normalize_brand_key) == normalized_brand
        ].copy()
        if not brand_filtered.empty:
            working = brand_filtered
        else:
            return random_brand_review("")

    working["display_review"] = source_series.fillna("").astype(str).str.strip()
    working = working[working["display_review"] != ""].copy()
    if working.empty:
        if normalized_brand:
            return random_brand_review("")
        return None

    sample = working.sample(n=1).iloc[0]
    rating = sample.get("rating")
    if pd.isna(rating):
        rating = None
    elif hasattr(rating, "item"):
        rating = rating.item()
    return {
        "review_text": str(sample.get("display_review", "")),
        "brand": str(sample.get("brand", "") or ""),
        "platform": str(sample.get("platform", "") or ""),
        "review_date": str(sample.get("review_date", "") or ""),
        "rating": rating,
        "predicted_sentiment": str(sample.get("predicted_sentiment", "") or ""),
    }


@lru_cache(maxsize=64)
def _keyword_source_frame_cached(cache_key: tuple[str, int, int]) -> pd.DataFrame:
    df = _prediction_frame_cached(cache_key)
    if "cleaned_review" not in df.columns:
        return pd.DataFrame(columns=["brand_key", "sentiment", "review_date", "cleaned_review"])
    return pd.DataFrame(
        {
            "brand_key": df.get("brand", pd.Series(dtype="string")).fillna("").astype(str).map(normalize_brand_key),
            "sentiment": df.get("predicted_sentiment", pd.Series(dtype="string")).fillna("").astype(str),
            "review_date": parse_review_dates(df.get("review_date", pd.Series(dtype="string"))),
            "cleaned_review": df.get("cleaned_review", pd.Series(dtype="string")).fillna("").astype(str),
        }
    )


@lru_cache(maxsize=64)
def _filtered_keyword_frame_cached(
    cache_key: tuple[str, int, int],
    brand: str = "",
    months: str = "all",
) -> pd.DataFrame:
    working = _keyword_source_frame_cached(cache_key)
    if working.empty:
        return pd.DataFrame(columns=working.columns)

    normalized_brand = normalize_brand_key(brand)
    if normalized_brand:
        working = working[working["brand_key"] == normalized_brand]
        if working.empty:
            return pd.DataFrame(columns=working.columns)

    months_value = str(months or "all").strip().lower()
    parsed_dates = working["review_date"]
    if months_value != "all" and months_value.isdigit() and parsed_dates.notna().any():
        month_count = max(1, int(months_value))
        latest = parsed_dates.max()
        cutoff = latest - pd.DateOffset(months=month_count - 1)
        working = working[parsed_dates >= cutoff]
        if working.empty:
            return pd.DataFrame(columns=working.columns)

    return working.copy()


def _keyword_counter(texts: pd.Series) -> Counter:
    counter: Counter[str] = Counter()
    for text in texts:
        counter.update(
            token
            for token in TOKEN_RE.findall(str(text).lower())
            if token not in KEYWORD_EXCLUSION_WORDS
        )
    return counter


def _rank_keyword_counter(target_counter: Counter, overall_counter: Counter) -> list[dict]:
    if not target_counter:
        return []

    top_count = max(target_counter.values(), default=0)
    minimum_count = max(3, min(40, int(top_count * 0.05)))
    scored_keywords = []
    for word, count in target_counter.items():
        if count < minimum_count:
            continue
        total = overall_counter.get(word, 0)
        if total <= 0:
            continue
        sentiment_share = count / total
        distinctiveness = sentiment_share * math.log1p(count)
        scored_keywords.append((distinctiveness, count, sentiment_share, word))

    scored_keywords.sort(key=lambda item: (-item[0], -item[1], item[3]))
    return [
        {
            "word": word,
            "count": count,
            "sentiment_share": round(sentiment_share, 4),
        }
        for _, count, sentiment_share, word in scored_keywords[:12]
    ]


def _keyword_groups_dependency_mtime_ns(cache_key: tuple) -> int:
    prediction_mtime_ns = int(cache_key[1]) if len(cache_key) > 1 else 0
    realtime_mtime_ns = int(cache_key[4]) if len(cache_key) > 4 else 0
    return max(prediction_mtime_ns, realtime_mtime_ns)


def _keyword_groups_disk_cache_is_current(cache_key: tuple) -> bool:
    return (
        KEYWORD_GROUPS_CACHE_PATH.exists()
        and KEYWORD_GROUPS_CACHE_PATH.stat().st_mtime_ns >= _keyword_groups_dependency_mtime_ns(cache_key)
    )


def _normalize_keyword_group_payload(payload: dict | None) -> dict[str, list[dict]]:
    normalized = {"Positive": [], "Neutral": [], "Negative": []}
    if not isinstance(payload, dict):
        return normalized
    for sentiment in normalized:
        rows = payload.get(sentiment, [])
        normalized[sentiment] = rows if isinstance(rows, list) else []
    return normalized


def _load_keyword_groups_disk_cache(cache_key: tuple) -> dict[str, list[dict]] | None:
    if not _keyword_groups_disk_cache_is_current(cache_key):
        return None
    try:
        payload = json.loads(KEYWORD_GROUPS_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return _normalize_keyword_group_payload(payload)


def _write_keyword_groups_disk_cache(payload: dict[str, list[dict]]) -> None:
    try:
        KEYWORD_GROUPS_CACHE_PATH.write_text(
            json.dumps(_normalize_keyword_group_payload(payload), ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        return


@lru_cache(maxsize=64)
def _dashboard_keyword_groups_cached(
    cache_key: tuple[str, int, int],
    brand: str = "",
    months: str = "all",
) -> dict[str, list[dict]]:
    working = _filtered_keyword_frame_cached(cache_key, brand, months)
    if working.empty:
        return {"Positive": [], "Neutral": [], "Negative": []}

    overall_counter: Counter[str] = Counter()
    sentiment_counters: dict[str, Counter] = {}
    for sentiment_name, sentiment_frame in working.groupby("sentiment"):
        normalized_sentiment = str(sentiment_name or "").strip()
        if not normalized_sentiment:
            continue
        counter = _keyword_counter(sentiment_frame["cleaned_review"])
        sentiment_counters[normalized_sentiment] = counter
        overall_counter.update(counter)

    if not overall_counter:
        return {"Positive": [], "Neutral": [], "Negative": []}

    return {
        "Positive": _rank_keyword_counter(sentiment_counters.get("Positive", Counter()), overall_counter),
        "Neutral": _rank_keyword_counter(sentiment_counters.get("Neutral", Counter()), overall_counter),
        "Negative": _rank_keyword_counter(sentiment_counters.get("Negative", Counter()), overall_counter),
    }


@lru_cache(maxsize=64)
def _dashboard_keywords_cached(
    cache_key: tuple[str, int, int],
    brand: str = "",
    months: str = "all",
    sentiment: str = "",
) -> list[dict]:
    working = _filtered_keyword_frame_cached(cache_key, brand, months)
    if working.empty:
        return []

    overall_counter = _keyword_counter(working["cleaned_review"])

    if not overall_counter:
        return []

    sentiment_value = str(sentiment or "").strip()
    if not sentiment_value:
        return [{"word": word, "count": count} for word, count in overall_counter.most_common(12)]

    return _dashboard_keyword_groups_cached(cache_key, brand, months).get(sentiment_value, [])


def dashboard_keywords_payload(brand: str = "", months: str = "all", sentiment: str = "") -> list[dict]:
    return _dashboard_keywords_cached(predictions_cache_key(), brand, months, sentiment)


def dashboard_keyword_groups_payload(brand: str = "", months: str = "all") -> dict[str, list[dict]]:
    cache_key = predictions_cache_key()
    normalized_brand = str(brand or "").strip()
    normalized_months = str(months or "all").strip().lower() or "all"
    can_use_disk_cache = not normalized_brand and normalized_months == "all"
    if can_use_disk_cache:
        cached_payload = _load_keyword_groups_disk_cache(cache_key)
        if cached_payload is not None:
            return cached_payload

    payload = _dashboard_keyword_groups_cached(cache_key, normalized_brand, normalized_months)
    if can_use_disk_cache:
        _write_keyword_groups_disk_cache(payload)
    return payload


def brand_rows() -> list[dict]:
    rows = dashboard_brand_payload().get("brand_scores", [])
    normalized = []
    for row in rows:
        normalized.append(
            {
                "brand": str(row.get("brand", "Unknown")),
                "total_reviews": int(float(row.get("total_reviews", 0) or 0)),
                "positive_pct": float(row.get("positive_pct", 0) or 0),
                "neutral_pct": float(row.get("neutral_pct", 0) or 0),
                "negative_pct": float(row.get("negative_pct", 0) or 0),
                "brand_reputation_score": float(row.get("brand_reputation_score", 0) or 0),
            }
        )
    return normalized


def find_brand_row(brand_name: str) -> dict:
    lookup = brand_name.strip().lower()
    for row in brand_rows():
        if row["brand"].strip().lower() == lookup:
            return row
    raise KeyError(f"Unknown brand: {brand_name}")


def risk_profile(score: float, negative_pct: float) -> dict:
    if score >= 45 and negative_pct < 25:
        return {"level": "low", "label": "Low Risk"}
    if score < 10 or negative_pct >= 40:
        return {"level": "high", "label": "High Risk"}
    return {"level": "medium", "label": "Medium Risk"}


def build_brand_insights(row: dict) -> dict:
    score = float(row["brand_reputation_score"])
    negative_pct = float(row["negative_pct"])
    positive_pct = float(row["positive_pct"])
    total_reviews = int(row["total_reviews"])
    risk = risk_profile(score, negative_pct)

    pros = []
    cons = []

    if positive_pct >= 65:
        pros.append("Strong positive sentiment share")
    if score >= 40:
        pros.append("Healthy brand reputation score")
    if negative_pct <= 20:
        pros.append("Complaint pressure is relatively low")
    if total_reviews >= 5000:
        pros.append("Large review volume supports confidence")

    if negative_pct >= 35:
        cons.append("Negative sentiment is elevated")
    if score < 10:
        cons.append("Brand reputation score is weak")
    if positive_pct < 50:
        cons.append("Positive sentiment is below majority")
    if total_reviews < 1000:
        cons.append("Smaller review base reduces confidence")

    if not pros:
        pros.append("No standout strengths detected")
    if not cons:
        cons.append("No major weaknesses detected")

    if risk["level"] == "high":
        recommendation = "Prioritize service recovery, complaint resolution, and root-cause analysis."
    elif risk["level"] == "medium":
        recommendation = "Monitor complaint clusters closely and improve weak touchpoints before sentiment drops further."
    else:
        recommendation = "Maintain current service quality and continue proactive monitoring."

    return {
        "metrics": row,
        "risk": risk,
        "pros": pros[:4],
        "cons": cons[:4],
        "recommendation": recommendation,
    }


def similar_brand_rows(base_row: dict, limit: int = 3) -> list[dict]:
    scored_rows = []
    for row in brand_rows():
        if row["brand"] == base_row["brand"]:
            continue
        distance = (
            abs(row["brand_reputation_score"] - base_row["brand_reputation_score"])
            + abs(row["positive_pct"] - base_row["positive_pct"]) * 0.4
            + abs(row["negative_pct"] - base_row["negative_pct"]) * 0.5
        )
        scored_rows.append(
            {
                "brand": row["brand"],
                "metrics": row,
                "risk": risk_profile(row["brand_reputation_score"], row["negative_pct"]),
                "distance": round(distance, 2),
            }
        )
    return sorted(scored_rows, key=lambda item: item["distance"])[:limit]


def platform_breakdown() -> list[dict]:
    df = prediction_frame()
    grouped = (
        df.groupby(["platform", "predicted_sentiment"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    return grouped.to_dict(orient="records")
