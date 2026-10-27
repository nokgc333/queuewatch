"""リクエスト ID の付与、アクセスログ、HTTP メトリクスを、1 つの ASGI ミドルウェアで行う。"""

from __future__ import annotations

import logging
import re
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app import metrics
from app.logging_config import request_id_var

REQUEST_ID_HEADER = "X-Request-ID"
SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
UNLOGGED_PATHS = frozenset({"/healthz"})

access_logger = logging.getLogger("queuewatch.access")


def route_template(scope: Scope) -> str:
    """ルーターの接頭辞を含む、ルートのテンプレート(`/jobs/{job_id}`)。マッチしなければ unmatched。

    `scope["route"].path` は、`include_router` の接頭辞を含まないため、パスの中の
    パラメーターの値を、`{名前}` に置き換えて作る。
    """
    if scope.get("route") is None:
        return metrics.UNMATCHED_ROUTE
    template: str = scope["path"]
    for name, value in scope.get("path_params", {}).items():
        template = template.replace(f"/{value}", f"/{{{name}}}", 1)
    return template


def _request_id_from(headers: Headers) -> str:
    candidate = headers.get(REQUEST_ID_HEADER, "")
    return candidate if SAFE_REQUEST_ID.match(candidate) else uuid.uuid4().hex


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = _request_id_from(Headers(scope=scope))
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            elapsed = time.perf_counter() - started
            template = route_template(scope)
            path = scope["path"]
            if path != "/metrics":
                metrics.observe_request(scope["method"], template, status, elapsed)
            if path not in UNLOGGED_PATHS:
                access_logger.info(
                    "request",
                    extra={
                        "method": scope["method"],
                        "path": path,
                        "status": status,
                        "duration_ms": round(elapsed * 1000, 2),
                        "request_id": request_id,
                    },
                )
            request_id_var.reset(token)
