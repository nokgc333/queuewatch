"""リクエスト本文の大きさの上限(ジョブ投入などの JSON は小さいので、大きな本文は受け付けない)。"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

MAX_BODY_BYTES = 16 * 1024
BODY_METHODS = {"POST", "PUT", "PATCH"}


def _problem(status: int, title: str) -> Response:
    return JSONResponse(
        {"type": f"https://queuewatch.local/probs/{status}", "title": title, "status": status},
        status_code=status,
        media_type="application/problem+json",
    )


class BodyLimitMiddleware:
    """本文を持つメソッドは、Content-Length が必須で、上限以下であること(411 / 413)。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in BODY_METHODS:
            await self.app(scope, receive, send)
            return
        length = Request(scope).headers.get("content-length")
        problem: Response | None = None
        if length is None:
            problem = _problem(411, "Content-Length is required")
        elif not length.isdigit():
            problem = _problem(400, "Invalid Content-Length")
        elif int(length) > MAX_BODY_BYTES:
            problem = _problem(413, f"Request body too large (max {MAX_BODY_BYTES} bytes)")
        if problem is not None:
            await problem(scope, receive, send)
            return
        await self.app(scope, receive, send)
