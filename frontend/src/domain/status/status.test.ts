/**
 * domain/status/status.ts の単体テスト（仕様書§6.2, §7.3の状態遷移を反映）。
 */
import { describe, expect, it } from "vitest";

import {
  DONE_STATUSES,
  groupJobsByStatus,
  isDeadStatus,
  isDoneStatus,
  isValidStatus,
  STATUS_LABELS,
  STATUS_ORDER,
  type Job,
} from "./status";

describe("isValidStatus", () => {
  it.each(STATUS_ORDER)("%sは有効なステータスと判定される", (status) => {
    expect(isValidStatus(status)).toBe(true);
  });

  it("未定義の文字列は無効と判定される", () => {
    expect(isValidStatus("unknown")).toBe(false);
  });

  it("空文字列は無効と判定される", () => {
    expect(isValidStatus("")).toBe(false);
  });
});

describe("STATUS_LABELS", () => {
  it("全ステータスに日本語ラベルが定義されている", () => {
    for (const status of STATUS_ORDER) {
      expect(STATUS_LABELS[status]).toBeTruthy();
    }
  });
});

describe("isDoneStatus", () => {
  it("successはdone扱い", () => {
    expect(isDoneStatus("success")).toBe(true);
  });

  it("deadはdone扱い(SCR-001でコンパクト表示対象)", () => {
    expect(isDoneStatus("dead")).toBe(true);
  });

  it("pendingはdone扱いではない", () => {
    expect(isDoneStatus("pending")).toBe(false);
  });

  it("DONE_STATUSESとisDoneStatusは一致する", () => {
    for (const status of STATUS_ORDER) {
      expect(isDoneStatus(status)).toBe(DONE_STATUSES.has(status));
    }
  });
});

describe("isDeadStatus", () => {
  it("deadのみtrueを返す", () => {
    expect(isDeadStatus("dead")).toBe(true);
    expect(isDeadStatus("success")).toBe(false);
    expect(isDeadStatus("retrying")).toBe(false);
  });
});

describe("groupJobsByStatus", () => {
  const makeJob = (id: number, status: Job["status"]): Job => ({
    id,
    name: `JOB_${id}`,
    priority: "normal",
    status,
    retry_count: 0,
    max_retries: 3,
  });

  it("空配列を渡すと全ステータスが空配列のグループを返す", () => {
    const grouped = groupJobsByStatus([]);
    for (const status of STATUS_ORDER) {
      expect(grouped[status]).toEqual([]);
    }
  });

  it("ジョブをステータス別に分類する", () => {
    const jobs = [makeJob(1, "pending"), makeJob(2, "running"), makeJob(3, "pending")];

    const grouped = groupJobsByStatus(jobs);

    expect(grouped.pending).toHaveLength(2);
    expect(grouped.running).toHaveLength(1);
    expect(grouped.success).toHaveLength(0);
  });
});
