from __future__ import annotations

import os

DEFAULT_ORIGIN = "http://localhost:5173"


def load_allowed_origins() -> list[str]:
    raw = os.environ.get("QUEUEWATCH_CORS_ORIGINS", "").strip()
    if not raw:
        return [DEFAULT_ORIGIN]
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if "*" in origins and len(origins) > 1:
        raise ValueError("QUEUEWATCH_CORS_ORIGINS must not mix '*' with specific origins")
    return origins
