/** ジョブの操作ボタン(状態に応じて出し分け、結果と失敗を読み上げ領域に出す)。 */
import { useState, type ReactElement } from "react";

import {
  ACTION_LABELS,
  ACTION_RESULT_LABELS,
  availableActions,
  type JobAction,
} from "@/domain/job/actions";
import type { Job } from "@/domain/status/status";
import { ApiError, controlJob } from "@/lib/api-client";
import { API_BASE_URL } from "@/lib/config";

export interface JobActionsProps {
  job: Job;
  onDone?: () => void;
}

export function JobActions({ job, onDone }: JobActionsProps): ReactElement | null {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const actions = availableActions(job.status);

  if (actions.length === 0 && message === "") return null;

  const run = async (action: JobAction): Promise<void> => {
    setBusy(true);
    try {
      await controlJob(API_BASE_URL, job.id, action);
      setMessage(`${job.name}を${ACTION_RESULT_LABELS[action]}`);
      onDone?.();
    } catch (error) {
      const reason = error instanceof ApiError ? `(${error.message})` : "";
      setMessage(`${job.name}の${ACTION_LABELS[action]}に失敗しました${reason}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {actions.map((action) => (
        <button
          key={action}
          type="button"
          disabled={busy}
          onClick={() => void run(action)}
          className="rounded border border-slate-300 bg-white px-3 py-1 text-sm font-medium text-slate-800 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-600 disabled:opacity-50"
        >
          {ACTION_LABELS[action]}
        </button>
      ))}
      <p role="status" aria-live="polite" className="text-sm text-slate-700">
        {message}
      </p>
    </div>
  );
}
