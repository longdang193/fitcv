import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchCvVersions,
  fetchCvPreview,
  downloadCvVersion,
  regenerateCvVersion,
  submitCvReviewDecision,
} from "./api";

describe("CV Review route and contracts", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches ordered CV versions for a run job", async () => {
    const mockVersions = [
      {
        version_id: "cv-ver-2",
        run_id: "run-1",
        run_job_id: "job-1",
        job_url: "https://job.url",
        ordinal: 2,
        generation_status: "generated",
        content_checksum: "sha256-abc",
        content_length: 120,
        media_type: "text/markdown; charset=utf-8",
        filename: "cv-ver-2.md",
        parent_cv_version_id: "cv-ver-1",
        created_at: "2026-08-30T10:00:00Z",
        review_state: "approved",
        capabilities: { download: true, preview: true, regenerate: true },
      },
      {
        version_id: "cv-ver-1",
        run_id: "run-1",
        run_job_id: "job-1",
        job_url: "https://job.url",
        ordinal: 1,
        generation_status: "generated",
        content_checksum: "sha256-def",
        content_length: 100,
        media_type: "text/markdown; charset=utf-8",
        filename: "cv-ver-1.md",
        parent_cv_version_id: null,
        created_at: "2026-08-30T09:00:00Z",
        review_state: "none",
        capabilities: { download: true, preview: true, regenerate: true },
      },
    ];

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ data: mockVersions }),
    } as any);

    const data = await fetchCvVersions("run-1", "job-1");
    expect(data).toHaveLength(2);
    expect(data[0].version_id).toBe("cv-ver-2");
    expect(data[0].ordinal).toBe(2);
    expect(data[0].parent_cv_version_id).toBe("cv-ver-1");
  });

  it("fetches preview bytes and validates checksum/media-type headers", async () => {
    const sampleMarkdown = "# Jane Doe\nSoftware Engineer";
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({
        "content-type": "text/markdown; charset=utf-8",
        "etag": '"sha-999"',
        "content-length": String(sampleMarkdown.length),
        "x-cv-version-id": "cv-ver-1",
        "content-disposition": "inline",
      }),
      text: async () => sampleMarkdown,
    } as any);

    const preview = await fetchCvPreview("cv-ver-1");
    expect(preview.version_id).toBe("cv-ver-1");
    expect(preview.content).toBe(sampleMarkdown);
    expect(preview.media_type).toContain("text/markdown");
    expect(preview.checksum).toBe("sha-999");
  });

  it("handles retryable 409 pending preview states", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({
        error: {
          code: "artifact_not_available",
          message: "CV preview is not available for this version.",
          retryable: true,
          action: "Wait for generation and retry.",
        },
      }),
    } as any);

    await expect(fetchCvPreview("cv-pending")).rejects.toMatchObject({
      status: 409,
      code: "artifact_not_available",
      retryable: true,
      action: "Wait for generation and retry.",
    });
  });

  it("triggers CV version download", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({
        "content-type": "text/markdown",
        "content-disposition": 'attachment; filename="cv-custom.md"',
      }),
      blob: async () => new Blob(["# CV"]),
    } as any);

    await expect(downloadCvVersion("cv-123")).resolves.toBeUndefined();
  });

  it("requests CV regeneration with idempotency key", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({
        data: {
          action_id: "act-123",
          status: "queued",
          queue_job_id: "qjob-456",
        },
      }),
    } as any);

    const res = await regenerateCvVersion("run-1", "job-1", "cv-ver-1", "idem-key-1");
    expect(res.action_id).toBe("act-123");
    expect(res.status).toBe("queued");
  });

  it("preserves and updates returned ETag during review mutation with CAS If-Match", async () => {
    let lastIfMatch: string | null = null;
    globalThis.fetch = vi.fn().mockImplementation(async (_url: string, opts: any) => {
      lastIfMatch = opts?.headers?.["If-Match"] || null;
      return {
        ok: true,
        status: 200,
        headers: new Headers({
          "content-type": "application/json",
          "etag": '"etag-updated-rev-2"',
        }),
        json: async () => ({
          data: {
            version_id: "cv-ver-1",
            review_state: "approved",
            content_checksum: "etag-updated-rev-2",
          },
        }),
      };
    });

    // First mutation using initial ETag
    const firstMutation = await submitCvReviewDecision(
      "run-1",
      "job-1",
      "cv-ver-1",
      { review_state: "approved", notes: "First review" },
      '"etag-rev-1"'
    );

    expect(lastIfMatch).toBe('"etag-rev-1"');
    expect(firstMutation.etag).toBe('"etag-updated-rev-2"');

    // Second mutation using newly updated ETag
    await submitCvReviewDecision(
      "run-1",
      "job-1",
      "cv-ver-1",
      { review_state: "stretch", notes: "Updated review" },
      firstMutation.etag
    );

    expect(lastIfMatch).toBe('"etag-updated-rev-2"');
  });
});
