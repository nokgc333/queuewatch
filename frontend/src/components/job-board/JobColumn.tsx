/** SCR-001ダッシュボードのステータス別カラム（仕様書§6.2）。 */
import type { ReactElement } from "react";

import type { Job } from "@/domain/status/status";

import { JobCard } from "./JobCard";

export interface JobColumnProps {
  title: string;
  jobs: Job[];
  emptyMessage?: string;
  isLoading?: boolean;
  onJobClick?: (jobId: number) => void;
}

const SKELETON_COUNT = 3;

export function JobColumn({
  title,
  jobs,
  emptyMessage = "ジョブがありません",
  isLoading = false,
  onJobClick,
}: JobColumnProps): ReactElement {
  return (
    <section className="flex min-w-64 flex-1 flex-col rounded-lg bg-slate-50 p-3">
      <header className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
        <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-600">
          {jobs.length}
        </span>
      </header>
      <div className="flex flex-col gap-2">
        {isLoading &&
          Array.from({ length: SKELETON_COUNT }).map((_, index) => (
            <div
              key={index}
              data-testid="job-card-skeleton"
              className="h-16 animate-pulse rounded-lg bg-slate-200"
            />
          ))}
        {!isLoading && jobs.length === 0 && (
          <p className="py-4 text-center text-xs text-slate-400">{emptyMessage}</p>
        )}
        {!isLoading &&
          jobs.map((job) => <JobCard key={job.id} job={job} onClick={onJobClick} />)}
      </div>
    </section>
  );
}
