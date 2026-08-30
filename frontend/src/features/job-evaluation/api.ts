import { apiClient } from "../../lib/api-client";
import {
  SelectionContextPayload,
  SelectionPreviewResponse,
  SelectionExportPayload,
  InterestUpdateResult,
  BookmarkUpdateResult,
} from "./types";

export const RATING_CONTRACT_REVISION = "application-interest-v1";

export async function setJobBookmark(
  runId: string,
  runJobId: string
): Promise<BookmarkUpdateResult> {
  const res = await apiClient.put<{ data: BookmarkUpdateResult }>(
    `/runs/${encodeURIComponent(runId)}/jobs/${encodeURIComponent(runJobId)}/bookmark`
  );
  return (res.data as any)?.data || res.data;
}

export async function clearJobBookmark(
  runId: string,
  runJobId: string
): Promise<BookmarkUpdateResult> {
  const res = await apiClient.delete<{ data: BookmarkUpdateResult }>(
    `/runs/${encodeURIComponent(runId)}/jobs/${encodeURIComponent(runJobId)}/bookmark`
  );
  return (res.data as any)?.data || res.data;
}

export async function setJobInterest(
  runId: string,
  runJobId: string,
  rating: number,
  revision = RATING_CONTRACT_REVISION
): Promise<InterestUpdateResult> {
  const res = await apiClient.put<{ data: InterestUpdateResult }>(
    `/runs/${encodeURIComponent(runId)}/jobs/${encodeURIComponent(runJobId)}/interest`,
    {
      rating,
      rating_contract_revision: revision,
    }
  );
  return (res.data as any)?.data || res.data;
}

export async function clearJobInterest(
  runId: string,
  runJobId: string
): Promise<InterestUpdateResult> {
  const res = await apiClient.delete<{ data: InterestUpdateResult }>(
    `/runs/${encodeURIComponent(runId)}/jobs/${encodeURIComponent(runJobId)}/interest`
  );
  return (res.data as any)?.data || res.data;
}

export async function previewRunJobExport(
  runId: string,
  body: SelectionContextPayload
): Promise<SelectionPreviewResponse> {
  const res = await apiClient.post<{ data: SelectionPreviewResponse }>(
    `/runs/${encodeURIComponent(runId)}/jobs/actions/export/preview`,
    body
  );
  return (res.data as any)?.data || res.data;
}

export async function exportRunJobSelection(
  runId: string,
  body: SelectionExportPayload,
  idempotencyKey?: string
): Promise<void> {
  const key =
    idempotencyKey ||
    "idem_exp_" + Math.random().toString(36).substring(2, 10) + Date.now().toString(36);

  const res = await fetch(`/runs/${encodeURIComponent(runId)}/jobs/actions/export`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/csv",
      "Idempotency-Key": key,
    },
    credentials: "same-origin",
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new Error(`Export failed with status ${res.status}`);
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.style.display = "none";
  a.href = url;
  a.download = `fitcv-run-${runId}-jobs.csv`;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }, 100);
}
