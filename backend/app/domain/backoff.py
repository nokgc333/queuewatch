"""指数バックオフ計算の純粋関数（仕様書§8.1 business-logic参照）。

Celeryの`retry_backoff=True`が実際のリトライ間隔決定を担うため、本モジュールは
アプリケーションコード側でリトライ処理を再実装するものではない。あくまで
Celery公式実装の計算式(`delay = min(backoff_max, (2 ** retries) * backoff_base)`)を
純粋関数として切り出し、フロントエンドへの「次回リトライ予定時刻」表示や
テストによる計算式そのものの検証に用いる（要件定義書§16.6 Q6と対応）。
"""

from __future__ import annotations

DEFAULT_BACKOFF_BASE = 1.0
DEFAULT_BACKOFF_MAX = 60.0


def calculate_backoff_delay(
    retries: int,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
    backoff_max: float = DEFAULT_BACKOFF_MAX,
) -> float:
    """リトライ回数からバックオフ待機時間(秒)を計算する。

    delay = min(backoff_max, (2 ** retries) * backoff_base)

    Args:
        retries: これまでのリトライ試行回数(0始まり)。
        backoff_base: バックオフの基準秒数(Celeryの既定は1秒相当)。
        backoff_max: バックオフ間隔の上限秒数。

    Raises:
        ValueError: retriesが負数の場合。
    """
    if retries < 0:
        raise ValueError(f"retries must be >= 0, got {retries}")
    delay = float(2**retries) * backoff_base
    return min(backoff_max, delay)
