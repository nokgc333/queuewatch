/**
 * 統計APIレスポンスをChart.js用データ形式に整形する純粋関数（仕様書§6.4）。
 * コンポーネント側はこの結果をそのままBar/Doughnutへ渡すだけの薄いラッパーにする。
 */
import type {
  DurationBinDto,
  ErrorBreakdownItemDto,
  UtilizationStatDto,
} from "@/lib/api-client";

export interface SimpleChartData {
  labels: string[];
  datasets: [{ label: string; data: number[]; backgroundColor: string | string[] }];
}

const UTILIZATION_COLOR = "#2563eb";
const DURATION_COLOR = "#7c3aed";
const ERROR_PALETTE = ["#dc2626", "#ea580c", "#d97706", "#65a30d", "#0891b2", "#7c3aed"];

export function buildUtilizationChartData(stats: UtilizationStatDto[]): SimpleChartData {
  return {
    labels: stats.map((s) => s.worker_name),
    datasets: [
      {
        label: "稼働率 (%)",
        data: stats.map((s) => Math.round(s.utilization * 100)),
        backgroundColor: UTILIZATION_COLOR,
      },
    ],
  };
}

export function buildDurationHistogramData(bins: DurationBinDto[]): SimpleChartData {
  return {
    labels: bins.map((bin) => `${bin.bin_start.toFixed(1)}–${bin.bin_end.toFixed(1)}s`),
    datasets: [
      {
        label: "処理時間分布 (件数)",
        data: bins.map((bin) => bin.count),
        backgroundColor: DURATION_COLOR,
      },
    ],
  };
}

export function buildErrorBreakdownData(items: ErrorBreakdownItemDto[]): SimpleChartData {
  return {
    labels: items.map((item) => item.error_message),
    datasets: [
      {
        label: "エラー件数",
        data: items.map((item) => item.count),
        backgroundColor: items.map((_, i) => ERROR_PALETTE[i % ERROR_PALETTE.length] as string),
      },
    ],
  };
}
