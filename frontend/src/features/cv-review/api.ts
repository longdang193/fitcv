import { apiClient, getCsrfToken, ApiClientError } from "../../lib/api-client";
import {
  CvVersionResource,
  CvPreviewResult,
  CvRegenerateResponseData,
  CvReviewActionRequest,
  CvReviewResource,
} from "./types";

function unwrapData<T>(payload: T | { data: T }): T {
  return payload && typeof payload === "object" && "data" in payload
    ? (payload as { data: T }).data
    : payload as T;
}

/**
 * Fetch ordered list of CV versions for a specific run job
 */
export async function fetchCvVersions(
  runId: string,
  runJobId: string
): Promise<CvVersionResource[]> {
  const res = await apiClient.get<{ data: CvVersionResource[] } | CvVersionResource[]>(
    `/runs/${encodeURIComponent(runId)}/jobs/${encodeURIComponent(runJobId)}/cvs`
  );
  const payload = unwrapData(res.data);
  return Array.isArray(payload) ? payload : [];
}

/**
 * Fetch raw preview bytes for an immutable CV version.
 * Returns text content, media type, and checksum validation headers.
 */
export async function fetchCvPreview(versionId: string): Promise<CvPreviewResult> {
  const csrf = getCsrfToken();
  const headers: Record<string, string> = {
    Accept: "text/markdown, text/plain, */*",
  };
  if (csrf) {
    headers["X-FitCV-CSRF"] = csrf;
  }

  const response = await fetch(`/cv-versions/${encodeURIComponent(versionId)}/preview`, {
    method: "GET",
    credentials: "same-origin",
    headers,
  });

  if (!response.ok) {
    let errorCode = `http_${response.status}`;
    let errorMessage = response.statusText || `Request failed with status ${response.status}`;
    let action: string | undefined;
    let retryable: boolean | undefined;

    try {
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const payload = await response.json();
        if (payload && payload.error) {
          errorCode = payload.error.code || errorCode;
          errorMessage = payload.error.message || errorMessage;
          action = payload.error.action;
          retryable = payload.error.retryable;
        }
      } else {
        const text = await response.text();
        if (text) {
          errorMessage = text;
        }
      }
    } catch {
      // body parse fail
    }

    const error = new ApiClientError(
      response.status,
      errorCode,
      errorMessage,
      action,
      undefined,
      { retryable }
    );
    (error as any).retryable = retryable;
    throw error;
  }

  const content = await response.text();
  const mediaType = response.headers.get("content-type") || "text/markdown; charset=utf-8";
  const checksumHeader = response.headers.get("etag") || "";
  const checksum = checksumHeader.replace(/^"|"$/g, "");
  const contentLength = Number(response.headers.get("content-length")) || content.length;
  const returnedVersionId = response.headers.get("x-cv-version-id") || versionId;

  return {
    version_id: returnedVersionId,
    content,
    media_type: mediaType,
    checksum,
    content_length: contentLength,
  };
}

/**
 * Trigger attachment download of CV version
 */
export async function downloadCvVersion(
  versionId: string,
  fallbackFilename?: string
): Promise<void> {
  await apiClient.download(
    `/cv-versions/${encodeURIComponent(versionId)}/download`,
    fallbackFilename || `${versionId}.md`
  );
}

/**
 * Request regeneration of CV for a run job with idempotent key
 */
export async function regenerateCvVersion(
  runId: string,
  runJobId: string,
  parentCvVersionId?: string | null,
  idempotencyKey?: string
): Promise<CvRegenerateResponseData> {
  const key = idempotencyKey || crypto.randomUUID();
  const res = await apiClient.post<{ data: CvRegenerateResponseData } | CvRegenerateResponseData>(
    `/runs/${encodeURIComponent(runId)}/jobs/${encodeURIComponent(runJobId)}/cvs/actions/regenerate`,
    { parent_cv_version_id: parentCvVersionId || null },
    { idempotencyKey: key }
  );
  return unwrapData(res.data);
}

/**
 * Submit review decision and notes for a CV version with CAS ETag support.
 * Preserves and returns updated ETag for optimistic concurrency.
 */
export async function fetchCvReviewResource(
  runId: string,
  runJobId: string
): Promise<CvReviewResource> {
  const res = await apiClient.get<{ data: CvReviewResource } | CvReviewResource>(
    `/runs/${encodeURIComponent(runId)}/jobs/${encodeURIComponent(runJobId)}/cv-review`
  );
  return unwrapData(res.data);
}

export async function applyCvReviewAction(
  runId: string,
  runJobId: string,
  action: CvReviewActionRequest,
  idempotencyKey?: string
): Promise<CvReviewResource & { action_id?: string; regeneration_job_id?: string | null }> {
  const res = await apiClient.post<
    { data: CvReviewResource & { action_id?: string; regeneration_job_id?: string | null } }
    | (CvReviewResource & { action_id?: string; regeneration_job_id?: string | null })
  >(
    `/runs/${encodeURIComponent(runId)}/jobs/${encodeURIComponent(runJobId)}/cv-review/actions`,
    action,
    { idempotencyKey: idempotencyKey || crypto.randomUUID() }
  );
  return unwrapData(res.data);
}
