import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as apiClient from "@/lib/api-client";

vi.mock("react-chartjs-2", () => ({
  Bar: () => <div data-testid="bar-chart" />,
  Doughnut: () => <div data-testid="doughnut-chart" />,
}));
vi.mock("@/components/charts/chart-setup", () => ({}));

const { Stats } = await import("../Stats");

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Stats", () => {
  it("3種類の統計を取得してチャートを描画する", async () => {
    vi.spyOn(apiClient, "getUtilizationStats").mockResolvedValue([
      { worker_name: "celery@w1", utilization: 0.5 },
    ]);
    vi.spyOn(apiClient, "getDurationStats").mockResolvedValue([
      { bin_start: 0, bin_end: 5, count: 2 },
    ]);
    vi.spyOn(apiClient, "getErrorStats").mockResolvedValue([
      { error_message: "err", count: 1 },
    ]);

    render(<Stats />);

    expect(await screen.findAllByTestId("bar-chart")).toHaveLength(2);
    expect(await screen.findByTestId("doughnut-chart")).toBeInTheDocument();
  });

  it("すべて空の場合はempty状態メッセージを表示する", async () => {
    vi.spyOn(apiClient, "getUtilizationStats").mockResolvedValue([]);
    vi.spyOn(apiClient, "getDurationStats").mockResolvedValue([]);
    vi.spyOn(apiClient, "getErrorStats").mockResolvedValue([]);

    render(<Stats />);

    const messages = await screen.findAllByText("まだ統計データがありません");
    expect(messages.length).toBeGreaterThan(0);
  });
});
