"""domain/backoff.py の単体テスト（仕様書§8.1 指数バックオフの計算式）。

Celery自体のretry_backoff=Trueが実際のリトライ間隔を決定するため、
本テストはアプリケーションコード側で計算式を再現・検証する目的のみに使う
（アプリ層でリトライを実装しているわけではない点に注意、仕様書§8.1）。
"""

from __future__ import annotations

import pytest

from app.domain.backoff import calculate_backoff_delay


def test_first_retry_is_about_one_second() -> None:
    """TC相当: 0回目(初回リトライ前)は 2**0 * 1 = 1秒。"""
    assert calculate_backoff_delay(retries=0) == 1.0


def test_second_retry_is_about_two_seconds() -> None:
    assert calculate_backoff_delay(retries=1) == 2.0


def test_third_retry_is_about_four_seconds() -> None:
    assert calculate_backoff_delay(retries=2) == 4.0


def test_delay_is_capped_at_backoff_max() -> None:
    """大きなretries値でもbackoff_max(既定60秒)を超えない。"""
    assert calculate_backoff_delay(retries=10) == 60.0


def test_custom_backoff_max_is_respected() -> None:
    assert calculate_backoff_delay(retries=10, backoff_max=30.0) == 30.0


def test_custom_backoff_base_scales_delay() -> None:
    assert calculate_backoff_delay(retries=1, backoff_base=2.0) == 4.0


def test_negative_retries_raises_value_error() -> None:
    with pytest.raises(ValueError):
        calculate_backoff_delay(retries=-1)


def test_zero_backoff_max_returns_zero() -> None:
    assert calculate_backoff_delay(retries=0, backoff_max=0.0) == 0.0
