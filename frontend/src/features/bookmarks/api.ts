import { apiClient } from "../../lib/api-client";
import { setJobInterest, clearJobInterest } from "../job-evaluation/api";
import {
  BookmarksPaginationEnvelope,
  SelectionContextPayload,
  SelectionPreviewResponse,
  SelectionExportPayload,
} from "./types";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseInteger(value: unknown, fallback: number, minimum: number): number {
  const parsed = typeof value === "number" ? value : Number.parseInt(String(value), 10);
  return Number.isFinite(parsed) && parsed >= minimum ? Math.floor(parsed) : fallback;
}

export function generateIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "idem_bm_" + Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
}

export async function fetchBookmarks(params?: {
  page?: number;
  page_size?: number;
  stage?: string;
  result?: string;
  search?: string;
}): Promise<BookmarksPaginationEnvelope> {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  if (params?.stage && params.stage !== "all") query.set("stage", params.stage);
  if (params?.result && params.result !== "all") query.set("result", params.result);
  if (params?.search) query.set("search", params.search);
  query.set("sort", "bookmarked_desc");

  const qs = query.toString();
  const path = `/bookmarks${qs ? `?${qs}` : ""}`;
  const res = await apiClient.get<any>(path);
  const payload = isRecord(res.data) ? res.data : {};
  const rawPage = isRecord(payload.page) ? payload.page : {};
  const data = Array.isArray(payload.data) ? payload.data : [];
  const pageSize = parseInteger(payload.page_size ?? rawPage.size ?? params?.page_size, 20, 1);
  const totalItems = parseInteger(payload.total_items ?? rawPage.total_items, data.length, 0);
  const pageNumber = parseInteger(
    rawPage.number ?? payload.page_number ?? (typeof payload.page === "number" ? payload.page : params?.page),
    1,
    1
  );
  return {
    data,
    page: pageNumber,
    page_size: pageSize,
    total_items: totalItems,
    total_pages: parseInteger(
      payload.total_pages ?? rawPage.total_pages,
      Math.max(1, Math.ceil(totalItems / pageSize)),
      1
    ),
    meta: isRecord(payload.meta) ? payload.meta : undefined,
  };
}

export async function updateBookmarkInterest(
  runId: string,
  runJobId: string,
  rating: number | null
): Promise<{ rating: number | null }> {
  if (rating === null || rating <= 0) {
    const res = await clearJobInterest(runId, runJobId);
    return { rating: res.rating ?? null };
  }
  const res = await setJobInterest(runId, runJobId, rating);
  return { rating: res.rating ?? rating };
}

export async function previewBookmarkExport(
  body: SelectionContextPayload
): Promise<SelectionPreviewResponse> {
  const res = await apiClient.post<{ data: SelectionPreviewResponse }>(
    "/bookmarks/actions/export/preview",
    body
  );
  return (res.data as any)?.data || res.data;
}

export async function exportBookmarkSelection(
  body: SelectionExportPayload,
  idempotencyKey = generateIdempotencyKey()
): Promise<void> {
  const res = await apiClient.post<string>("/bookmarks/actions/export", body, {
    idempotencyKey,
    headers: { Accept: "text/csv" },
  });

  const blob = new Blob([res.data], { type: "text/csv" });
  if (typeof window !== "undefined" && typeof document !== "undefined") {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = url;
    a.download = "fitcv-bookmarks.csv";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    }, 100);
  }
}

export async function removeBookmarkSelection(
  body: SelectionContextPayload,
  idempotencyKey = generateIdempotencyKey()
): Promise<{ removed_count: number }> {
  const res = await apiClient.post<{ data: { removed_count: number } }>(
    "/bookmarks/actions/remove",
    body,
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}
