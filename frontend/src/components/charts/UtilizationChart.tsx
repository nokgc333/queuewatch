/** SCR-003統計ページ: ワーカー稼働率の棒グラフ（仕様書§6.4）。 */
import type { ReactElement } from "react";
import { Bar } from "react-chartjs-2";

import { buildUtilizationChartData } from "@/domain/stats/chart-data";
import type { UtilizationStatDto } from "@/lib/api-client";

import "./chart-setup";

export interface UtilizationChartProps {
  stats: UtilizationStatDto[];
}

export function UtilizationChart({ stats }: UtilizationChartProps): ReactElement {
  if (stats.length === 0) {
    return <p className="text-sm text-slate-600">まだ統計データがありません</p>;
  }

  return (
    <Bar
      data={buildUtilizationChartData(stats)}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, title: { display: true, text: "ワーカー稼働率" } },
        scales: { y: { beginAtZero: true, max: 100 } },
      }}
    />
  );
}
