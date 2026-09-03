import { apiClient } from "../../lib/api-client";
import {
  CandidateProfile,
  CandidateProfileDetail,
  CandidateProfileReviewOperation,
  ConfirmationResource,
  CreationAttempt,
  FieldSchema,
  ReviewResource,
  SourceBlock,
} from "./types";

export interface PaginationEnvelope<T> {
  data: T[];
  page: number;
  page_size: number;
  total_items: number;
  meta?: {
    active_count?: number;
    archived_count?: number;
    [key: string]: unknown;
  };
}

export function generateIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "idem_" + Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
}

let cachedFieldSchema: { schema: FieldSchema; etag?: string | null } | null = null;

export async function fetchFieldSchema(force = false): Promise<FieldSchema> {
  if (!force && cachedFieldSchema) {
    return cachedFieldSchema.schema;
  }

  const options = cachedFieldSchema?.etag
    ? { ifNoneMatch: cachedFieldSchema.etag }
    : undefined;

  try {
    const res = await apiClient.get<{ data: FieldSchema }>("/candidate-profile-field-schema", options);
    if (res.status === 304 && cachedFieldSchema) {
      return cachedFieldSchema.schema;
    }
    const schema = (res.data as any)?.data || res.data;
    cachedFieldSchema = { schema, etag: res.etag };
    return schema;
  } catch (err: any) {
    if (cachedFieldSchema) {
      return cachedFieldSchema.schema;
    }
    throw err;
  }
}

export async function fetchCreationAttempts(params?: {
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginationEnvelope<CreationAttempt>> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));

  const qs = query.toString();
  const path = `/candidate-profile-creation-attempts${qs ? `?${qs}` : ""}`;
  const res = await apiClient.get<PaginationEnvelope<CreationAttempt>>(path);
  return res.data;
}

export async function createCreationAttempt(
  profileName: string,
  file: File,
  idempotencyKey = generateIdempotencyKey()
): Promise<CreationAttempt> {
  const formData = new FormData();
  formData.append("profile_name", profileName);
  formData.append("profile_file", file);

  const res = await apiClient.post<{ data: CreationAttempt }>(
    "/candidate-profile-creation-attempts",
    formData,
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function fetchCreationAttempt(attemptId: string): Promise<CreationAttempt> {
  const res = await apiClient.get<{ data: CreationAttempt }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}`
  );
  return (res.data as any)?.data || res.data;
}

export async function fetchSourceBlock(
  attemptId: string,
  sourceBlockId: string
): Promise<SourceBlock> {
  const res = await apiClient.get<{ data: SourceBlock }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(
      attemptId
    )}/source-blocks/${encodeURIComponent(sourceBlockId)}`
  );
  return (res.data as any)?.data || res.data;
}

export async function downloadAttemptSource(attemptId: string, fallbackFilename?: string): Promise<void> {
  return apiClient.download(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}/source`,
    fallbackFilename
  );
}

export async function fetchBaselineReview(attemptId: string): Promise<ReviewResource> {
  const res = await apiClient.get<{ data: ReviewResource }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}/baseline`
  );
  return (res.data as any)?.data || res.data;
}

