"""OpenAPI から、API の一覧(メソッド・パス・必要なロール・概要)の Markdown を作る。"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.routing import APIRoute

from app.auth import Role
from app.main import ROUTERS, app

METHOD_ORDER = {"GET": 0, "POST": 1, "PUT": 2, "PATCH": 3, "DELETE": 4}
PUBLIC_PATHS = {"/healthz"}


def _role_of(route: APIRoute, prefix: str) -> str:
    if prefix + route.path in PUBLIC_PATHS:
        return "なし"
    needed = Role.VIEWER
    for dependency in route.dependencies:
        closure = getattr(dependency.dependency, "__closure__", None) or ()
        for cell in closure:
            if isinstance(cell.cell_contents, Role):
                needed = max(needed, cell.cell_contents)
    return needed.name.lower()


def _summary_of(route: APIRoute) -> str:
    return (route.endpoint.__doc__ or route.name.replace("_", " ")).strip().splitlines()[0]


def api_markdown() -> str:
    rows: list[tuple[str, str, str, str, str]] = []
    for router, prefix, tag in ROUTERS:
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            for method in sorted(route.methods or ()):
                rows.append(
                    (tag, prefix + route.path, method, _role_of(route, prefix), _summary_of(route))
                )
    for route in app.routes:
        if isinstance(route, APIRoute):
            role = "なし" if route.path in PUBLIC_PATHS else _role_of(route, "")
            for method in sorted(route.methods or ()):
                rows.append(("health", route.path, method, role, _summary_of(route)))
    rows.sort(key=lambda r: (r[0], r[1], METHOD_ORDER.get(r[2], 9)))

    lines = [
        "# API 一覧",
        "",
        "`python -m app.export_api_doc ../docs/api.md` で、実際の API から生成する(手で編集しない。",
        "テストが、実際の API と一致していることを確かめる)。完全な定義は、起動中の `/docs`(Swagger UI)と",
        "`frontend/openapi.json` にある。",
        "",
        "ロールは、必要な最小の権限。`token` モードで、未認証は 401、権限不足は 403。",
        "`local` モードでは、すべて管理者として扱う。",
        "",
    ]
    current_tag = ""
    for tag, path, method, role, summary in rows:
        if tag != current_tag:
            current_tag = tag
            lines += [
                "",
                f"## {tag}",
                "",
                "| メソッド | パス | ロール | 概要 |",
                "| --- | --- | --- | --- |",
            ]
        lines.append(f"| {method} | `{path}` | {role} | {summary} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m app.export_api_doc <output.md>", file=sys.stderr)
        return 2
    Path(argv[1]).write_text(api_markdown(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
