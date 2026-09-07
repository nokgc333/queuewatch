"""優先度からCeleryキュー名へのマッピングを純粋関数として切り出す
(PipeBoardのdomain分離パターンを踏襲、仕様書§8.2)。

Celery自体には厳密な優先度スケジューリング機構が限定的にしか
存在しないため(ブローカーによって対応状況が異なる)、本プロジェクトでは
優先度ごとに物理的に異なるキューを用意し、ワーカー起動時にキュー名を
優先度順(queue_high, queue_normal, queue_lowの順)で指定することで、
Celeryのタスク消費順序が概ね優先度順に近づく設計とした
(疑似的な優先度制御、要件定義書ADR-0004)。

既知の限界: この設計はワーカーが単一プロセスでキューを順番にポーリングする
場合に限り優先度順に近い挙動を示すが、複数ワーカープロセスが並行して
異なるキューを消費する場合、真の意味でのグローバルな優先度順序は保証されない。
"""

from __future__ import annotations

PRIORITY_QUEUE_MAP: dict[str, str] = {
    "high": "queue_high",
    "normal": "queue_normal",
    "low": "queue_low",
}

VALID_PRIORITIES = frozenset(PRIORITY_QUEUE_MAP.keys())


def resolve_queue_name(priority: str) -> str:
    """優先度文字列に対応するCeleryキュー名を返す。未定義の優先度はValueError。"""
    if priority not in PRIORITY_QUEUE_MAP:
        raise ValueError(f"Invalid priority: {priority}")
    return PRIORITY_QUEUE_MAP[priority]
