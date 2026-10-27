/** バックエンドAPI(FastAPI)向けの薄いfetchラッパー（PipeBoardのapi-client.tsパターンを踏襲）。 */
import { getApiToken } from "@/lib/config";
import type { Job, Status } from "@/domain/status/status";
import type { Priority } from "@/domain/job/priority";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface RetryLogDto {
  id: number;
  job_id: number;
  attempt_number: number;
  status: string;
  error_message: string | null;
  attempted_at: string;
}

export interface JobDetailDto extends Job {
  retry_logs: RetryLogDto[];
}

export interface WorkerStatusDto {
  worker_name: string;
  processed_count: number;
  failed_count: number;
  utilization: number;
}

export interface UtilizationStatDto {
  worker_name: string;
  utilization: number;
}

export interface DurationBinDto {
  bin_start: number;
  bin_end: number;
  count: number;
}

export interface ErrorBreakdownItemDto {
  error_message: string;
  count: number;
}

function withAuthorization(init?: RequestInit): RequestInit | undefined {
  const token = getApiToken();
  if (!token) return init;
  return {
    ...init,
    headers: {
      ...(init?.headers as Record<string, string> | undefined),
      Authorization: `Bearer ${token}`,
    },
  };
}

async function request<T>(url: string, requestInit?: RequestInit): Promise<T> {
  const init = withAuthorization(requestInit);
  const response = init === undefined ? await fetch(url) : await fetch(url, init);
  if (!response.ok) {
    const problem = await response.json().catch(() => ({}));
    throw new ApiError(response.status, problem.title ?? `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export interface ListJobsFilter {
  status?: Status;
  priority?: Priority;
}

export function listJobs(baseUrl: string, filter?: ListJobsFilter): Promise<Job[]> {
  const params = new URLSearchParams();
  if (filter?.status) params.set("status", filter.status);
  if (filter?.priority) params.set("priority", filter.priority);
  const query = params.toString();
  return request<Job[]>(`${baseUrl}/jobs${query ? `?${query}` : ""}`);
}

export interface CreateJobPayload {
  name: string;
  priority?: Priority;
}

export function createJob(baseUrl: string, payload: CreateJobPayload): Promise<Job> {
  return request<Job>(`${baseUrl}/jobs`, jsonInit("POST", payload));
}

export function getJob(baseUrl: string, jobId: number): Promise<JobDetailDto> {
  return request<JobDetailDto>(`${baseUrl}/jobs/${jobId}`);
}

export async function deleteJob(baseUrl: string, jobId: number): Promise<void> {
  await request<unknown>(`${baseUrl}/jobs/${jobId}`, { method: "DELETE" });
}

export function getWorkerStatus(baseUrl: string): Promise<WorkerStatusDto[]> {
  return request<WorkerStatusDto[]>(`${baseUrl}/workers/status`);
}

export function getUtilizationStats(baseUrl: string): Promise<UtilizationStatDto[]> {
  return request<UtilizationStatDto[]>(`${baseUrl}/stats/utilization`);
}

export function getDurationStats(baseUrl: string): Promise<DurationBinDto[]> {
  return request<DurationBinDto[]>(`${baseUrl}/stats/duration`);
}

export function getErrorStats(baseUrl: string): Promise<ErrorBreakdownItemDto[]> {
  return request<ErrorBreakdownItemDto[]>(`${baseUrl}/stats/errors`);
}
