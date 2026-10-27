"""QueueWatch APIエントリポイント（仕様書§5.3参照）。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app import rate_limit
from app.auth import load_auth_settings
from app.body_limit import BodyLimitMiddleware
from app.cors import load_allowed_origins
from app.database import Base, engine
from app.errors import problem_details_handler
from app.logging_config import configure_logging
from app.routers import jobs, stats, workers

configure_logging()

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    load_auth_settings()
    rate_limit.load_limits()
    load_allowed_origins()
    yield


app = FastAPI(
    title="QueueWatch API",
    version="0.1.0",
    lifespan=lifespan,
    dependencies=[Depends(rate_limit.enforce_rate_limit)],
)

app.add_exception_handler(HTTPException, problem_details_handler)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """最小限のセキュリティヘッダーを付与する（仕様書§9.3参照）。"""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(BodyLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=load_allowed_origins(),
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
)

app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(workers.router, prefix="/workers", tags=["workers"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """ヘルスチェック（Redis接続確認を含む、仕様書§5.2参照）。"""
    from app.worker import celery_app

    try:
        conn = celery_app.broker_connection()
        conn.ensure_connection(max_retries=1)
        redis_status = "ok"
    except Exception:
        redis_status = "unreachable"
    return {"status": "ok", "redis": redis_status}
