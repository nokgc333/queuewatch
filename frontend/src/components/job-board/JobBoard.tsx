/** SCR-001ダッシュボードのジョブボード本体（仕様書§6.2）。 */
import type { ReactElement } from "react";

import { groupJobsByStatus, type Job } from "@/domain/status/status";

import { JobColumn } from "./JobColumn";

export interface JobBoardProps {
  jobs: Job[];
  isLoading?: boolean;
  onJobClick?: (jobId: number) => void;
  onCreateJob?: () => void;
}

export function JobBoard({
  jobs,
  isLoading = false,
  onJobClick,
  onCreateJob,
}: JobBoardProps): ReactElement {
  const grouped = groupJobsByStatus(jobs);
  const doneJobs = [...grouped.success, ...grouped.dead];
  const heldJobs = [...grouped.paused, ...grouped.cancelled];

  if (!isLoading && jobs.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-slate-300 py-16 text-center">
        <p className="text-slate-600">まだジョブがありません</p>
        {onCreateJob && (
          <button
            type="button"
            onClick={onCreateJob}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            + 新規ジョブ
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {onCreateJob && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onCreateJob}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            + 新規ジョブ
          </button>
        </div>
      )}
      <div className="flex gap-3 overflow-x-auto">
        <JobColumn
          title="待機中"
          jobs={grouped.pending}
          isLoading={isLoading}
          onJobClick={onJobClick}
        />
        <JobColumn
          title="処理中"
          jobs={grouped.running}
          isLoading={isLoading}
          onJobClick={onJobClick}
        />
        <JobColumn
          title="リトライ中"
          jobs={grouped.retrying}
          isLoading={isLoading}
          onJobClick={onJobClick}
        />
        <JobColumn
          title="完了"
          jobs={doneJobs}
          isLoading={isLoading}
          onJobClick={onJobClick}
        />
        <JobColumn
          title="保留・中止"
          jobs={heldJobs}
          isLoading={isLoading}
          onJobClick={onJobClick}
        />
      </div>
    </div>
  );
}
