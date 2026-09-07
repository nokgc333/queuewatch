"""domain/priority_queue.py の単体テスト（仕様書§8.2）。"""

from __future__ import annotations

import pytest

from app.domain.priority_queue import (
    VALID_PRIORITIES,
    resolve_queue_name,
)


def test_resolve_queue_name_maps_high_priority() -> None:
    assert resolve_queue_name("high") == "queue_high"


def test_resolve_queue_name_maps_normal_priority() -> None:
    assert resolve_queue_name("normal") == "queue_normal"


def test_resolve_queue_name_maps_low_priority() -> None:
    assert resolve_queue_name("low") == "queue_low"


def test_resolve_queue_name_rejects_unknown_priority() -> None:
    with pytest.raises(ValueError):
        resolve_queue_name("urgent")


def test_resolve_queue_name_rejects_empty_string() -> None:
    with pytest.raises(ValueError):
        resolve_queue_name("")


def test_valid_priorities_contains_exactly_three_levels() -> None:
    assert VALID_PRIORITIES == frozenset({"high", "normal", "low"})
