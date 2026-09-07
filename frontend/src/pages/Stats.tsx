/** SCR-003: 統計ページ（稼働率・処理時間分布・エラー種別、仕様書§6.4）。 */
import { useCallback, type ReactElement } from "react";

import { DurationHistogram } from "@/components/charts/DurationHistogram";
import { ErrorBreakdownChart } from "@/components/charts/ErrorBreakdownChart";
import { UtilizationChart } from "@/components/charts/UtilizationChart";
import { getDurationStats, getErrorStats, getUtilizationStats } from "@/lib/api-client";
import { API_BASE_URL, POLLING_INTERVAL_MS } from "@/lib/config";
import { usePolling } from "@/lib/polling";

export function Stats(): ReactElement {
  const fetchUtilization = useCallback(() => getUtilizationStats(API_BASE_URL), []);
  const fetchDuration = useCallback(() => getDurationStats(API_BASE_URL), []);
  const fetchErrors = useCallback(() => getErrorStats(API_BASE_URL), []);

  const utilization = usePolling(fetchUtilization, POLLING_INTERVAL_MS);
  const duration = usePolling(fetchDuration, POLLING_INTERVAL_MS);
  const errors = usePolling(fetchErrors, POLLING_INTERVAL_MS);

  return (
    <div className="flex flex-col gap-6 p-4">
      <h1 className="text-lg font-semibold text-slate-900">統計</h1>
      <section>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">ワーカー稼働率</h2>
        <UtilizationChart stats={utilization.data ?? []} />
      </section>
      <section>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">処理時間分布</h2>
        <DurationHistogram bins={duration.data ?? []} />
      </section>
      <section>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">エラー種別集計</h2>
        <ErrorBreakdownChart items={errors.data ?? []} />
      </section>
    </div>
  );
}
