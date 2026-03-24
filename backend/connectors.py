from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys

import pandas as pd

try:
    from kafka import KafkaConsumer
except Exception:  # pragma: no cover
    KafkaConsumer = None

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import CONNECTOR_STATE_PATH, DATASET_DIR, LEGACY_RAW_DATA_DIR, RAW_DATA_DIR, RAW_DATA_EXCLUSIONS
from backend.preprocessing import normalize_frame, parse_review_date


@dataclass
class ConnectorFetchResult:
    connector: str
    reviews: list[dict]
    next_cursor: str | None
    fetched_count: int


class BaseConnector:
    name = "base"
    description = "Base connector"
    supports_polling = True

    def fetch_reviews(self, cursor: str | None = None, limit: int = 20, options: dict | None = None) -> ConnectorFetchResult:
        raise NotImplementedError

    def metadata(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "supports_polling": self.supports_polling,
        }


class MockMarketplaceConnector(BaseConnector):
    name = "mock_marketplace"
    description = "Built-in demo connector that simulates external ecommerce reviews."

    def fetch_reviews(self, cursor: str | None = None, limit: int = 20, options: dict | None = None) -> ConnectorFetchResult:
        options = options or {}
        platform = str(options.get("platform", "MockStore")).strip() or "MockStore"
        brand = str(options.get("brand", platform)).strip() or platform
        feed = [
            {
                "review_id": "mock-1001",
                "review_text": "Package arrived damaged and seller support never replied.",
                "platform": platform,
                "brand": brand,
                "rating": 1,
                "review_date": "2026-03-12",
                "source_type": "connector:mock_marketplace",
            },
            {
                "review_id": "mock-1002",
                "review_text": "Muito bom produto, entrega rapida e preco justo.",
                "platform": platform,
                "brand": brand,
                "rating": 5,
                "review_date": "2026-03-12",
                "source_type": "connector:mock_marketplace",
            },
            {
                "review_id": "mock-1003",
                "review_text": "\u092f\u0939 \u0928\u0915\u0932\u0940 \u092a\u094d\u0930\u0949\u0921\u0915\u094d\u091f \u0939\u0948 \u0914\u0930 \u0930\u093f\u092b\u0902\u0921 \u0928\u0939\u0940\u0902 \u092e\u093f\u0932\u093e",
                "platform": platform,
                "brand": brand,
                "rating": 1,
                "review_date": "2026-03-12",
                "source_type": "connector:mock_marketplace",
            },
        ]
        start = int(cursor or 0)
        batch = feed[start:start + limit]
        next_cursor = str(start + len(batch)) if start + len(batch) < len(feed) else None
        return ConnectorFetchResult(self.name, batch, next_cursor, len(batch))


class DatasetCsvConnector(BaseConnector):
    name = "dataset_csv"
    description = "Poll reviews from local ecommerce CSV datasets using a connector-style interface."

    def fetch_reviews(self, cursor: str | None = None, limit: int = 20, options: dict | None = None) -> ConnectorFetchResult:
        options = options or {}
        paths = _resolve_dataset_csv_paths(options)
        frames: list[pd.DataFrame] = []
        for path in paths:
            frame = normalize_frame(path)
            if frame.empty:
                continue
            frame["connector_source_file"] = path.name
            frame["parsed_review_date"] = frame["review_date"].apply(parse_review_date)
            frame = frame.sort_values(
                by=["parsed_review_date", "review_id"],
                ascending=[False, False],
                na_position="last",
            ).reset_index(drop=True)
            frame["connector_round"] = range(len(frame))
            frames.append(frame)

        if not frames:
            return ConnectorFetchResult(self.name, [], None, 0)

        df = pd.concat(frames, ignore_index=True)
        df = df.sort_values(
            by=["connector_round", "parsed_review_date", "connector_source_file", "review_id"],
            ascending=[True, False, True, False],
            na_position="last",
        ).reset_index(drop=True)

        start = int(cursor or 0)
        selected = df.iloc[start:start + limit].copy()
        reviews = []
        for _, row in selected.iterrows():
            reviews.append(
                {
                    "review_id": str(row.get("review_id", "")),
                    "review_text": str(row.get("review_text", "")),
                    "platform": str(row.get("platform", "")),
                    "brand": str(row.get("brand", "")),
                    "rating": row.get("rating"),
                    "review_date": str(row.get("review_date", "")),
                    "source_type": f"connector:dataset_csv:{row.get('connector_source_file', row.get('source_file', 'dataset'))}",
                }
            )
        next_cursor = str(start + len(reviews)) if start + len(reviews) < len(df) else None
        return ConnectorFetchResult(self.name, reviews, next_cursor, len(reviews))


