/** SCR-004: デッドレターキュービュー（仕様書§6.5、Could優先度FR-010はv1スコープ外）。 */
import { useCallback, type ReactElement } from "react";

import { listJobs } from "@/lib/api-client";
import { API_BASE_URL, POLLING_INTERVAL_MS } from "@/lib/config";
import { usePolling } from "@/lib/polling";

export function DeadLetterQueue(): ReactElement {
  const fetchDeadJobs = useCallback(() => listJobs(API_BASE_URL, { status: "dead" }), []);
  const { data, isLoading } = usePolling(fetchDeadJobs, POLLING_INTERVAL_MS);
  const jobs = data ?? [];

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1 className="text-lg font-semibold text-slate-900">デッドレターキュー</h1>
      <p className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
        手動再投入機能はv1では未対応です。原因調査後、必要であれば同名で再度POST
        /jobsしてください。
      </p>
      {!isLoading && jobs.length === 0 && (
        <p className="text-sm text-slate-400">デッドレターキューにジョブはありません。</p>
      )}
      <ul className="flex flex-col gap-2">
        {jobs.map((job) => (
          <li
            key={job.id}
            className="rounded border border-red-200 bg-red-50 p-3 text-sm"
          >
            <div className="font-medium text-slate-900">{job.name}</div>
            {job.error_message && (
              <div className="mt-1 text-red-700">{job.error_message}</div>
            )}
            {job.finished_at && (
              <div className="mt-1 text-xs text-slate-500">失敗日時: {job.finished_at}</div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
