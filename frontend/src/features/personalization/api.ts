import { apiClient } from "../../lib/api-client";
import {
  PersonalizationCandidateActivationPayload,
  PersonalizationCandidatePayload,
  PersonalizationOptimizationResource,
  PersonalizationPatchPayload,
  PersonalizationResource,
} from "./types";

export async function fetchPersonalization(): Promise<{
  resource: PersonalizationResource;
  etag?: string | null;
}> {
  const res = await apiClient.get<{ data: PersonalizationResource }>("/personalization");
  const resource = (res.data as any)?.data || res.data;
  return { resource, etag: res.etag };
}

export async function patchPersonalization(
  payload: PersonalizationPatchPayload
): Promise<{
  resource: PersonalizationResource;
  etag?: string | null;
}> {
  const res = await apiClient.patch<{ data: PersonalizationResource }>(
    "/personalization",
    payload
  );
  const resource = (res.data as any)?.data || res.data;
  return { resource, etag: res.etag };
}

export async function fetchPersonalizationOptimization(): Promise<PersonalizationOptimizationResource> {
  const res = await apiClient.get<{ data: PersonalizationOptimizationResource }>(
    "/personalization/optimization"
  );
  return (res.data as any)?.data || res.data;
}

export async function createPersonalizationCandidate(
  payload: PersonalizationCandidatePayload
): Promise<PersonalizationOptimizationResource> {
  const res = await apiClient.post<{ data: PersonalizationOptimizationResource }>(
    "/personalization/optimization/candidate",
    payload
  );
  return (res.data as any)?.data || res.data;
}

export async function activatePersonalizationCandidate(
  snapshotId: string,
  payload: PersonalizationCandidateActivationPayload
): Promise<PersonalizationOptimizationResource> {
  const res = await apiClient.post<{ data: PersonalizationOptimizationResource }>(
    `/personalization/optimization/candidates/${encodeURIComponent(snapshotId)}/activate`,
    payload
  );
  return (res.data as any)?.data || res.data;
}
