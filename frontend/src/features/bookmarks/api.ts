import { apiClient } from "../../lib/api-client";
import {
  BookmarksPaginationEnvelope,
  SelectionContextPayload,
  SelectionPreviewResponse,
  SelectionExportPayload,
} from "./types";

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
  const res = await apiClient.get<BookmarksPaginationEnvelope>(path);
  return res.data;
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
  const res = await fetch("/bookmarks/actions/export", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/csv",
      "Idempotency-Key": idempotencyKey,
    },
    credentials: "same-origin",
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new Error(`Export bookmarks failed with status ${res.status}`);
  }

  const blob = await res.blob();
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
