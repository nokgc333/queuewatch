/** components/charts の単体テスト。Chart.jsのcanvas描画はhappy-domで不安定なため
 * react-chartjs-2自体をモックし、正しいpropsで呼ばれることのみ検証する。
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("react-chartjs-2", () => ({
  Bar: (props: { data: { labels: string[] } }) => (
    <div data-testid="bar-chart">{JSON.stringify(props.data.labels)}</div>
  ),
  Doughnut: (props: { data: { labels: string[] } }) => (
    <div data-testid="doughnut-chart">{JSON.stringify(props.data.labels)}</div>
  ),
}));

vi.mock("../chart-setup", () => ({}));

const { UtilizationChart } = await import("../UtilizationChart");
const { DurationHistogram } = await import("../DurationHistogram");
const { ErrorBreakdownChart } = await import("../ErrorBreakdownChart");

describe("UtilizationChart", () => {
  it("statsが空の場合はempty表示", () => {
    render(<UtilizationChart stats={[]} />);
    expect(screen.getByText("まだ統計データがありません")).toBeInTheDocument();
  });

  it("statsがある場合はBarチャートを描画する", () => {
    render(<UtilizationChart stats={[{ worker_name: "celery@w1", utilization: 0.5 }]} />);
    expect(screen.getByTestId("bar-chart")).toHaveTextContent("celery@w1");
  });
});

describe("DurationHistogram", () => {
  it("全ビンが0件の場合はempty表示", () => {
    render(<DurationHistogram bins={[{ bin_start: 0, bin_end: 1, count: 0 }]} />);
    expect(screen.getByText("まだ統計データがありません")).toBeInTheDocument();
  });

  it("データがある場合はBarチャートを描画する", () => {
    render(<DurationHistogram bins={[{ bin_start: 0, bin_end: 5, count: 3 }]} />);
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });
});

describe("ErrorBreakdownChart", () => {
  it("itemsが空の場合はempty表示", () => {
    render(<ErrorBreakdownChart items={[]} />);
    expect(screen.getByText("まだ統計データがありません")).toBeInTheDocument();
  });

  it("itemsがある場合はDoughnutチャートを描画する", () => {
    render(<ErrorBreakdownChart items={[{ error_message: "err", count: 1 }]} />);
    expect(screen.getByTestId("doughnut-chart")).toHaveTextContent("err");
  });
});
