/**
 * ジョブステータスの分類・グルーピングの純粋関数
 * (PipeBoardのdomain/status/status.tsパターンを踏襲、仕様書§6.2, §7.3)。
 *
 * 状態遷移: pending -> running -> (success | retrying -> running -> ... -> dead)
 */

export const STATUS_ORDER = [
  "pending",
  "running",
  "retrying",
  "success",
  "dead",
] as const;

export type Status = (typeof STATUS_ORDER)[number];

export const STATUS_LABELS: Record<Status, string> = {
  pending: "待機中",
  running: "処理中",
  retrying: "リトライ中",
  success: "成功",
  dead: "デッドレター",
};

export function isValidStatus(value: string): value is Status {
  return (STATUS_ORDER as readonly string[]).includes(value);
}

/** SCR-001: doneはコンパクト表示に折りたたむ対象（success/dead）。 */
export const DONE_STATUSES: ReadonlySet<Status> = new Set(["success", "dead"]);

export function isDoneStatus(status: Status): boolean {
  return DONE_STATUSES.has(status);
}

export function isDeadStatus(status: Status): boolean {
  return status === "dead";
}

export interface Job {
  id: number;
  name: string;
  priority: "high" | "normal" | "low";
  status: Status;
  retry_count: number;
  max_retries: number;
  error_message?: string | null;
  created_at?: string;
  updated_at?: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export type GroupedJobs = Record<Status, Job[]>;

export function groupJobsByStatus(jobs: Job[]): GroupedJobs {
  const grouped: GroupedJobs = {
    pending: [],
    running: [],
    retrying: [],
    success: [],
    dead: [],
  };

  for (const job of jobs) {
    grouped[job.status].push(job);
  }
  return grouped;
}
