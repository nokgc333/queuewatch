"""ジョブの操作(キャンセル・一時停止・再開・再投入)で、どの状態からどの状態へ進めるか。

実行中(running)のジョブは、Celery のタスクを安全に止める手段が無いため、どの操作も受け付けない。
"""

from __future__ import annotations

ACTIONS: dict[str, tuple[frozenset[str], str]] = {
    "cancel": (frozenset({"pending", "retrying", "paused"}), "cancelled"),
    "pause": (frozenset({"pending", "retrying"}), "paused"),
    "resume": (frozenset({"paused"}), "pending"),
    "requeue": (frozenset({"dead", "cancelled"}), "pending"),
}

SKIPPED_BY_WORKERS = frozenset({"cancelled", "paused"})


def next_status(action: str, current: str) -> str | None:
    """操作で進める先の状態。その状態からは操作できないとき(未知の操作を含む)は None。"""
    rule = ACTIONS.get(action)
    if rule is None:
        return None
    allowed_from, target = rule
    return target if current in allowed_from else None
