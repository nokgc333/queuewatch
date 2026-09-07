/** SCR-001: ダッシュボード（ジョブボード + ワーカーパネル、仕様書§6.2）。 */
import { useCallback, useState, type ReactElement } from "react";
import { useNavigate } from "react-router-dom";

import { JobBoard } from "@/components/job-board/JobBoard";
import { NewJobModal } from "@/components/job-board/NewJobModal";
import { WorkerStatusPanel } from "@/components/worker-panel/WorkerStatusPanel";
import type { Priority } from "@/domain/job/priority";
import { createJob, getWorkerStatus, listJobs } from "@/lib/api-client";
import { API_BASE_URL, POLLING_INTERVAL_MS } from "@/lib/config";
import { usePolling } from "@/lib/polling";

export function Dashboard(): ReactElement {
  const navigate = useNavigate();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchJobs = useCallback(() => listJobs(API_BASE_URL), []);
  const fetchWorkers = useCallback(() => getWorkerStatus(API_BASE_URL), []);

  const jobsState = usePolling(fetchJobs, POLLING_INTERVAL_MS);
  const workersState = usePolling(fetchWorkers, POLLING_INTERVAL_MS);

  const handleCreateJob = async (payload: { name: string; priority: Priority }): Promise<void> => {
    await createJob(API_BASE_URL, payload);
    setIsModalOpen(false);
  };

  const hasError = jobsState.error !== null || workersState.error !== null;
  const jobs = jobsState.data ?? [];
  const workers = workersState.data ?? [];

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1 className="text-lg font-semibold text-slate-900">ダッシュボード</h1>
      {hasError && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          最新データの取得に失敗しました。直近の表示を保持しています。
        </div>
      )}
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
