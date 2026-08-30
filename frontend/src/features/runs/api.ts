import { apiClient } from "../../lib/api-client";
import {
  PipelineRunResource,
  RunStageResource,
  RunJobItem,
  RunEventsPage,
  DeleteArchivedRunsPreview,
  RunLifecycle,
  RunsPaginationMeta,
  RunJobsPaginationMeta,
} from "./types";

export interface PaginationEnvelope<T, M = Record<string, unknown>> {
  data: T[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages?: number;
  meta?: M;
}

export function generateIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "idem_" + Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
}

export async function fetchRuns(params?: {
  view?: RunLifecycle;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginationEnvelope<PipelineRunResource, RunsPaginationMeta>> {
  const query = new URLSearchParams();
  if (params?.view) query.set("view", params.view);
  if (params?.search) query.set("search", params.search);
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));

  const qs = query.toString();
  const path = `/runs${qs ? `?${qs}` : ""}`;
  const res = await apiClient.get<PaginationEnvelope<PipelineRunResource, RunsPaginationMeta>>(path);
  return res.data;
}

export async function fetchRun(runId: string): Promise<PipelineRunResource> {
  const res = await apiClient.get<{ data: PipelineRunResource }>(
    `/runs/${encodeURIComponent(runId)}`
  );
  return (res.data as any)?.data || res.data;
}

export async function fetchRunStages(runId: string): Promise<RunStageResource[]> {
  const res = await apiClient.get<{ data: RunStageResource[] }>(
    `/runs/${encodeURIComponent(runId)}/stages`
  );
  return (res.data as any)?.data || res.data;
}

export async function fetchRunJobs(
  runId: string,
  params?: {
    page?: number;
    page_size?: number;
    search?: string;
    stage?: string;
    result_bucket?: string;
  }
): Promise<PaginationEnvelope<RunJobItem, RunJobsPaginationMeta>> {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  if (params?.search) query.set("search", params.search);
  if (params?.stage && params.stage !== "all") query.set("stage", params.stage);
  if (params?.result_bucket && params.result_bucket !== "all") query.set("result_bucket", params.result_bucket);

  const qs = query.toString();
  const path = `/runs/${encodeURIComponent(runId)}/jobs${qs ? `?${qs}` : ""}`;
  const res = await apiClient.get<PaginationEnvelope<RunJobItem, RunJobsPaginationMeta>>(path);
  return res.data;
}

export async function fetchRunEvents(
  runId: string,
  cursor?: string | null,
  limit = 100
): Promise<RunEventsPage> {
  const query = new URLSearchParams();
  if (cursor) query.set("cursor", cursor);
  if (limit) query.set("limit", String(limit));

  const qs = query.toString();
  const path = `/runs/${encodeURIComponent(runId)}/events${qs ? `?${qs}` : ""}`;
  const res = await apiClient.get<PaginationEnvelope<any, any>>(path);

  const data = res.data;
  const items = Array.isArray(data?.data) ? data.data : Array.isArray(data) ? data : [];
  const meta = data?.meta || {};

  return {
    events: items,
    next_cursor: meta.next_cursor || null,
    integrity_conflicts: Number(meta.integrity_conflicts || 0),
    total_count: Number(data?.total_items || items.length),
  };
}

export async function triggerRun(
  formData: FormData,
  idempotencyKey = generateIdempotencyKey()
): Promise<PipelineRunResource> {
  const res = await apiClient.post<{ data: PipelineRunResource }>(
    "/runs",
    formData,
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function cancelRun(runId: string): Promise<PipelineRunResource> {
  const res = await apiClient.post<{ data: PipelineRunResource }>(
    `/runs/${encodeURIComponent(runId)}/actions/cancel`
  );
  return (res.data as any)?.data || res.data;
}

export async function archiveRun(runId: string): Promise<PipelineRunResource> {
  const res = await apiClient.post<{ data: PipelineRunResource }>(
    `/runs/${encodeURIComponent(runId)}/actions/archive`
  );
  return (res.data as any)?.data || res.data;
}

export async function unarchiveRun(runId: string): Promise<PipelineRunResource> {
  const res = await apiClient.post<{ data: PipelineRunResource }>(
    `/runs/${encodeURIComponent(runId)}/actions/unarchive`
  );
  return (res.data as any)?.data || res.data;
}

export async function previewDeleteArchivedRuns(
  runIds: string[]
): Promise<DeleteArchivedRunsPreview> {
  const res = await apiClient.post<{ data: DeleteArchivedRunsPreview }>(
    "/runs/actions/delete-archived/preview",
    { run_ids: runIds }
  );
  return (res.data as any)?.data || res.data;
}

export async function deleteArchivedRuns(
  runIds: string[],
  previewRevision: string,
  idempotencyKey = generateIdempotencyKey()
): Promise<{ deleted_count: number; run_ids: string[] }> {
  const res = await apiClient.post<{ data: { deleted_count: number; run_ids: string[] } }>(
    "/runs/actions/delete-archived",
    {
      run_ids: runIds,
      preview_revision: previewRevision,
    },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function downloadDebugBundle(runId: string): Promise<void> {
  return apiClient.download(
    `/runs/${encodeURIComponent(runId)}/debug-bundle`,
    `fitcv-run-${runId}-debug.zip`
  );
}

export async function exportRunJobsCsv(
  runId: string,
  params?: {
    search?: string;
    stage?: string;
    result_bucket?: string;
  }
): Promise<void> {
  const query = new URLSearchParams();
  if (params?.search) query.set("search", params.search);
  if (params?.stage && params.stage !== "all") query.set("stage", params.stage);
  if (params?.result_bucket && params.result_bucket !== "all") query.set("result_bucket", params.result_bucket);

  const qs = query.toString();
  const path = `/runs/${encodeURIComponent(runId)}/jobs/export.csv${qs ? `?${qs}` : ""}`;
  return apiClient.download(path, `fitcv-run-${runId}-jobs.csv`);
}
