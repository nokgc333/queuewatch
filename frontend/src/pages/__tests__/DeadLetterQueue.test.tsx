import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as apiClient from "@/lib/api-client";

import { DeadLetterQueue } from "../DeadLetterQueue";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("DeadLetterQueue", () => {
  it("dead状態のジョブ一覧を表示する", async () => {
    vi.spyOn(apiClient, "listJobs").mockResolvedValue([
      {
        id: 1,
        name: "SHOT099_render",
        priority: "high",
        status: "dead",
        retry_count: 3,
        max_retries: 3,
        error_message: "Simulated render failure (license server timeout)",
      },
    ]);

    render(
      <DeadLetterQueue />,
    );

    expect(await screen.findByText("SHOT099_render")).toBeInTheDocument();
    expect(screen.getByText(/Simulated render failure/)).toBeInTheDocument();
    expect(apiClient.listJobs).toHaveBeenCalledWith(expect.any(String), { status: "dead" });
  });

  it("運用ガイド文言を表示する", async () => {
    vi.spyOn(apiClient, "listJobs").mockResolvedValue([]);

    render(
      <DeadLetterQueue />,
    );

    expect(await screen.findByText(/「再投入」で、リトライ回数を 0 に戻して/)).toBeInTheDocument();
  });

  it("デッドレターのジョブごとに、再投入のボタンを出す", async () => {
    vi.spyOn(apiClient, "listJobs").mockResolvedValue([
      {
        id: 9,
        name: "SHOT090_render",
        priority: "normal",
        status: "dead",
        retry_count: 3,
        max_retries: 3,
        error_message: "boom",
      },
    ]);

    render(
      <DeadLetterQueue />,
    );

    expect(await screen.findByRole("button", { name: "再投入" })).toBeInTheDocument();
  });
});
