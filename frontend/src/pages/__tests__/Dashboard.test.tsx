import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as apiClient from "@/lib/api-client";

import { Dashboard } from "../Dashboard";

afterEach(() => {
  vi.restoreAllMocks();
});

function renderDashboard(): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

describe("Dashboard", () => {
  it("ジョブとワーカー情報を取得して表示する", async () => {
    vi.spyOn(apiClient, "listJobs").mockResolvedValue([
      {
        id: 1,
        name: "SHOT010_render",
        priority: "high",
        status: "pending",
        retry_count: 0,
        max_retries: 3,
      },
    ]);
    vi.spyOn(apiClient, "getWorkerStatus").mockResolvedValue([
      { worker_name: "celery@w1", processed_count: 1, failed_count: 0, utilization: 0.4 },
    ]);

    renderDashboard();

    expect(await screen.findByText("SHOT010_render")).toBeInTheDocument();
    expect(await screen.findByText("celery@w1")).toBeInTheDocument();
  });

  it("ポーリング失敗時はエラーバナーを表示する", async () => {
    vi.spyOn(apiClient, "listJobs").mockRejectedValue(new Error("network error"));
    vi.spyOn(apiClient, "getWorkerStatus").mockResolvedValue([]);

    renderDashboard();

    expect(await screen.findByText(/取得に失敗/)).toBeInTheDocument();
  });

  it("新規ジョブボタンからモーダルを開きジョブを登録する", async () => {
    vi.spyOn(apiClient, "listJobs").mockResolvedValue([]);
    vi.spyOn(apiClient, "getWorkerStatus").mockResolvedValue([]);
    const createJobSpy = vi.spyOn(apiClient, "createJob").mockResolvedValue({
      id: 2,
      name: "NEW_JOB",
      priority: "normal",
      status: "pending",
      retry_count: 0,
      max_retries: 3,
    });

    renderDashboard();

    const user = userEvent.setup();
    // 両方のポーリング(jobs/workers)が解決し切ってDOMが安定するまで待ってから操作する
    // (2つの独立した非同期fetchが別々のタイミングで再描画を起こすため、片方の
    // 解決だけを待って要素参照を保持すると、直後の再描画で参照が切り離される
    // ことがある。クリック直前に毎回 screen から取り直すことで回避する)。
    await screen.findByText("ワーカー情報がありません");
    await user.click(screen.getByRole("button", { name: /新規ジョブ/ }));

    const dialog = await screen.findByRole("dialog");
    const nameInput = within(dialog).getByPlaceholderText("SHOT010_render");
    await user.type(nameInput, "NEW_JOB");
    await user.click(screen.getByRole("button", { name: "登録" }));

    await vi.waitFor(() => expect(createJobSpy).toHaveBeenCalled());
  });
});
