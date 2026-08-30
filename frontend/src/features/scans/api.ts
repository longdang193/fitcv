import { apiClient } from "../../lib/api-client";
import {
  ScanResource,
  TrackedCompanyResource,
  TrackedCompanyVerifyPayload,
  TrackedCompanyVerifyResult,
  ScanCreatePayload,
  ProcessEventsPage,
  ScanJobItem,
  DeletePreviewResult,
} from "./types";

export interface ScanListResponse {
  data: ScanResource[];
  page: number;
  page_size: number;
  total_items?: number;
  total?: number;
  meta?: {
    active_count?: number;
    archived_count?: number;
    [key: string]: unknown;
  };
}

export interface TrackedCompanyListResponse {
  data: TrackedCompanyResource[];
  page: number;
  page_size: number;
  total_items?: number;
  total?: number;
}

export interface ScanJobsResponse {
  data: ScanJobItem[];
  page: number;
  page_size: number;
  total_items?: number;
  total?: number;
}

export async function fetchScans(params: {
  lifecycle?: string;
  execution_status?: string;
  usable_for_run?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<ScanListResponse> {
  const query = new URLSearchParams();
  if (params.lifecycle) query.set("lifecycle", params.lifecycle);
  if (params.execution_status) query.set("execution_status", params.execution_status);
  if (params.usable_for_run !== undefined) query.set("usable_for_run", String(params.usable_for_run));
  if (params.search) query.set("search", params.search);
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));

  const res = await apiClient.get<ScanListResponse>(`/scans?${query.toString()}`);
  return res.data;
}

export async function fetchScan(scanId: string): Promise<ScanResource> {
  const res = await apiClient.get<{ data: ScanResource }>(`/scans/${encodeURIComponent(scanId)}`);
  return res.data.data;
}

export async function createScan(
  payload: ScanCreatePayload,
  idempotencyKey?: string
): Promise<ScanResource> {
  const key = idempotencyKey || crypto.randomUUID();
  const res = await apiClient.post<{ data: ScanResource }>("/scans", payload, {
    idempotencyKey: key,
  });
  return res.data.data;
}

export async function fetchTrackedCompanies(search = ""): Promise<TrackedCompanyResource[]> {
  const query = new URLSearchParams({ page: "1", page_size: "50" });
  if (search.trim()) query.set("search", search.trim());
  const res = await apiClient.get<TrackedCompanyListResponse>(`/tracked-companies?${query.toString()}`);
  return res.data.data || [];
}

export async function verifyTrackedCompany(
  payload: TrackedCompanyVerifyPayload
): Promise<TrackedCompanyVerifyResult> {
  const res = await apiClient.post<{ data: TrackedCompanyVerifyResult }>(
    "/tracked-companies/actions/verify",
    payload
  );
  return res.data.data;
}

export async function createTrackedCompany(
  payload: TrackedCompanyVerifyPayload,
  idempotencyKey?: string
): Promise<TrackedCompanyResource> {
  const key = idempotencyKey || crypto.randomUUID();
  const res = await apiClient.post<{ data: TrackedCompanyResource }>(
    "/tracked-companies",
    payload,
    { idempotencyKey: key }
  );
  return res.data.data;
}

export async function cancelScan(
  scanId: string,
  expectedRevision?: number,
  idempotencyKey?: string
): Promise<ScanResource> {
  const key = idempotencyKey || crypto.randomUUID();
  const res = await apiClient.post<{ data: ScanResource }>(
    `/scans/${encodeURIComponent(scanId)}/actions/cancel`,
    { scan_id: scanId, expected_revision: expectedRevision },
    { idempotencyKey: key }
  );
  return res.data.data;
}

export async function runScanAgain(
  scanId: string,
  scanName?: string,
  expectedRevision?: number,
  idempotencyKey?: string
): Promise<ScanResource> {
  const key = idempotencyKey || crypto.randomUUID();
  const res = await apiClient.post<{ data: ScanResource }>(
    `/scans/${encodeURIComponent(scanId)}/actions/run-again`,
    { scan_id: scanId, scan_name: scanName, expected_revision: expectedRevision },
    { idempotencyKey: key }
  );
  return res.data.data;
}

export async function archiveScans(
  items: Array<{ scan_id: string; expected_revision: number }>,
  idempotencyKey?: string
): Promise<unknown> {
  const key = idempotencyKey || crypto.randomUUID();
  const res = await apiClient.post(
    "/scans/actions/archive",
    { items },
    { idempotencyKey: key }
  );
  return res.data;
}

export async function unarchiveScans(
  items: Array<{ scan_id: string; expected_revision: number }>,
  idempotencyKey?: string
): Promise<unknown> {
  const key = idempotencyKey || crypto.randomUUID();
  const res = await apiClient.post(
    "/scans/actions/unarchive",
    { items },
    { idempotencyKey: key }
  );
  return res.data;
}

export async function previewDeleteScans(scanIds: string[]): Promise<DeletePreviewResult> {
  const res = await apiClient.post<{ data: DeletePreviewResult }>(
    "/scans/actions/delete-archived/preview",
    { scan_ids: scanIds }
  );
  return res.data.data;
}

export async function deleteScans(
  scanIds: string[],
  previewRevision: string,
  idempotencyKey?: string
): Promise<unknown> {
  const key = idempotencyKey || crypto.randomUUID();
  const res = await apiClient.post(
    "/scans/actions/delete-archived",
    { scan_ids: scanIds, preview_revision: previewRevision },
    { idempotencyKey: key }
  );
  return res.data;
}

export async function fetchScanEvents(
  scanId: string,
  cursor?: string | null,
  limit = 200
): Promise<ProcessEventsPage> {
  const query = new URLSearchParams({ limit: String(limit) });
  if (cursor) query.set("cursor", cursor);
  const res = await apiClient.get<{ data: ProcessEventsPage }>(
    `/scans/${encodeURIComponent(scanId)}/events?${query.toString()}`
  );
  return res.data.data;
}

export async function fetchScanJobs(
  scanId: string,
  page = 1,
  pageSize = 20
): Promise<ScanJobsResponse> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  const res = await apiClient.get<ScanJobsResponse>(
    `/scans/${encodeURIComponent(scanId)}/jobs?${query.toString()}`
  );
  return res.data;
}

export async function fetchScanOutputJson(scanId: string): Promise<string> {
  return apiClient.previewText(`/scans/${encodeURIComponent(scanId)}/output`);
}

export function buildRunSourcesHash(scanIds: string[]): string {
  const params = new URLSearchParams();
  for (const scanId of scanIds) params.append("scan_ids", scanId);
  const query = params.toString();
  return query ? `#/runs?${query}` : "#/runs";
}
