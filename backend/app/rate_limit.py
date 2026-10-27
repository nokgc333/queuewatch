from __future__ import annotations

import math
import os
import time
from collections import deque
from threading import Lock

from fastapi import HTTPException, Request, status

WINDOW_SECONDS = 60.0
DEFAULT_READ_PER_MINUTE = 300
DEFAULT_WRITE_PER_MINUTE = 60
READ_METHODS = {"GET", "HEAD", "OPTIONS"}
EXEMPT_PATHS = {"/healthz", "/health"}


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, key: str, limit: int, now: float | None = None) -> int:
        moment = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and moment - hits[0] >= WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, math.ceil(WINDOW_SECONDS - (moment - hits[0])))
            hits.append(moment)
            return 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_limiter = SlidingWindowLimiter()


def reset() -> None:
    _limiter.reset()


def _limit_from_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer, got '{raw}'") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer, got '{raw}'")
    return value


def load_limits() -> tuple[int, int]:
    return (
        _limit_from_env("QUEUEWATCH_RATE_LIMIT_READ_PER_MINUTE", DEFAULT_READ_PER_MINUTE),
        _limit_from_env("QUEUEWATCH_RATE_LIMIT_WRITE_PER_MINUTE", DEFAULT_WRITE_PER_MINUTE),
    )


def enforce_rate_limit(request: Request) -> None:
    if request.url.path in EXEMPT_PATHS:
        return
    read_limit, write_limit = load_limits()
    is_read = request.method in READ_METHODS
    client = request.client.host if request.client else "unknown"
    bucket = "read" if is_read else "write"
    retry_after = _limiter.check(f"{client}:{bucket}", read_limit if is_read else write_limit)
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": str(retry_after)},
        )
