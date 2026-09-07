"""domain/stats.py の単体テスト（仕様書§8.3、TC-016〜017相当）。"""

from __future__ import annotations

from app.domain.stats import calculate_duration_histogram, calculate_utilization


class TestCalculateUtilization:
    def test_half_busy_returns_point_five(self) -> None:
        assert calculate_utilization(total_busy_seconds=30.0, window_seconds=60.0) == 0.5

    def test_fully_busy_returns_one(self) -> None:
        assert calculate_utilization(total_busy_seconds=60.0, window_seconds=60.0) == 1.0

    def test_busy_exceeding_window_is_capped_at_one(self) -> None:
        """複数ワーカーの合算等でbusy時間がwindowを超えるケースも1.0に丸める。"""
        assert calculate_utilization(total_busy_seconds=90.0, window_seconds=60.0) == 1.0

    def test_zero_window_seconds_returns_zero(self) -> None:
        assert calculate_utilization(total_busy_seconds=10.0, window_seconds=0.0) == 0.0

    def test_negative_window_seconds_returns_zero(self) -> None:
        assert calculate_utilization(total_busy_seconds=10.0, window_seconds=-5.0) == 0.0

    def test_zero_busy_seconds_returns_zero(self) -> None:
        assert calculate_utilization(total_busy_seconds=0.0, window_seconds=60.0) == 0.0


class TestCalculateDurationHistogram:
    def test_empty_durations_returns_empty_list(self) -> None:
        assert calculate_duration_histogram([]) == []

    def test_single_value_repeated_creates_uniform_bin_width_of_one(self) -> None:
        """min==maxの場合、bin_widthは1.0のフォールバックを使う。"""
        bins = calculate_duration_histogram([5.0, 5.0, 5.0], bin_count=2)
        assert len(bins) == 2
        assert bins[0][0] == 5.0
        total_count = sum(count for _, _, count in bins)
        assert total_count == 3

    def test_distributes_values_across_bins(self) -> None:
        durations = [1.0, 2.0, 3.0, 4.0, 5.0]
        bins = calculate_duration_histogram(durations, bin_count=5)
        assert len(bins) == 5
        total_count = sum(count for _, _, count in bins)
        assert total_count == len(durations)

    def test_max_value_falls_into_last_bin(self) -> None:
        durations = [0.0, 10.0]
        bins = calculate_duration_histogram(durations, bin_count=10)
        assert bins[-1][2] == 1

    def test_default_bin_count_is_ten(self) -> None:
        bins = calculate_duration_histogram([1.0, 2.0, 3.0])
        assert len(bins) == 10
