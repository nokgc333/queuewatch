/** SCR-001: 「+ 新規ジョブ」ボタンから開く登録モーダル（仕様書§6.2）。 */
import { useState, type ReactElement } from "react";

import { PRIORITY_LABELS, PRIORITY_ORDER, type Priority } from "@/domain/job/priority";

export interface NewJobModalProps {
  onSubmit: (payload: { name: string; priority: Priority }) => void;
  onClose: () => void;
}

export function NewJobModal({ onSubmit, onClose }: NewJobModalProps): ReactElement {
  const [name, setName] = useState("");
  const [priority, setPriority] = useState<Priority>("normal");

  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    if (name.trim().length === 0) return;
    onSubmit({ name: name.trim(), priority });
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/40">
      <div
        role="dialog"
        aria-label="新規ジョブ登録"
        className="w-full max-w-sm rounded-lg bg-white p-4 shadow-lg"
      >
        <h2 className="mb-3 text-sm font-semibold text-slate-800">新規ジョブ登録</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            ジョブ名
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="rounded border border-slate-300 px-2 py-1 text-sm"
              placeholder="SHOT010_render"
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            優先度
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value as Priority)}
              className="rounded border border-slate-300 px-2 py-1 text-sm"
            >
              {PRIORITY_ORDER.map((p) => (
                <option key={p} value={p}>
                  {PRIORITY_LABELS[p]}
                </option>
              ))}
            </select>
          </label>
          <div className="mt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
            >
              キャンセル
            </button>
            <button
              type="submit"
              className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              登録
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
