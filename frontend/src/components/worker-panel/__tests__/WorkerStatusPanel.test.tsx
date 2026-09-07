import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { WorkerStatusDto } from "@/lib/api-client";

import { WorkerStatusPanel } from "../WorkerStatusPanel";

describe("WorkerStatusPanel", () => {
  it("ワーカーごとの稼働率・処理件数を表示する", () => {
    const workers: WorkerStatusDto[] = [
      { worker_name: "celery@worker1", processed_count: 12, failed_count: 1, utilization: 0.75 },
    ];

    render(<WorkerStatusPanel workers={workers} />);

    expect(screen.getByText("celery@worker1")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText(/12/)).toBeInTheDocument();
  });

  it("ワーカーが0件の場合はメッセージを表示する", () => {
    render(<WorkerStatusPanel workers={[]} />);

    expect(screen.getByText(/ワーカー情報がありません/)).toBeInTheDocument();
  });

  it("稼働率が0.3未満はidle、それ以上はbusyのラベルを付与する", () => {
    const workers: WorkerStatusDto[] = [
      { worker_name: "celery@idle", processed_count: 0, failed_count: 0, utilization: 0.1 },
      { worker_name: "celery@busy", processed_count: 5, failed_count: 0, utilization: 0.9 },
    ];

    render(<WorkerStatusPanel workers={workers} />);

    expect(screen.getByLabelText(/celery@idle.*idle/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/celery@busy.*busy/i)).toBeInTheDocument();
  });
});
