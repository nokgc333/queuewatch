/** components/job-board/__tests__/JobCard.test.tsx（仕様書§12.2の抜粋を踏襲）。 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Job } from "@/domain/status/status";

import { JobCard } from "../JobCard";

function makeJob(overrides: Partial<Job> = {}): Job {
  return {
    id: 1,
    name: "SHOT010_render",
    priority: "high",
    status: "retrying",
    retry_count: 1,
    max_retries: 3,
    ...overrides,
  };
}

describe("JobCard", () => {
  it("ジョブ名・優先度・現在ステータスを表示する", () => {
    render(<JobCard job={makeJob()} />);

    expect(screen.getByText("SHOT010_render")).toBeInTheDocument();
    expect(screen.getByLabelText(/リトライ中/)).toBeInTheDocument();
  });

  it("リトライ回数を表示する", () => {
    render(<JobCard job={makeJob({ retry_count: 2, max_retries: 3 })} />);

    expect(screen.getByText("2 / 3")).toBeInTheDocument();
  });

  it("クリック時にonClickへジョブIDを渡す", async () => {
    const onClick = vi.fn();
    render(<JobCard job={makeJob({ id: 42 })} onClick={onClick} />);

    screen.getByRole("button").click();

    expect(onClick).toHaveBeenCalledWith(42);
  });

  it("dead状態のジョブにはaria-labelでデッドレターである旨を示す", () => {
    render(<JobCard job={makeJob({ status: "dead" })} />);

    expect(screen.getByLabelText(/デッドレター/)).toBeInTheDocument();
  });

  it("アクセシブルな名前は、見えている文字(優先度・状態・リトライ回数)を含む", () => {
    render(
      <JobCard
        job={{
          id: 1,
          name: "SHOT010_render",
          priority: "high",
          status: "retrying",
          retry_count: 2,
          max_retries: 3,
        }}
      />,
    );

    const name = screen.getByRole("button").getAttribute("aria-label") ?? "";

    for (const visible of ["SHOT010_render", "高", "リトライ中", "2 / 3"]) {
      expect(name).toContain(visible);
    }
  });
});
