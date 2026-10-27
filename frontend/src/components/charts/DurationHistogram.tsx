/** SCR-003統計ページ: 処理時間分布のヒストグラム（仕様書§6.4）。 */
import type { ReactElement } from "react";
import { Bar } from "react-chartjs-2";

import { buildDurationHistogramData } from "@/domain/stats/chart-data";
import type { DurationBinDto } from "@/lib/api-client";

import "./chart-setup";

export interface DurationHistogramProps {
  bins: DurationBinDto[];
}

export function DurationHistogram({ bins }: DurationHistogramProps): ReactElement {
  if (bins.length === 0 || bins.every((bin) => bin.count === 0)) {
    return <p className="text-sm text-slate-600">まだ統計データがありません</p>;
  }

  return (
    <Bar
      data={buildDurationHistogramData(bins)}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          title: { display: true, text: "処理時間分布" },
        },
        scales: { y: { beginAtZero: true } },
      }}
    />
  );
}