export async function patchBaselineReview(
  attemptId: string,
  expectedRevision: number,
  operations: CandidateProfileReviewOperation[],
  idempotencyKey = generateIdempotencyKey()
): Promise<ReviewResource> {
  const res = await apiClient.patch<{ data: ReviewResource }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}/baseline`,
    {
      expected_revision: expectedRevision,
      operations,
    },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function regenerateBaselineReview(
  attemptId: string,
  expectedRevision: number,
  targets: string[],
  idempotencyKey = generateIdempotencyKey()
): Promise<CreationAttempt | ReviewResource> {
  const res = await apiClient.post<{ data: CreationAttempt | ReviewResource }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}/baseline/actions/regenerate`,
    {
      expected_revision: expectedRevision,
      targets,
    },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function undoBaselineRegeneration(
  attemptId: string,
  expectedRevision: number,
  idempotencyKey = generateIdempotencyKey()
): Promise<ReviewResource> {
  const res = await apiClient.post<{ data: ReviewResource }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(
      attemptId
    )}/baseline/actions/undo-regeneration`,
    { expected_revision: expectedRevision },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function approveBaselineReview(
  attemptId: string,
  expectedRevision: number,
  expectedFingerprint: string,
  idempotencyKey = generateIdempotencyKey()
): Promise<CreationAttempt> {
  const res = await apiClient.post<{ data: CreationAttempt }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}/baseline/actions/approve`,
    {
      expected_revision: expectedRevision,
      expected_fingerprint: expectedFingerprint,
    },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function fetchDerivedReview(attemptId: string): Promise<ReviewResource> {
  const res = await apiClient.get<{ data: ReviewResource }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}/derived`
  );
  return (res.data as any)?.data || res.data;
}

export async function patchDerivedReview(
  attemptId: string,
  expectedRevision: number,
  operations: CandidateProfileReviewOperation[],
  idempotencyKey = generateIdempotencyKey()
): Promise<ReviewResource> {
  const res = await apiClient.patch<{ data: ReviewResource }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}/derived`,
    {
      expected_revision: expectedRevision,
      operations,
    },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function regenerateDerivedReview(
  attemptId: string,
  expectedRevision: number,
  targets: string[],
  idempotencyKey = generateIdempotencyKey()
): Promise<CreationAttempt | ReviewResource> {
  const res = await apiClient.post<{ data: CreationAttempt | ReviewResource }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}/derived/actions/regenerate`,
    {
      expected_revision: expectedRevision,
      targets,
    },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function undoDerivedRegeneration(
  attemptId: string,
  expectedRevision: number,
  idempotencyKey = generateIdempotencyKey()
): Promise<ReviewResource> {
  const res = await apiClient.post<{ data: ReviewResource }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(
      attemptId
    )}/derived/actions/undo-regeneration`,
    { expected_revision: expectedRevision },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function approveDerivedReview(
  attemptId: string,
  expectedRevision: number,
  expectedFingerprint: string,
  expectedBaselineFingerprint: string,
  idempotencyKey = generateIdempotencyKey()
): Promise<CreationAttempt> {
  const res = await apiClient.post<{ data: CreationAttempt }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}/derived/actions/approve`,
    {
      expected_revision: expectedRevision,
      expected_fingerprint: expectedFingerprint,
      expected_baseline_fingerprint: expectedBaselineFingerprint,
    },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function fetchConfirmation(attemptId: string): Promise<ConfirmationResource> {
  const res = await apiClient.get<{ data: ConfirmationResource }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}/confirmation`
  );
  return (res.data as any)?.data || res.data;
}

