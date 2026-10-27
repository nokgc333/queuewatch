/** lib/api-client.ts の単体テスト（fetchをモックして検証、PipeBoardのパターンを踏襲）。 */
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  createJob,
  deleteJob,
  getDurationStats,
  getErrorStats,
  getJob,
  getUtilizationStats,
  getWorkerStatus,
  listJobs,
} from "./api-client";

const BASE_URL = "http://localhost:8000";

function mockFetchOnce(status: number, body: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("listJobs", () => {
  it("GET /jobsを呼びジョブ配列を返す", async () => {
    mockFetchOnce(200, [{ id: 1, name: "JOB_A", status: "pending" }]);

    const jobs = await listJobs(BASE_URL);

    expect(fetch).toHaveBeenCalledWith(`${BASE_URL}/jobs`);
    expect(jobs).toHaveLength(1);
  });

  it("statusフィルタをクエリパラメータに付与する", async () => {
    mockFetchOnce(200, []);

    await listJobs(BASE_URL, { status: "dead" });

    expect(fetch).toHaveBeenCalledWith(`${BASE_URL}/jobs?status=dead`);
  });

  it("priorityフィルタをクエリパラメータに付与する", async () => {
    mockFetchOnce(200, []);

    await listJobs(BASE_URL, { priority: "high" });

    expect(fetch).toHaveBeenCalledWith(`${BASE_URL}/jobs?priority=high`);
  });
});

describe("createJob", () => {
  it("POST /jobsでname/priorityを送信する", async () => {
    mockFetchOnce(201, { id: 1, name: "SHOT010_render", priority: "high", status: "pending" });

    const job = await createJob(BASE_URL, { name: "SHOT010_render", priority: "high" });

    expect(fetch).toHaveBeenCalledWith(`${BASE_URL}/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "SHOT010_render", priority: "high" }),
    });
    expect(job.id).toBe(1);
  });
});

describe("getJob", () => {
  it("GET /jobs/:idでジョブ詳細を取得する", async () => {
    mockFetchOnce(200, { id: 5, name: "JOB_E", retry_logs: [] });

    const job = await getJob(BASE_URL, 5);

    expect(fetch).toHaveBeenCalledWith(`${BASE_URL}/jobs/5`);
    expect(job.id).toBe(5);
  });

  it("404応答時はApiErrorを送出する", async () => {
    mockFetchOnce(404, { title: "Job 999 not found", status: 404 });

    await expect(getJob(BASE_URL, 999)).rejects.toThrow(ApiError);
  });

  it("ApiErrorはtitleをmessageとして保持する", async () => {
    mockFetchOnce(404, { title: "Job 999 not found", status: 404 });

    try {
      await getJob(BASE_URL, 999);
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).message).toBe("Job 999 not found");
      expect((err as ApiError).status).toBe(404);
    }
  });
});

describe("deleteJob", () => {
  it("DELETE /jobs/:idを呼ぶ", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 204, json: async () => ({}) }),
    );

    await deleteJob(BASE_URL, 7);

    expect(fetch).toHaveBeenCalledWith(`${BASE_URL}/jobs/7`, { method: "DELETE" });
  });
});

describe("getWorkerStatus", () => {
  it("GET /workers/statusを呼ぶ", async () => {
    mockFetchOnce(200, [{ worker_name: "celery@w1", processed_count: 1, failed_count: 0, utilization: 0.5 }]);

    const workers = await getWorkerStatus(BASE_URL);

    expect(fetch).toHaveBeenCalledWith(`${BASE_URL}/workers/status`);
    expect(workers[0]?.worker_name).toBe("celery@w1");
  });
});

describe("stats endpoints", () => {
  it("getUtilizationStatsはGET /stats/utilizationを呼ぶ", async () => {
    mockFetchOnce(200, []);
    await getUtilizationStats(BASE_URL);
    expect(fetch).toHaveBeenCalledWith(`${BASE_URL}/stats/utilization`);
  });

  it("getDurationStatsはGET /stats/durationを呼ぶ", async () => {
    mockFetchOnce(200, []);
    await getDurationStats(BASE_URL);
    expect(fetch).toHaveBeenCalledWith(`${BASE_URL}/stats/duration`);
  });

  it("getErrorStatsはGET /stats/errorsを呼ぶ", async () => {
    mockFetchOnce(200, []);
    await getErrorStats(BASE_URL);
    expect(fetch).toHaveBeenCalledWith(`${BASE_URL}/stats/errors`);
  });
});

describe("ApiError fallback", () => {
  it("JSONパース失敗時はデフォルトメッセージを使う", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error("not json");
        },
      }),
    );

    await expect(listJobs(BASE_URL)).rejects.toThrow("Request failed: 500");
  });
});

describe("認証トークン", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("トークンが無いときは、Authorization ヘッダを付けない", async () => {
    mockFetchOnce(200, []);

    await listJobs(BASE_URL);

    expect(fetch).toHaveBeenCalledWith(`${BASE_URL}/jobs`);
  });

  it("VITE_API_TOKEN があるときは、読み取りに Bearer ヘッダを付ける", async () => {
    vi.stubEnv("VITE_API_TOKEN", "view-token-0001");
    mockFetchOnce(200, []);

    await listJobs(BASE_URL);

    expect(fetch).toHaveBeenCalledWith(`${BASE_URL}/jobs`, {
      headers: { Authorization: "Bearer view-token-0001" },
    });
  });

  it("書き込みでは、Content-Type と Bearer の両方を送る", async () => {
    vi.stubEnv("VITE_API_TOKEN", "edit-token-0002");
    mockFetchOnce(201, { id: 1 });

    await createJob(BASE_URL, { name: "JOB_A" });

    expect(fetch).toHaveBeenCalledWith(
      `${BASE_URL}/jobs`,
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer edit-token-0002" },
      }),
    );
  });

  it("401 のときは、案内つきのエラーにする", async () => {
    mockFetchOnce(401, { title: "Authentication required" });

    await expect(listJobs(BASE_URL)).rejects.toMatchObject({ status: 401 });
  });
});
