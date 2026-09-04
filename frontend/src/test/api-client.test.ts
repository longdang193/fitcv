import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiClient, ApiClientError } from "../lib/api-client";

describe("api-client", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("handles successful JSON requests with same-origin credentials", async () => {
    const mockData = { ready: true, mode: "local" };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({
        "content-type": "application/json",
        ETag: 'W/"123"',
      }),
      json: async () => mockData,
    });

    const response = await apiClient.get<typeof mockData>("/healthz", {
      idempotencyKey: "idem-1",
      ifMatch: 'W/"123"',
    });

    expect(response.status).toBe(200);
    expect(response.data).toEqual(mockData);
    expect(response.etag).toBe('W/"123"');

    const [calledPath, calledInit] = (globalThis.fetch as any).mock.calls[0];
    expect(calledPath).toBe("/healthz");
    expect(calledInit.credentials).toBe("same-origin");
    expect(calledInit.headers["Idempotency-Key"]).toBe("idem-1");
    expect(calledInit.headers["If-Match"]).toBe('W/"123"');
  });

  it("parses standard ApiError envelopes on failure", async () => {
    const errorPayload = {
      error: {
        code: "candidate_profile_not_found",
        message: "Profile was not found",
        action: "Create a new candidate profile",
        field_errors: [{ field: "profile_id", code: "not_found", message: "Missing" }],
      },
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => errorPayload,
    });

    await expect(apiClient.get("/candidate-profiles/missing")).rejects.toSatisfy(
      (err: any) => {
        expect(err).toBeInstanceOf(ApiClientError);
        expect(err.status).toBe(404);
        expect(err.code).toBe("candidate_profile_not_found");
        expect(err.message).toBe("Profile was not found");
        expect(err.action).toBe("Create a new candidate profile");
        expect(err.fieldErrors).toHaveLength(1);
        return true;
      }
    );
  });

  it("handles 204 No Content gracefully", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      headers: new Headers(),
    });

    const response = await apiClient.delete("/bookmarks/item-1");
    expect(response.status).toBe(204);
    expect(response.data).toBeNull();
  });

  it("preserves canonical retryable errors", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      statusText: "Conflict",
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({
        error: {
          code: "cv_preview_pending",
          message: "CV preview is not ready.",
          retryable: true,
        },
      }),
    });

    await expect(apiClient.get("/cv-versions/pending/preview")).rejects.toMatchObject({
      code: "cv_preview_pending",
      retryable: true,
    });
  });
});
