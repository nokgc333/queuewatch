/** SCR-001ダッシュボードのワーカー稼働状況パネル（仕様書§6.2, FR-003）。 */
import type { ReactElement } from "react";

import type { WorkerStatusDto } from "@/lib/api-client";

const BUSY_THRESHOLD = 0.3;

export interface WorkerStatusPanelProps {
  workers: WorkerStatusDto[];
}

export function WorkerStatusPanel({ workers }: WorkerStatusPanelProps): ReactElement {
  if (workers.length === 0) {
    return (
      <aside className="w-64 shrink-0 rounded-lg bg-slate-50 p-3">
        <h2 className="mb-2 text-sm font-semibold text-slate-700">ワーカー</h2>
        <p className="text-xs text-slate-400">ワーカー情報がありません</p>
      </aside>
    );
  }

  return (
    <aside className="w-64 shrink-0 rounded-lg bg-slate-50 p-3">
      <h2 className="mb-2 text-sm font-semibold text-slate-700">ワーカー</h2>
      <ul className="flex flex-col gap-2">
        {workers.map((worker) => {
          const busyState = worker.utilization >= BUSY_THRESHOLD ? "busy" : "idle";
          return (
            <li
              key={worker.worker_name}
              aria-label={`${worker.worker_name} ${busyState}`}
              className="rounded border border-slate-200 bg-white p-2 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-800">{worker.worker_name}</span>
                <span
                  className={
                    busyState === "busy"
                      ? "rounded bg-blue-100 px-1.5 py-0.5 text-blue-700"
                      : "rounded bg-slate-100 px-1.5 py-0.5 text-slate-500"
                  }
                >
                  {busyState}
                </span>
              </div>
              <div className="mt-1 text-slate-500">
                処理: {worker.processed_count} / 失敗: {worker.failed_count}
              </div>
              <div className="mt-1 font-medium text-slate-700">
                {Math.round(worker.utilization * 100)}%
              </div>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
