"""RFC 9457 (Problem Details for HTTP APIs) 準拠のエラーレスポンス統一（仕様書§5.4）。"""

from __future__ import annotations

from typing import cast

from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse


async def problem_details_handler(request: Request, exc: Exception) -> JSONResponse:
    """FastAPIのadd_exception_handlerはHTTPException専用に登録するため、実行時は必ずHTTPException。"""
    exc = cast(HTTPException, exc)
    return JSONResponse(
        status_code=exc.status_code,
        media_type="application/problem+json",
        headers=exc.headers,
        content={
            "type": f"https://queuewatch.local/probs/{exc.status_code}",
            "title": exc.detail,
            "status": exc.status_code,
            "instance": str(request.url.path),
        },
    )
