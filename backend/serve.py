from __future__ import annotations

import os

from waitress import serve

from backend.app import app, start_background_services
from backend.config import resolve_runtime_server_settings


def resolve_waitress_threads(default: int = 4) -> int:
    raw_value = os.getenv("WAITRESS_THREADS", str(default)).strip()
    try:
        return max(1, int(raw_value))
    except ValueError:
        return default


def main() -> None:
    server_settings = resolve_runtime_server_settings()
    start_background_services(debug_enabled=False)
    serve(
        app,
        host=str(server_settings["host"]),
        port=int(server_settings["port"]),
        threads=resolve_waitress_threads(),
    )


if __name__ == "__main__":
    main()
