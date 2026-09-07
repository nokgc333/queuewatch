import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Job } from "@/domain/status/status";

import { JobBoard } from "../JobBoard";

function makeJob(id: number, status: Job["status"]): Job {
  return {
    id,
    name: `JOB_${id}`,
    priority: "normal",
    status,
    retry_count: 0,
    max_retries: 3,
  };
}

describe("JobBoard", () => {
  it("ステータス別カラムを表示する", () => {
    render(<JobBoard jobs={[makeJob(1, "pending"), makeJob(2, "running")]} />);

    expect(screen.getByRole("heading", { name: "待機中" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "処理中" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "完了" })).toBeInTheDocument();
  });

  it("success/deadはdoneカラムにまとめられる", () => {
    render(
      <JobBoard jobs={[makeJob(1, "success"), makeJob(2, "dead")]} />,
    );

    expect(screen.getByText("JOB_1")).toBeInTheDocument();
    expect(screen.getByText("JOB_2")).toBeInTheDocument();
  });

  it("全体が0件の場合は空状態メッセージと新規登録ボタンを表示する", () => {
    render(<JobBoard jobs={[]} onCreateJob={vi.fn()} />);

    expect(screen.getByText("まだジョブがありません")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /新規ジョブ/ })).toBeInTheDocument();
  });

  it("新規ジョブボタンクリックでonCreateJobを呼ぶ", () => {
    const onCreateJob = vi.fn();
    render(<JobBoard jobs={[makeJob(1, "pending")]} onCreateJob={onCreateJob} />);

    screen.getByRole("button", { name: /新規ジョブ/ }).click();

    expect(onCreateJob).toHaveBeenCalledTimes(1);
  });
});
