import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Job } from "@/domain/status/status";
import * as apiClient from "@/lib/api-client";

import { JobActions } from "../JobActions";

afterEach(() => {
  vi.restoreAllMocks();
});

const job = (status: Job["status"]): Job => ({
  id: 4,
  name: "SHOT010_render",
  priority: "normal",
  status,
  retry_count: 0,
  max_retries: 3,
});

describe("JobActions", () => {
  it("待機中は、一時停止とキャンセルを出す", () => {
    render(<JobActions job={job("pending")} />);

    expect(screen.getByRole("button", { name: "一時停止" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "キャンセル" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "再投入" })).not.toBeInTheDocument();
  });

  it("実行中は、操作を出さない", () => {
    const { container } = render(<JobActions job={job("running")} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("成功すると、結果を通知し、onDone を呼ぶ", async () => {
    const control = vi.spyOn(apiClient, "controlJob").mockResolvedValue(job("pending"));
    const onDone = vi.fn();
    const user = userEvent.setup();
    render(<JobActions job={job("dead")} onDone={onDone} />);

    await user.click(screen.getByRole("button", { name: "再投入" }));

    expect(control).toHaveBeenCalledWith(expect.any(String), 4, "requeue");
    expect(await screen.findByRole("status")).toHaveTextContent("SHOT010_renderを再投入しました");
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it("失敗すると、理由つきで通知し、onDone は呼ばない", async () => {
    vi.spyOn(apiClient, "controlJob").mockRejectedValue(
      new apiClient.ApiError(409, "Cannot cancel a job that is running"),
    );
    const onDone = vi.fn();
    const user = userEvent.setup();
    render(<JobActions job={job("pending")} onDone={onDone} />);

    await user.click(screen.getByRole("button", { name: "キャンセル" }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(
        "SHOT010_renderのキャンセルに失敗しました(Cannot cancel a job that is running)",
      );
    });
    expect(onDone).not.toHaveBeenCalled();
  });

  it("通知の領域は、操作の前から存在する(読み上げに必要)", () => {
    render(<JobActions job={job("pending")} />);

    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });
});
