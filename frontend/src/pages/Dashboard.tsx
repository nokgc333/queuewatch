/** SCR-001: ダッシュボード（ジョブボード + ワーカーパネル、仕様書§6.2）。 */
import { useCallback, useState, type ReactElement } from "react";
import { useLocation } from "wouter";

import { JobBoard } from "@/components/job-board/JobBoard";
import { JobFilters, type JobFilterValue } from "@/components/job-board/JobFilters";
import { NewJobModal } from "@/components/job-board/NewJobModal";
import { WorkerStatusPanel } from "@/components/worker-panel/WorkerStatusPanel";
import type { Priority } from "@/domain/job/priority";
import { createJob, getWorkerStatus, listJobsPage } from "@/lib/api-client";
import { API_BASE_URL, POLLING_INTERVAL_MS } from "@/lib/config";
import { usePolling } from "@/lib/polling";

const PAGE_SIZE = 100;

export function Dashboard(): ReactElement {
  const [, navigate] = useLocation();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const [filter, setFilter] = useState<JobFilterValue>({ q: "", priority: "" });
  const [limit, setLimit] = useState(PAGE_SIZE);

  const fetchJobs = useCallback(
    () =>
      listJobsPage(API_BASE_URL, {
        q: filter.q.trim() || undefined,
        priority: filter.priority || undefined,
        limit,
      }),
    [filter, limit],
  );
  const fetchWorkers = useCallback(() => getWorkerStatus(API_BASE_URL), []);

  const jobsState = usePolling(
    fetchJobs,
    POLLING_INTERVAL_MS,
    `${filter.q.trim()}|${filter.priority}|${limit}`,
  );
  const workersState = usePolling(fetchWorkers, POLLING_INTERVAL_MS);

  const handleCreateJob = async (payload: { name: string; priority: Priority }): Promise<void> => {
    await createJob(API_BASE_URL, payload);
    setIsModalOpen(false);
  };

  const hasError = jobsState.error !== null || workersState.error !== null;
  const jobs = jobsState.data?.jobs ?? [];
  const total = jobsState.data?.total ?? 0;
  const workers = workersState.data ?? [];

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1 className="text-lg font-semibold text-slate-900">ダッシュボード</h1>
      {hasError && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          最新データの取得に失敗しました。直近の表示を保持しています。
        </div>
      )}
      <JobFilters
        value={filter}
        onChange={(next) => {
          setFilter(next);
          setLimit(PAGE_SIZE);
        }}
      />
      <div className="flex gap-4">
        <div className="flex-1">
          <JobBoard
            jobs={jobs}
            isLoading={jobsState.isLoading}
            onJobClick={(jobId) => navigate(`/jobs/${jobId}`)}
            onCreateJob={() => setIsModalOpen(true)}
          />
        </div>
        <WorkerStatusPanel workers={workers} />
      </div>
      <p className="text-sm text-slate-700" role="status" aria-live="polite">
        {total}件中 {jobs.length}件を表示
        {jobs.length < total && (
          <button
            type="button"
            onClick={() => setLimit((current) => current + PAGE_SIZE)}
            className="ml-3 rounded border border-slate-400 px-2 py-0.5 text-sm hover:bg-slate-50"
          >
            さらに表示
          </button>
        )}
      </p>
      {isModalOpen && (
        <NewJobModal
          onSubmit={(payload) => {
            void handleCreateJob(payload);
          }}
          onClose={() => setIsModalOpen(false)}
        />
      )}
    </div>
  );
}
