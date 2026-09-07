/** SCR-003統計ページ: エラー種別集計の円グラフ（仕様書§6.4, FR-005）。 */
import type { ReactElement } from "react";
import { Doughnut } from "react-chartjs-2";

import { buildErrorBreakdownData } from "@/domain/stats/chart-data";
import type { ErrorBreakdownItemDto } from "@/lib/api-client";

import "./chart-setup";

export interface ErrorBreakdownChartProps {
  items: ErrorBreakdownItemDto[];
}

export function ErrorBreakdownChart({ items }: ErrorBreakdownChartProps): ReactElement {
  if (items.length === 0) {
    return <p className="text-sm text-slate-400">まだ統計データがありません</p>;
  }

  return (
    <Doughnut
      data={buildErrorBreakdownData(items)}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: { title: { display: true, text: "エラー種別集計" } },
      }}
    />
  );
}
