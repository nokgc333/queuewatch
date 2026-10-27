/** SCR-001ダッシュボードのジョブカード（仕様書§6.2）。 */
import type { ReactElement } from "react";

import { PRIORITY_LABELS } from "@/domain/job/priority";
import { STATUS_LABELS, type Job } from "@/domain/status/status";

const STATUS_BADGE_CLASSES: Record<Job["status"], string> = {
  pending: "bg-slate-200 text-slate-700",
  running: "bg-blue-200 text-blue-800",
  retrying: "bg-amber-200 text-amber-800",
  success: "bg-emerald-200 text-emerald-800",
  dead: "bg-red-200 text-red-800",
  paused: "bg-violet-200 text-violet-900",
  cancelled: "bg-slate-300 text-slate-800",
};

const PRIORITY_BADGE_CLASSES: Record<Job["priority"], string> = {
  high: "bg-red-100 text-red-700",
  normal: "bg-slate-100 text-slate-700",
  low: "bg-slate-100 text-slate-600",
};

export interface JobCardProps {
  job: Job;
  onClick?: (jobId: number) => void;
}

export function JobCard({ job, onClick }: JobCardProps): ReactElement {
  const statusLabel = STATUS_LABELS[job.status];
  const priorityLabel = PRIORITY_LABELS[job.priority];

  return (
    <button
      type="button"
      onClick={() => onClick?.(job.id)}
      aria-label={`${job.name} ${priorityLabel} ${statusLabel} ${job.retry_count} / ${job.max_retries}`}
      className="w-full rounded-lg border border-slate-200 bg-white p-3 text-left shadow-sm transition hover:border-slate-300 hover:shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate font-medium text-slate-900">{job.name}</span>
        <span
          className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${PRIORITY_BADGE_CLASSES[job.priority]}`}
        >
          {priorityLabel}
        </span>
      </div>
      <div className="mt-2 flex items-center justify-between text-xs">
        <span
          className={`rounded px-1.5 py-0.5 font-medium ${STATUS_BADGE_CLASSES[job.status]}`}
        >
          {statusLabel}
        </span>
        <span className="text-slate-600">
          {job.retry_count} / {job.max_retries}
        </span>
      </div>
    </button>
  );
}
