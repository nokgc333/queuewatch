"""稼働率・処理時間統計の集計を純粋関数として切り出す（仕様書§8.3）。

Python3エンジニア認定データ分析試験で学んだ基礎統計(平均・分散・
正規分布)の知見を、レンダーファーム運用の実務指標に接続する
(要件定義書§2.6-5)。
"""

from __future__ import annotations

DEFAULT_BIN_COUNT = 10


def calculate_utilization(total_busy_seconds: float, window_seconds: float) -> float:
    """稼働率(0.0〜1.0)を計算する。

    稼働率 = 集計ウィンドウ内でワーカーが実処理に費やした時間の合計
             ÷ 集計ウィンドウの全体時間
    """
    if window_seconds <= 0:
        return 0.0
    return min(1.0, total_busy_seconds / window_seconds)


def calculate_duration_histogram(
    durations: list[float], bin_count: int = DEFAULT_BIN_COUNT
) -> list[tuple[float, float, int]]:
    """処理時間のリストから(bin_start, bin_end, count)のヒストグラムを生成する。"""
    if not durations:
        return []
    min_d, max_d = min(durations), max(durations)
    bin_width = (max_d - min_d) / bin_count if max_d > min_d else 1.0
    bins = [(min_d + i * bin_width, min_d + (i + 1) * bin_width, 0) for i in range(bin_count)]
    for d in durations:
        idx = min(int((d - min_d) / bin_width), bin_count - 1) if bin_width > 0 else 0
        start, end, count = bins[idx]
        bins[idx] = (start, end, count + 1)
    return bins