export async function confirmProfile(
  attemptId: string,
  expectedRevision: number,
  expectedBaselineFingerprint: string,
  expectedDerivedFingerprint: string,
  expectedConfirmationFingerprint: string,
  idempotencyKey = generateIdempotencyKey()
): Promise<{ profile_id: string; [key: string]: unknown }> {
  const res = await apiClient.post<{ data: { profile_id: string; [key: string]: unknown } }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}/actions/confirm`,
    {
      expected_revision: expectedRevision,
      expected_baseline_fingerprint: expectedBaselineFingerprint,
      expected_derived_fingerprint: expectedDerivedFingerprint,
      expected_confirmation_fingerprint: expectedConfirmationFingerprint,
    },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function retryAttempt(
  attemptId: string,
  expectedRevision: number,
  idempotencyKey = generateIdempotencyKey()
): Promise<CreationAttempt> {
  const res = await apiClient.post<{ data: CreationAttempt }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}/actions/retry`,
    { expected_revision: expectedRevision },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function discardCreationAttempt(
  attemptId: string,
  expectedRevision: number,
  idempotencyKey = generateIdempotencyKey()
): Promise<{ attempt_id: string; discarded: boolean }> {
  const res = await apiClient.post<{ data: { attempt_id: string; discarded: boolean } }>(
    `/candidate-profile-creation-attempts/${encodeURIComponent(attemptId)}/actions/discard`,
    { expected_revision: expectedRevision },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function fetchProfiles(params?: {
  view?: "active" | "archived";
  lifecycle?: "active" | "archived";
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginationEnvelope<CandidateProfile>> {
  const query = new URLSearchParams();
  const viewParam = params?.view || params?.lifecycle;
  if (viewParam) query.set("view", viewParam);
  if (params?.search) query.set("search", params.search);
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));

  const qs = query.toString();
  const path = `/candidate-profiles${qs ? `?${qs}` : ""}`;
  const res = await apiClient.get<PaginationEnvelope<CandidateProfile>>(path);
  return res.data;
}

export function normalizeCandidateProfileDetail(raw: CandidateProfileDetail): CandidateProfileDetail {
  const canonical = raw.canonical || raw.profile?.canonical || raw.overview || {};
  return {
    ...raw,
    canonical,
  };
}

export async function fetchProfileDetail(profileId: string): Promise<CandidateProfileDetail> {
  const res = await apiClient.get<{ data: CandidateProfileDetail }>(
    `/candidate-profiles/${encodeURIComponent(profileId)}`
  );
  const data = (res.data as any)?.data || res.data;
  return normalizeCandidateProfileDetail(data);
}

export async function createEditAttempt(
  profileId: string,
  idempotencyKey = generateIdempotencyKey()
): Promise<CreationAttempt> {
  const res = await apiClient.post<{ data: CreationAttempt }>(
    `/candidate-profiles/${encodeURIComponent(profileId)}/actions/edit`,
    {},
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function updateProfile(
  profileId: string,
  expectedRevision: number,
  profileName?: string,
  canonical?: Record<string, any>,
  idempotencyKey = generateIdempotencyKey()
): Promise<CandidateProfileDetail> {
  const res = await apiClient.put<{ data: CandidateProfileDetail }>(
    `/candidate-profiles/${encodeURIComponent(profileId)}`,
    {
      expected_revision: expectedRevision,
      profile_name: profileName,
      canonical,
    },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function archiveProfile(
  profileId: string,
  expectedRevision: number,
  idempotencyKey = generateIdempotencyKey()
): Promise<CandidateProfile> {
  const res = await apiClient.post<{ data: CandidateProfile }>(
    `/candidate-profiles/${encodeURIComponent(profileId)}/actions/archive`,
    { expected_revision: expectedRevision },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function restoreProfile(
  profileId: string,
  expectedRevision: number,
  idempotencyKey = generateIdempotencyKey()
): Promise<CandidateProfile> {
  const res = await apiClient.post<{ data: CandidateProfile }>(
    `/candidate-profiles/${encodeURIComponent(profileId)}/actions/restore`,
    { expected_revision: expectedRevision },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function deleteProfile(
  profileId: string,
  expectedRevision: number,
  idempotencyKey = generateIdempotencyKey()
): Promise<{ profile_id: string; deleted: boolean }> {
  const res = await apiClient.post<{ data: { profile_id: string; deleted: boolean } }>(
    `/candidate-profiles/${encodeURIComponent(profileId)}/actions/delete`,
    { expected_revision: expectedRevision },
    { idempotencyKey }
  );
  return (res.data as any)?.data || res.data;
}

export async function waitForAttemptTransition(
  attemptId: string,
  targetActions: string | string[],
  maxAttempts = 60,
  initialPollMs = 800
): Promise<CreationAttempt> {
  const targets = Array.isArray(targetActions) ? targetActions : [targetActions];
  let delay = initialPollMs;

  for (let i = 0; i < maxAttempts; i++) {
    const attempt = await fetchCreationAttempt(attemptId);
    if (targets.includes(attempt.next_action)) {
      return attempt;
    }
    if (attempt.creation_status === "failed") {
      return attempt;
    }
    const pollDelay =
      typeof attempt.poll_after_ms === "number" && attempt.poll_after_ms > 0
        ? attempt.poll_after_ms
        : delay;
    await new Promise((resolve) => setTimeout(resolve, pollDelay));
  }
  return fetchCreationAttempt(attemptId);
}
