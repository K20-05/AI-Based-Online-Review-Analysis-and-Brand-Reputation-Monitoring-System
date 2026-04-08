from __future__ import annotations

from datetime import datetime, UTC
import json
from pathlib import Path
import sys
import threading
import time

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import CONNECTOR_SCHEDULER_PATH
from backend.connectors import dataset_csv_source_names, poll_connector
from backend.realtime_reviews import ingest_realtime_reviews


DEFAULT_SCHEDULER_CONFIG = {
    "enabled": True,
    "connector": "dataset_csv",
    "interval_seconds": 15,
    "limit": 1,
    "reset_cursor_on_start": False,
    "options": {
        "file_names": [
            "Alibaba.csv",
            "Aliexpress.csv",
            "Amazon shopping.csv",
            "Daraz Online Shopping App.csv",
            "eBay online shopping & selling.csv",
            "Flipkart.csv",
            "Lazada.csv",
            "Meesho.csv",
            "Myntra.csv",
            "Shein.csv",
            "Snapdeal.csv",
            "Walmart.csv",
        ],
    },
}

_scheduler_lock = threading.Lock()
_scheduler_thread: threading.Thread | None = None
_scheduler_started = False
_scheduler_runtime = {
    "is_running": False,
    "last_run_at": None,
    "last_success_at": None,
    "last_error": "",
    "last_ingested_rows": 0,
    "next_run_at": None,
    "last_source_file": "",
    "dataset_csv_rotation_index": 0,
}


def load_scheduler_config() -> dict:
    if not CONNECTOR_SCHEDULER_PATH.exists():
        return dict(DEFAULT_SCHEDULER_CONFIG)
    try:
        stored = json.loads(CONNECTOR_SCHEDULER_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(DEFAULT_SCHEDULER_CONFIG)
    config = dict(DEFAULT_SCHEDULER_CONFIG)
    config.update(stored if isinstance(stored, dict) else {})
    config["options"] = stored.get("options", config["options"]) if isinstance(stored, dict) else config["options"]
    return config


def save_scheduler_config(config: dict) -> dict:
    merged = dict(DEFAULT_SCHEDULER_CONFIG)
    merged.update(config or {})
    merged["interval_seconds"] = max(1, int(merged.get("interval_seconds", 15) or 15))
    merged["limit"] = max(1, min(int(merged.get("limit", 1) or 1), 100))
    merged["enabled"] = bool(merged.get("enabled"))
    merged["reset_cursor_on_start"] = bool(merged.get("reset_cursor_on_start"))
    merged["options"] = merged.get("options") if isinstance(merged.get("options"), dict) else {}
    CONNECTOR_SCHEDULER_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONNECTOR_SCHEDULER_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return merged


def scheduler_status() -> dict:
    config = load_scheduler_config()
    return {
        "config": config,
        "runtime": dict(_scheduler_runtime),
    }


def update_scheduler_config(config: dict) -> dict:
    updated = save_scheduler_config(config)
    _scheduler_runtime["last_error"] = ""
    return {
        "config": updated,
        "runtime": dict(_scheduler_runtime),
    }


def _timestamp_now() -> str:
    return datetime.now(UTC).isoformat()


def _resolve_scheduler_connector_options(config: dict) -> tuple[str, dict]:
    connector_name = str(config.get("connector", "")).strip()
    options = dict(config.get("options") or {})
    if connector_name != "dataset_csv":
        _scheduler_runtime["last_source_file"] = ""
        return connector_name, options

    configured_files = options.get("file_names")
    if isinstance(configured_files, list):
        file_names = [str(value).strip() for value in configured_files if str(value).strip()]
    elif options.get("all_files"):
        file_names = dataset_csv_source_names()
    else:
        file_names = []

    if not file_names:
        _scheduler_runtime["last_source_file"] = str(options.get("file_name", "")).strip()
        return connector_name, options

    rotation_index = int(_scheduler_runtime.get("dataset_csv_rotation_index", 0) or 0)
    selected = file_names[rotation_index % len(file_names)]
    _scheduler_runtime["dataset_csv_rotation_index"] = (rotation_index + 1) % len(file_names)
    _scheduler_runtime["last_source_file"] = selected
    resolved_options = dict(options)
    resolved_options["file_name"] = selected
    resolved_options.pop("file_names", None)
    resolved_options.pop("all_files", None)
    return connector_name, resolved_options


def _scheduler_loop() -> None:
    while True:
        config = load_scheduler_config()
        interval = max(1, int(config.get("interval_seconds", 15) or 15))

        if not config.get("enabled"):
            _scheduler_runtime["is_running"] = False
            _scheduler_runtime["next_run_at"] = None
            time.sleep(1.0)
            continue

        _scheduler_runtime["is_running"] = True
        _scheduler_runtime["next_run_at"] = datetime.fromtimestamp(time.time() + interval, tz=UTC).isoformat()
        try:
            connector_name, connector_options = _resolve_scheduler_connector_options(config)
            payload = poll_connector(
                connector_name,
                limit=int(config.get("limit", 1) or 1),
                options=connector_options,
                reset_cursor=bool(config.get("reset_cursor_on_start", False)),
            )
            reviews = payload.get("reviews", [])
            ingested_rows = 0
            if reviews:
                ingested_rows = int(len(ingest_realtime_reviews(reviews)))
            _scheduler_runtime["last_run_at"] = _timestamp_now()
            _scheduler_runtime["last_success_at"] = _scheduler_runtime["last_run_at"]
            _scheduler_runtime["last_error"] = ""
            _scheduler_runtime["last_ingested_rows"] = ingested_rows
        except Exception as error:  # pragma: no cover
            _scheduler_runtime["last_run_at"] = _timestamp_now()
            _scheduler_runtime["last_error"] = str(error)
            _scheduler_runtime["last_ingested_rows"] = 0
        finally:
            if config.get("reset_cursor_on_start"):
                save_scheduler_config({**config, "reset_cursor_on_start": False})
        time.sleep(interval)


def ensure_scheduler_started() -> None:
    global _scheduler_thread, _scheduler_started
    with _scheduler_lock:
        if _scheduler_started:
            return
        save_scheduler_config(load_scheduler_config())
        _scheduler_thread = threading.Thread(target=_scheduler_loop, name="connector-scheduler", daemon=True)
        _scheduler_thread.start()
        _scheduler_started = True
