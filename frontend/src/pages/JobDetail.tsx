/** SCR-002: ジョブ詳細（リトライ履歴、仕様書§6.3）。 */
import { useCallback, type ReactElement } from "react";
import { useParams } from "react-router-dom";

import { PRIORITY_LABELS } from "@/domain/job/priority";
import { STATUS_LABELS } from "@/domain/status/status";
import { ApiError, getJob } from "@/lib/api-client";
import { API_BASE_URL, POLLING_INTERVAL_MS } from "@/lib/config";
import { usePolling } from "@/lib/polling";

export function JobDetail(): ReactElement {
  const params = useParams<{ id: string }>();
  const jobId = Number(params.id);

  const fetchJob = useCallback(() => getJob(API_BASE_URL, jobId), [jobId]);
  const { data: job, error, isLoading } = usePolling(fetchJob, POLLING_INTERVAL_MS);

  if (error instanceof ApiError && error.status === 404) {
    return <p className="p-4 text-slate-600">ジョブが見つかりません（ID: {jobId}）。</p>;
  }

  if (isLoading && job === null) {
    return <p className="p-4 text-slate-400">読み込み中...</p>;
  }

  if (job === null) {
    return <p className="p-4 text-slate-600">ジョブが見つかりません（ID: {jobId}）。</p>;
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      <header className="flex flex-wrap items-center gap-2">
        <h1 className="text-lg font-semibold text-slate-900">{job.name}</h1>
        <span className="rounded bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700">
          {STATUS_LABELS[job.status]}
        </span>
        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
          優先度: {PRIORITY_LABELS[job.priority]}
        </span>
        <span className="text-xs text-slate-500">
          {job.retry_count} / {job.max_retries}
        </span>
      </header>

      {job.status === "dead" && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          このジョブはデッドレターキューに移動しました（最大リトライ回数に到達）。
        </div>
      )}

      <section>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">タイムライン</h2>
        <ol className="flex flex-col gap-1 text-xs text-slate-600">
          <li>登録: {job.created_at ?? "-"}</li>
          {job.started_at && <li>開始: {job.started_at}</li>}
          {job.retry_logs.map((log) => (
            <li key={log.id}>
              試行{log.attempt_number}: {log.status} ({log.attempted_at})
            </li>
          ))}
          {job.finished_at && <li>終了: {job.finished_at}</li>}
        </ol>
      </section>

      {job.error_message && (
        <section>
          <h2 className="mb-1 text-sm font-semibold text-slate-700">エラー詳細</h2>
          <p className="text-sm text-red-600">{job.error_message}</p>
        </section>
      )}
    </div>
  );
}
