/** ジョブ盤の検索・絞り込み(名前の部分一致と優先度)。 */
import type { ReactElement } from "react";

import { PRIORITY_LABELS, PRIORITY_ORDER, type Priority } from "@/domain/job/priority";

export interface JobFilterValue {
  q: string;
  priority: Priority | "";
}

export interface JobFiltersProps {
  value: JobFilterValue;
  onChange: (next: JobFilterValue) => void;
}

export function JobFilters({ value, onChange }: JobFiltersProps): ReactElement {
  return (
    <form
      role="search"
      aria-label="ジョブの検索"
      className="flex flex-wrap items-end gap-3"
      onSubmit={(event) => event.preventDefault()}
    >
      <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
        名前で検索
        <input
          type="search"
          value={value.q}
          maxLength={100}
          onChange={(event) => onChange({ ...value, q: event.target.value })}
          className="w-56 rounded border border-slate-400 px-2 py-1 text-sm text-slate-900"
        />
      </label>
      <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
        優先度
        <select
          value={value.priority}
          onChange={(event) =>
            onChange({ ...value, priority: event.target.value as JobFilterValue["priority"] })
          }
          className="rounded border border-slate-400 px-2 py-1 text-sm text-slate-900"
        >
          <option value="">すべて</option>
          {PRIORITY_ORDER.map((priority) => (
            <option key={priority} value={priority}>
              {PRIORITY_LABELS[priority]}
            </option>
          ))}
        </select>
      </label>
      {(value.q !== "" || value.priority !== "") && (
        <button
          type="button"
          onClick={() => onChange({ q: "", priority: "" })}
          className="rounded border border-slate-400 px-2 py-1 text-sm text-slate-800 hover:bg-slate-50"
        >
          条件をクリア
        </button>
      )}
    </form>
  );
}
