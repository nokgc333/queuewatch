#!/usr/bin/env python
"""houdini_submit_job.py

Houdini同梱PythonのPython Shell（またはhython）から実行し、
指定したレンダージョブをQueueWatch APIに投入するスクリプト（FR-007）。

hou には一切依存しない（このファイル自体はHoudini専用の処理を持たず、
どのPython環境からでも実行できる）。そのため、CIのpytestでHTTP呼び出し
ロジックを直接検証できる（仕様書§12.5、PipeBoardのhoudini_status_update.py
と同一設計思想）。session を注入可能にすることで実ネットワーク呼び出し
なしにpytestで検証できる。

Usage（Houdini Python Shell内）:
    import sys
    sys.path.append("/path/to/queuewatch/scripts")
    from houdini_submit_job import submit_job
    submit_job("http://localhost:8000", "SHOT010_render", "high")

Usage（CLI）:
    python houdini_submit_job.py --name "SHOT010_render" --priority high
    python houdini_submit_job.py --name "SHOT010_render" --priority high \\
        --api-base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Protocol

import requests

DEFAULT_API_BASE_URL = "http://localhost:8000"
TIMEOUT_SECONDS = 5
VALID_PRIORITIES = {"high", "normal", "low"}


class _HttpSession(Protocol):
    def post(self, url: str, json: dict[str, Any], timeout: int) -> Any: ...


def build_jobs_url(api_base_url: str) -> str:
    """`POST /jobs`エンドポイントのURLを組み立てる。"""
    return f"{api_base_url.rstrip('/')}/jobs"


def submit_job(
    api_base_url: str,
    name: str,
    priority: str = "normal",
    session: _HttpSession | None = None,
) -> dict[str, Any]:
    """指定した名前・優先度でジョブをPOST /jobs経由で登録する。

    Args:
        api_base_url: QueueWatchバックエンドのベースURL。
        name: ジョブ名（例: "SHOT010_render"）。
        priority: high/normal/lowのいずれか。
        session: HTTPセッション互換オブジェクト。未指定時はrequestsモジュールを使う
            (テストからモックを注入可能にするための設計、仕様書§12.5)。

    Raises:
        ValueError: priorityが未定義の値の場合（バックエンドへ問い合わせる前に検知する）。
        Exception: HTTPエラー応答時（session.raise_for_status()が送出する例外をそのまま伝播）。
    """
    if priority not in VALID_PRIORITIES:
        raise ValueError(
            f"Invalid priority: {priority!r} (expected one of {sorted(VALID_PRIORITIES)})"
        )

    http = session or requests
    url = build_jobs_url(api_base_url)
    response = http.post(
        url, json={"name": name, "priority": priority}, timeout=TIMEOUT_SECONDS
    )
    response.raise_for_status()
    result: dict[str, Any] = response.json()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Submit a render job to QueueWatch from Houdini."
    )
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--priority", default="normal", choices=sorted(VALID_PRIORITIES)
    )
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    args = parser.parse_args()

    try:
        result = submit_job(args.api_base_url, args.name, args.priority)
        print(
            f"Success: job '{args.name}' submitted (id={result['id']}, status={result['status']})"
        )
    except (
        Exception
    ) as exc:  # noqa: BLE001 - CLIエントリポイントとして意図的に広く捕捉する
        print(
            f"Error: could not submit job to {args.api_base_url}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
