import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Job } from "@/domain/status/status";

import { JobColumn } from "../JobColumn";

function makeJob(id: number): Job {
  return {
    id,
    name: `JOB_${id}`,
    priority: "normal",
    status: "pending",
    retry_count: 0,
    max_retries: 3,
  };
}

describe("JobColumn", () => {
  it("タイトルと件数を表示する", () => {
    render(<JobColumn title="待機中" jobs={[makeJob(1), makeJob(2)]} />);

    expect(screen.getByRole("heading", { name: "待機中" })).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("ジョブが0件の場合は空状態のメッセージを表示する", () => {
    render(<JobColumn title="待機中" jobs={[]} emptyMessage="ジョブがありません" />);

    expect(screen.getByText("ジョブがありません")).toBeInTheDocument();
  });

  it("ジョブごとにJobCardを描画する", () => {
    render(<JobColumn title="待機中" jobs={[makeJob(1), makeJob(2)]} />);

    expect(screen.getByText("JOB_1")).toBeInTheDocument();
    expect(screen.getByText("JOB_2")).toBeInTheDocument();
  });

  it("isLoadingの場合はスケルトンカードを表示する", () => {
    render(<JobColumn title="待機中" jobs={[]} isLoading />);

    expect(screen.getAllByTestId("job-card-skeleton")).toHaveLength(3);
  });
});
