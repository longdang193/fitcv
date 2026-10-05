import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchCvVersions,
  fetchCvPreview,
  downloadCvVersion,
  regenerateCvVersion,
  fetchCvReviewResource,
  applyCvReviewAction,
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

  it("uses canonical review resource and action routes with idempotency", async () => {
    const requests: Array<{ url: string; options?: any }> = [];
    globalThis.fetch = vi.fn().mockImplementation(async (url: string, options?: any) => {
      requests.push({ url, options });
      return {
        ok: true,
        status: url.endsWith("/actions") ? 202 : 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          data: {
            run_id: "run-1",
            run_job_id: "job-1",
             status: "review_required",
             review_revision: "revision-1",
             uncertainties: [{ uncertainty_id: "u-1", resolution_key: "skill:sql" }],
            allowed_actions: ["RESOLVE_WITH_ANSWER"],
          },
        }),
      };
    });

    const resource = await fetchCvReviewResource("run-1", "job-1");
    expect(resource.status).toBe("review_required");
    await applyCvReviewAction("run-1", "job-1", {
      review_item_id: "review-1",
      uncertainty_id: "u-1",
       resolution_key: "skill:sql",
       review_revision: "revision-1",
       action: "RESOLVE_WITH_ANSWER",
      answer_text: "Used SQL for four years.",
    }, "idem-review-1");
    expect(requests[0].url).toBe("/runs/run-1/jobs/job-1/cv-review");
    expect(requests[1].url).toBe("/runs/run-1/jobs/job-1/cv-review/actions");
    expect(requests[1].options.headers["Idempotency-Key"]).toBe("idem-review-1");
    expect(JSON.parse(requests[1].options.body).review_revision).toBe("revision-1");
  });

  it("uses root API routes for preview and download", async () => {
    let requestedUrl = "";
    globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
      requestedUrl = url;
      return {
        ok: true,
        status: 200,
        headers: new Headers({
          "content-type": "text/markdown; charset=utf-8",
          "etag": '"sha-999"',
          "content-length": "10",
          "x-cv-version-id": "cv-ver-base",
        }),
        text: async () => "content",
        blob: async () => new Blob(["content"]),
      };
    });

    await fetchCvPreview("cv-ver-base");
    expect(requestedUrl).toBe("/cv-versions/cv-ver-base/preview");

    await downloadCvVersion("cv-ver-base");
    expect(requestedUrl).toBe("/cv-versions/cv-ver-base/download");
  });
});
