import { apiClient } from "../../lib/api-client";
import {
  PipelineRunResource,
  RunStageResource,
  RunJobItem,
  RunEventsPage,
  RunEventRecord,
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseInteger(value: unknown, fallback: number, minimum: number): number {
  const parsed = typeof value === "number" ? value : Number.parseInt(String(value), 10);
  return Number.isFinite(parsed) && parsed >= minimum ? Math.floor(parsed) : fallback;
}

function readPage(payload: Record<string, unknown>): {
  number: number;
  size: number;
  total_items: number;
  total_pages: number;
} {
  const page = payload.page;
  if (!isRecord(page)) throw new Error("Invalid pagination envelope.");
  const number = page.number;
  const size = page.size;
  const total_items = page.total_items;
  const total_pages = page.total_pages;
  if (
    typeof number !== "number" || !Number.isInteger(number) || number < 1 ||
    typeof size !== "number" || !Number.isInteger(size) || size < 1 ||
    typeof total_items !== "number" || !Number.isInteger(total_items) || total_items < 0 ||
    typeof total_pages !== "number" || !Number.isInteger(total_pages) || total_pages < 1
  ) {
    throw new Error("Invalid pagination envelope.");
  }
  return {
    number,
    size,
    total_items,
    total_pages,
  };
}

function normalizeSkillValues(value: unknown): string[] {
  const values = Array.isArray(value) ? value : [value];
  return values.flatMap((skill) => {
    if (typeof skill === "string") {
      return skill.split(/[,;\n]+/).map((part) => part.trim()).filter(Boolean);
    }
    if (isRecord(skill)) {
      const label = skill.name ?? skill.skill ?? skill.title ?? skill.canonical;
      return typeof label === "string" ? [label.trim()].filter(Boolean) : [];
    }
    return [];
  });
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
  if (params?.page !== undefined && params?.page !== null) {
    query.set("page", String(parseInteger(params.page, 1, 1)));
  }
  if (params?.page_size) query.set("page_size", String(params.page_size));

  const qs = query.toString();
  const path = `/runs${qs ? `?${qs}` : ""}`;
  const res = await apiClient.get<any>(path);
  const payload = isRecord(res.data) ? res.data : null;
  if (!payload || !Array.isArray(payload.data)) throw new Error("Invalid runs response.");
  const page = readPage(payload);
  return {
    data: payload.data as PipelineRunResource[],
    page: page.number,
    page_size: page.size,
    total_items: page.total_items,
    total_pages: page.total_pages,
    meta: isRecord(payload.meta) ? payload.meta as unknown as RunsPaginationMeta : undefined,
  };
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

export function extractJobSkills(item: unknown): string[] {
  if (!isRecord(item)) return [];
  const snapshot = isRecord(item.source_snapshot) ? item.source_snapshot : {};
  const attributes = isRecord(item.attributes) ? item.attributes : {};
  const job = isRecord(item.job) ? item.job : {};
  const candidates = [
    item.skills, item.required_skills, item.required_skills_display,
    item.required_skills_canonical, item.must_have_skills,
    snapshot.required_skills, snapshot.required_skills_display,
    snapshot.required_skills_canonical, snapshot.skills,
    snapshot.must_have_skills, attributes.required_skills,
    attributes.skills, job.skills, job.required_skills,
  ];
  for (const c of candidates) {
    const skills = normalizeSkillValues(c);
    if (skills.length > 0) return skills;
  }
  return [];
}

export function extractRequiredJobSkills(item: unknown): string[] {
  if (!isRecord(item)) return [];
  const snapshot = isRecord(item.source_snapshot) ? item.source_snapshot : {};
  const attributes = isRecord(item.attributes) ? item.attributes : {};
  const job = isRecord(item.job) ? item.job : {};
  const evidence = isRecord(item.evidence) ? item.evidence : {};
  for (const value of [
    item.required_skills, item.required_skills_display,
    item.required_skills_canonical, item.must_have_skills,
    item.skills, evidence.skills,
    snapshot.required_skills, snapshot.required_skills_display,
    snapshot.required_skills_canonical, snapshot.must_have_skills,
    snapshot.skills, attributes.required_skills,
    attributes.skills, job.required_skills, job.skills,
  ]) {
    const skills = normalizeSkillValues(value);
    if (skills.length > 0) return skills;
  }
  return [];
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
  if (params?.page !== undefined && params?.page !== null) {
    query.set("page", String(parseInteger(params.page, 1, 1)));
  }
  if (params?.page_size !== undefined && params?.page_size !== null) {
    query.set("page_size", String(parseInteger(params.page_size, 10, 1)));
  }
  if (params?.search) query.set("search", params.search);
  if (params?.stage && params.stage !== "all") query.set("stage", params.stage);
  if (params?.result_bucket && params.result_bucket !== "all") query.set("result_bucket", params.result_bucket);

  const qs = query.toString();
  const path = `/runs/${encodeURIComponent(runId)}/jobs${qs ? `?${qs}` : ""}`;
  const res = await apiClient.get<any>(path);
  const payload = isRecord(res.data) ? res.data : null;
  if (!payload || !Array.isArray(payload.data)) throw new Error("Invalid jobs response.");
  const page = readPage(payload);
  return {
    data: (payload.data as RunJobItem[]).map((job: any) => {
      const skills = extractJobSkills(job);
      return {
        ...job,
        skills,
        required_skills: extractRequiredJobSkills(job),
        interest_rating: job.interest_rating ?? (typeof job.rating === 'number' ? job.rating : null),
      };
    }),
    page: page.number,
    page_size: page.size,
    total_items: page.total_items,
    total_pages: page.total_pages,
    meta: isRecord(payload.meta)
      ? payload.meta as unknown as RunJobsPaginationMeta
      : undefined,
  };
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
  const res = await apiClient.get<unknown>(path);
  const data = isRecord(res.data) ? res.data : null;
  const meta = data && isRecord(data.meta) ? data.meta : null;
  if (!data || !Array.isArray(data.data) || !meta) throw new Error("Invalid events response.");
  if (
    (meta.next_cursor !== null && typeof meta.next_cursor !== "string") ||
    typeof meta.total_count !== "number" ||
    !Number.isInteger(meta.total_count) ||
    typeof meta.integrity_conflicts !== "number" ||
    !Number.isInteger(meta.integrity_conflicts)
  ) {
    throw new Error("Invalid events response.");
  }

  return {
    events: data.data as RunEventRecord[],
    next_cursor: meta.next_cursor as string | null,
    integrity_conflicts: meta.integrity_conflicts,
    total_count: meta.total_count,
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
