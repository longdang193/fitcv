import { apiClient } from "../../lib/api-client";
import { PersonalizationResource, PersonalizationPatchPayload } from "./types";

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
