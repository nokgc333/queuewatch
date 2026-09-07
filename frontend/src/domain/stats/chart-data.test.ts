/** domain/stats/chart-data.ts の単体テスト（Chart.js用データ整形の純粋関数、仕様書§6.4）。 */
import { describe, expect, it } from "vitest";

import {
  buildDurationHistogramData,
  buildErrorBreakdownData,
  buildUtilizationChartData,
} from "./chart-data";

describe("buildUtilizationChartData", () => {
  it("worker_nameをラベル、utilizationを百分率のデータ系列にする", () => {
    const result = buildUtilizationChartData([
      { worker_name: "celery@w1", utilization: 0.5 },
      { worker_name: "celery@w2", utilization: 0.9 },
    ]);

    expect(result.labels).toEqual(["celery@w1", "celery@w2"]);
    expect(result.datasets[0]?.data).toEqual([50, 90]);
  });

  it("空配列でも例外を投げない", () => {
    const result = buildUtilizationChartData([]);
    expect(result.labels).toEqual([]);
    expect(result.datasets[0]?.data).toEqual([]);
  });
});

describe("buildDurationHistogramData", () => {
  it("ビンの範囲をラベル、countをデータ系列にする", () => {
    const result = buildDurationHistogramData([
      { bin_start: 0, bin_end: 5, count: 3 },
      { bin_start: 5, bin_end: 10, count: 7 },
    ]);

    expect(result.labels).toEqual(["0.0–5.0s", "5.0–10.0s"]);
    expect(result.datasets[0]?.data).toEqual([3, 7]);
  });
});

describe("buildErrorBreakdownData", () => {
  it("エラーメッセージをラベル、countをデータ系列にする", () => {
    const result = buildErrorBreakdownData([
      { error_message: "Simulated render failure (license server timeout)", count: 4 },
      { error_message: "Other error", count: 1 },
    ]);

    expect(result.labels).toEqual([
      "Simulated render failure (license server timeout)",
      "Other error",
    ]);
    expect(result.datasets[0]?.data).toEqual([4, 1]);
  });

  it("空配列でも例外を投げない", () => {
    const result = buildErrorBreakdownData([]);
    expect(result.labels).toEqual([]);
  });
});
