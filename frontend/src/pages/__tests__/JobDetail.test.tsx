import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as apiClient from "@/lib/api-client";

import { JobDetail } from "../JobDetail";

afterEach(() => {
  vi.restoreAllMocks();
});

function renderAt(jobId: number): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={[`/jobs/${jobId}`]}>
      <Routes>
        <Route path="/jobs/:id" element={<JobDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("JobDetail", () => {
  it("ジョブ名・ステータス・優先度・リトライ回数を表示する", async () => {
    vi.spyOn(apiClient, "getJob").mockResolvedValue({
      id: 1,
      name: "SHOT010_render",
      priority: "high",
      status: "retrying",
      retry_count: 2,
      max_retries: 3,
      error_message: "Simulated render failure (license server timeout)",
      retry_logs: [
        {
          id: 1,
          job_id: 1,
          attempt_number: 1,
          status: "failed",
          error_message: "Simulated render failure (license server timeout)",
          attempted_at: "2026-01-01T00:00:00Z",
        },
      ],
    });

    renderAt(1);

    expect(await screen.findByText("SHOT010_render")).toBeInTheDocument();
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
    expect(screen.getByText(/Simulated render failure/)).toBeInTheDocument();
  });

  it("dead状態の場合は警告表示をする", async () => {
    vi.spyOn(apiClient, "getJob").mockResolvedValue({
      id: 2,
      name: "SHOT020_render",
      priority: "normal",
      status: "dead",
      retry_count: 3,
      max_retries: 3,
      error_message: "Simulated render failure (license server timeout)",
      retry_logs: [],
    });

    renderAt(2);

    expect(await screen.findByText(/デッドレターキュー/)).toBeInTheDocument();
  });

  it("存在しないjob_idの場合はNotFound表示をする", async () => {
    const { ApiError } = apiClient;
    vi.spyOn(apiClient, "getJob").mockRejectedValue(new ApiError(404, "Job 999 not found"));

    renderAt(999);

    expect(await screen.findByText(/見つかりません/)).toBeInTheDocument();
  });
});
