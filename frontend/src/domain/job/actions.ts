/**
 * ジョブの操作(キャンセル・一時停止・再開・再投入)を、状態ごとに出し分ける純粋関数
 * (バックエンドの domain/job_actions.py と同じ遷移)。
 */
import type { Status } from "@/domain/status/status";

export const JOB_ACTIONS = ["pause", "resume", "cancel", "requeue"] as const;

export type JobAction = (typeof JOB_ACTIONS)[number];

export const ACTION_LABELS: Record<JobAction, string> = {
  pause: "一時停止",
  resume: "再開",
  cancel: "キャンセル",
  requeue: "再投入",
};

export const ACTION_RESULT_LABELS: Record<JobAction, string> = {
  pause: "一時停止しました",
  resume: "再開しました",
  cancel: "キャンセルしました",
  requeue: "再投入しました",
};

const ALLOWED: Record<JobAction, ReadonlySet<Status>> = {
  pause: new Set<Status>(["pending", "retrying"]),
  resume: new Set<Status>(["paused"]),
  cancel: new Set<Status>(["pending", "retrying", "paused"]),
  requeue: new Set<Status>(["dead", "cancelled"]),
};

/** その状態で、できる操作(表示の順)。実行中・成功は、操作できない。 */
export function availableActions(status: Status): JobAction[] {
  return JOB_ACTIONS.filter((action) => ALLOWED[action].has(status));
}