class KafkaTopicConnector(BaseConnector):
    name = "kafka_topic"
    description = "Consume ecommerce reviews from a Kafka topic and map them into realtime review ingestion."
    supports_polling = True

    def fetch_reviews(self, cursor: str | None = None, limit: int = 20, options: dict | None = None) -> ConnectorFetchResult:
        del cursor
        options = options or {}
        if KafkaConsumer is None:
            raise ImportError("Kafka support is not available. Install dependencies from requirements.txt.")

        topic = str(options.get("topic", "")).strip()
        bootstrap_servers = options.get("bootstrap_servers", "localhost:9092")
        if isinstance(bootstrap_servers, str):
            bootstrap_servers = [item.strip() for item in bootstrap_servers.split(",") if item.strip()]
        if not bootstrap_servers:
            raise ValueError("kafka_topic connector requires bootstrap_servers")
        if not topic:
            raise ValueError("kafka_topic connector requires topic")

        group_id = str(options.get("group_id", "brandpulse-realtime")).strip() or "brandpulse-realtime"
        platform_fallback = str(options.get("platform", "Kafka Stream")).strip() or "Kafka Stream"
        brand_fallback = str(options.get("brand", platform_fallback)).strip() or platform_fallback
        poll_timeout_ms = max(100, int(options.get("poll_timeout_ms", 1500) or 1500))
        consumer_timeout_ms = max(poll_timeout_ms, int(options.get("consumer_timeout_ms", poll_timeout_ms) or poll_timeout_ms))
        auto_offset_reset = str(options.get("auto_offset_reset", "latest")).strip() or "latest"

        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=True,
            consumer_timeout_ms=consumer_timeout_ms,
            value_deserializer=lambda value: value.decode("utf-8", errors="replace"),
        )

        reviews: list[dict] = []
        try:
            batches = consumer.poll(timeout_ms=poll_timeout_ms, max_records=max(1, min(int(limit or 20), 100)))
            for records in batches.values():
                for record in records:
                    payload = self._parse_message(record.value)
                    if payload is None:
                        continue
                    review_text = str(payload.get("review_text", payload.get("text", ""))).strip()
                    if not review_text:
                        continue
                    platform = str(payload.get("platform", platform_fallback)).strip() or platform_fallback
                    brand = str(payload.get("brand", brand_fallback)).strip() or brand_fallback
                    review_id = str(
                        payload.get("review_id")
                        or payload.get("id")
                        or f"kafka-{topic}-{record.partition}-{record.offset}"
                    ).strip()
                    reviews.append(
                        {
                            "review_id": review_id,
                            "review_text": review_text,
                            "platform": platform,
                            "brand": brand,
                            "rating": payload.get("rating"),
                            "review_date": str(payload.get("review_date", payload.get("date", "")) or ""),
                            "source_type": f"connector:kafka_topic:{topic}",
                        }
                    )
        finally:
            consumer.close()

        return ConnectorFetchResult(self.name, reviews, None, len(reviews))

    @staticmethod
    def _parse_message(raw_value: str) -> dict | None:
        text = str(raw_value or "").strip()
        if not text:
            return None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return {"review_text": text}
        return payload if isinstance(payload, dict) else None


CONNECTOR_REGISTRY: dict[str, BaseConnector] = {
    MockMarketplaceConnector.name: MockMarketplaceConnector(),
    DatasetCsvConnector.name: DatasetCsvConnector(),
    KafkaTopicConnector.name: KafkaTopicConnector(),
}


def _connector_csv_candidates() -> list[Path]:
    exclusions = {str(name).strip().lower() for name in RAW_DATA_EXCLUSIONS}
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
        for candidate in iterator:
            if not candidate.is_file():
                continue
            if candidate.name.lower() in exclusions:
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(candidate)

    return candidates


def _locate_connector_csv(file_name: str) -> Path | None:
    requested = Path(file_name)
    requested_name = requested.name.lower()
    requested_suffix = requested.as_posix().replace("\\", "/").lower().lstrip("./")
    for candidate in _connector_csv_candidates():
        candidate_path = candidate.as_posix().replace("\\", "/").lower()
        if candidate.name.lower() == requested_name or candidate_path.endswith(requested_suffix):
            return candidate

    return None


def _resolve_dataset_csv_paths(options: dict) -> list[Path]:
    if bool(options.get("all_files")):
        paths = _connector_csv_candidates()
        if not paths:
            raise FileNotFoundError("No connector source CSV files were found.")
        return paths

    file_names = options.get("file_names")
    if isinstance(file_names, list):
        resolved_paths: list[Path] = []
        seen: set[Path] = set()
        for value in file_names:
            file_name = str(value or "").strip()
            if not file_name:
                continue
            path = _locate_connector_csv(file_name)
            if path is None:
                raise FileNotFoundError(f"Connector source file not found: {file_name}")
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            resolved_paths.append(path)
        if resolved_paths:
            return resolved_paths

    file_name = str(options.get("file_name", "")).strip()
    if not file_name:
        raise ValueError("dataset_csv connector requires file_name, file_names, or all_files=true")

    path = _locate_connector_csv(file_name)
    if path is None:
        raise FileNotFoundError(f"Connector source file not found: {file_name}")
    return [path]


def load_connector_state() -> dict:
    if not CONNECTOR_STATE_PATH.exists():
        return {}
    try:
        return json.loads(CONNECTOR_STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_connector_state(state: dict) -> None:
    CONNECTOR_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONNECTOR_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def list_connectors() -> list[dict]:
    return [connector.metadata() for connector in CONNECTOR_REGISTRY.values()]


def dataset_csv_source_names() -> list[str]:
    return [path.name for path in _connector_csv_candidates()]


def poll_connector(connector_name: str, limit: int = 20, options: dict | None = None, reset_cursor: bool = False) -> dict:
    connector = CONNECTOR_REGISTRY.get(connector_name)
    if connector is None:
        raise ValueError(f"Unknown connector: {connector_name}")

    options = options or {}
    state = load_connector_state()
    state_key = connector_name
    if options:
        normalized_options = "|".join(f"{key}={options[key]}" for key in sorted(options))
        state_key = f"{connector_name}:{normalized_options}"

    cursor = None if reset_cursor else state.get(state_key)
    result = connector.fetch_reviews(cursor=cursor, limit=limit, options=options)
    state[state_key] = result.next_cursor
    save_connector_state(state)

    return {
        "connector": connector_name,
        "cursor_used": cursor,
        "next_cursor": result.next_cursor,
        "fetched_count": result.fetched_count,
        "reviews": result.reviews,
        "options": options,
    }

