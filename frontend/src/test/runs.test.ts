import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  fetchRuns,
  fetchRun,
  fetchRunStages,
  fetchRunJobs,
  fetchRunEvents,
  triggerRun,
  cancelRun,
  archiveRun,
  unarchiveRun,
  previewDeleteArchivedRuns,
  deleteArchivedRuns,
  downloadDebugBundle,
  exportRunJobsCsv,
  generateIdempotencyKey,
  extractRequiredJobSkills,
} from "../features/runs/api";
import { apiClient } from "../lib/api-client";
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";
import { parseRunSourceIds } from "../features/runs/route";
import { PROVIDER_SETTINGS_HREF, RunErrorAction } from "../features/runs/new-run-dialog";
import { isDistinctStatusDetail, isRunTerminal } from "../features/runs/runs-list";

describe("runs feature route and api slice", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("treats only completed run statuses as terminal", () => {
    expect(isRunTerminal("succeeded")).toBe(true);
    expect(isRunTerminal("failed")).toBe(true);
    expect(isRunTerminal("cancelled")).toBe(true);
    expect(isRunTerminal("queued")).toBe(false);
    expect(isRunTerminal("running")).toBe(false);
    expect(isRunTerminal("awaiting_continue")).toBe(false);
    expect(isRunTerminal("cancelling")).toBe(false);
  });

  it("hides status details that duplicate badge labels", () => {
    expect(isDistinctStatusDetail("succeeded", "Succeeded")).toBe(false);
    expect(isDistinctStatusDetail(" Succeeded ", "Succeeded")).toBe(false);
    expect(isDistinctStatusDetail("Processing screening", "Running")).toBe(true);
    expect(isDistinctStatusDetail(null, "Succeeded")).toBe(false);
  });

  it("registers and matches runs feature route", () => {
    const routes = discoverFeatureRoutes();
    const runRoute = routes.find((r) => r.id === "runs");
    expect(runRoute).toBeDefined();
    expect(runRoute?.path).toBe("#/runs");
    expect(runRoute?.group).toBe("workspace");

    const matched = matchRoute("#/runs?view=archived", routes);
    expect(matched.id).toBe("runs");

    const matchedDetail = matchRoute("#/runs?run_id=run-101", routes);
    expect(matchedDetail.id).toBe("runs");
  });

  it("parses scan IDs handed off from Scan outputs", () => {
    expect(parseRunSourceIds("#/runs?scan_ids=scan-1&scan_ids=scan%2F2&scan_ids=%20"))
      .toEqual(["scan-1", "scan/2"]);
  });

  it("generates unique idempotency keys", () => {
    const key1 = generateIdempotencyKey();
    const key2 = generateIdempotencyKey();
    expect(key1).toBeTruthy();
    expect(key2).toBeTruthy();
    expect(key1).not.toBe(key2);
  });

  it("links run readiness actions to provider settings and preserves action text", () => {
    const markup = renderToStaticMarkup(
      React.createElement(RunErrorAction, {
        code: "local_readiness_required",
        action: "Configure an API provider before launching a run.",
      })
    );

    expect(markup).toBe(
      `<a href="${PROVIDER_SETTINGS_HREF}">Configure an API provider before launching a run.</a>`
    );
    expect(
      renderToStaticMarkup(
        React.createElement(RunErrorAction, { code: "local_readiness_required", action: null })
      )
    ).toBe(`<a href="${PROVIDER_SETTINGS_HREF}">Open provider settings</a>`);
    expect(
      renderToStaticMarkup(
        React.createElement(RunErrorAction, { code: "other_error", action: "Retry the request." })
      )
    ).toBe(`<a href="${PROVIDER_SETTINGS_HREF}">Retry the request.</a>`);
  });

  it("fetches runs collection with query parameters", async () => {
    const mockResponse = {
      data: {
        data: [
          {
            run_id: "run-001",
            run_name: "Production Run",
            backend_status: "running",
            display_status: "Running",
            status_detail: "Processing screening",
            created_at: "2026-08-30T12:00:00Z",
            counts: { total: 10, passed: 4, rejected: 1, skipped: 0, cvs_generated: 0 },
            progress: { completed: 5, total: 10 },
            capabilities: {
              inspect: true,
              cancel: true,
              archive: false,
              unarchive: false,
              delete: false,
              export: true,
            },
          },
        ],
        page: { number: 1, size: 20, total_items: 1, total_pages: 1 },
        meta: { active_count: 1, archived_count: 0, view: "active", search: "", server_time: "2026-08-30T12:00:00Z" },
      },
      status: 200,
    };

    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockResponse as any);

    const result = await fetchRuns({
      view: "active",
      search: "Production",
      page: 1,
      page_size: 20,
    });

    expect(getSpy).toHaveBeenCalledWith("/runs?view=active&search=Production&page=1&page_size=20");
    expect(result.data.length).toBe(1);
    expect(result.data[0].run_id).toBe("run-001");
    expect(result.data[0].counts.total).toBe(10);
  });

  it("normalizes canonical nested pagination for runs", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: {
        data: [{ run_id: "run-1" }],
        page: { number: 2, size: 20, total_items: 21, total_pages: 2 },
        meta: { active_count: 21, archived_count: 0, view: "active", search: "", server_time: "2026-09-04T00:00:00Z" },
      },
      status: 200,
    } as any);

    const result = await fetchRuns({ view: "active", page: 2, page_size: 20 });
    expect(result.page).toBe(2);
    expect(result.page_size).toBe(20);
    expect(result.total_items).toBe(21);
    expect(result.total_pages).toBe(2);
  });

  it("fetches single run detail", async () => {
    const mockDetail = {
      data: {
        run_id: "run-002",
        run_name: "Single Run Detail",
        backend_status: "succeeded",
        display_status: "Succeeded",
        created_at: "2026-08-30T12:00:00Z",
        counts: { total: 5, passed: 5, rejected: 0, skipped: 0, cvs_generated: 5 },
        progress: { completed: 5, total: 5 },
        capabilities: {
          inspect: true,
          cancel: false,
          archive: true,
          unarchive: false,
          delete: false,
          export: true,
        },
        stages: [
          { stage_id: "enrichment", label: "Enrichment", ordinal: 1, status: "succeeded" },
          { stage_id: "screening", label: "Screening", ordinal: 2, status: "succeeded" },
          { stage_id: "shortlisting", label: "Shortlisting", ordinal: 3, status: "succeeded" },
          { stage_id: "ranking", label: "Ranking", ordinal: 4, status: "succeeded" },
          { stage_id: "cv-analysis", label: "CV Analysis", ordinal: 5, status: "succeeded" },
          { stage_id: "cv-generation", label: "CV Generation", ordinal: 6, status: "succeeded" },
        ],
      },
      status: 200,
    };

    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockDetail as any);

    const res = await fetchRun("run-002");
    expect(getSpy).toHaveBeenCalledWith("/runs/run-002");
    expect(res.run_id).toBe("run-002");
    expect(res.stages?.length).toBe(6);
  });

  it("fetches run stages endpoint", async () => {
    const mockStages = {
      data: [
        { stage_id: "enrichment", label: "Enrichment", ordinal: 1, status: "succeeded" },
        { stage_id: "screening", label: "Screening", ordinal: 2, status: "running" },
      ],
      status: 200,
    };

    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockStages as any);

    const res = await fetchRunStages("run-003");
    expect(getSpy).toHaveBeenCalledWith("/runs/run-003/stages");
    expect(res.length).toBe(2);
  });

  it("fetches run jobs with filter parameters", async () => {
    const mockJobsResponse = {
      data: {
        data: [
          {
            run_job_id: "job-1",
            job_id: "ext-1",
            title: "Software Engineer",
            company: "Acme",
            current_stage_id: "screening",
            status: "passed",
            result_bucket: "passed",
            bookmarked: false,
            rating: 5,
            rating_contract_revision: "application-interest-v1",
            cv_versions_count: 1,
          },
        ],
        page: { number: 1, size: 50, total_items: 1, total_pages: 1 },
        meta: {
          run_id: "run-004",
          stage: "screening",
          result_bucket: "passed",
          search: "Software",
          total_evaluated: 1,
          passed: 1,
          rejected: 0,
          skipped: 0,
        },
      },
      status: 200,
    };

    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockJobsResponse as any);

    const res = await fetchRunJobs("run-004", {
      page: 1,
      page_size: 50,
      stage: "screening",
      result_bucket: "passed",
      search: "Software",
    });

    expect(getSpy).toHaveBeenCalledWith("/runs/run-004/jobs?page=1&page_size=50&search=Software&stage=screening&result_bucket=passed");
    expect(res.data.length).toBe(1);
    expect(res.data[0].title).toBe("Software Engineer");
    expect(res.data[0].interest_rating).toBe(5);
    expect(res.data[0].rating_contract_revision).toBe("application-interest-v1");
  });

  it("normalizes nested job pagination and required skills aliases", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: {
        data: [{ required_skills: [{ name: "Python" }, "SQL"] }],
        page: { number: 2, size: 20, total_items: 41, total_pages: 3 },
      },
      status: 200,
    } as any);

    const result = await fetchRunJobs("run-normalized", { page: 2, page_size: 20 });

    expect(result.data[0].skills).toEqual(["Python", "SQL"]);
    expect(result.page).toBe(2);
    expect(result.page_size).toBe(20);
    expect(result.total_items).toBe(41);
    expect(result.total_pages).toBe(3);
    expect(getSpy).toHaveBeenCalledWith("/runs/run-normalized/jobs?page=2&page_size=20");
  });

  it("rejects invalid pagination metadata", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: {
        data: [{ required_skills: "Python; SQL\nAirflow" }],
        page: { number: Number.NaN, size: Number.NaN, total_items: Number.NaN, total_pages: Number.NaN },
      },
      status: 200,
    } as any);

    await expect(fetchRunJobs("run-finite")).rejects.toThrow("Invalid pagination envelope.");
  });

  it("fetches run events with cursor pagination", async () => {
    const mockEventsResponse = {
      data: {
        data: [
          {
            event_id: "ev-1",
            time: "2026-08-30T12:00:01Z",
            stage_id: "screening",
            level: "info",
            operation: "screening",
            state: "recorded",
            message: "Screening completed for 10 jobs",
          },
        ],
        meta: {
          run_id: "run-005",
          cursor: "c-0",
          next_cursor: "c-1",
          total_count: 1,
          integrity_conflicts: 0,
        },
      },
      status: 200,
    };

    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockEventsResponse as any);

    const res = await fetchRunEvents("run-005", "c-0", 100);
    expect(getSpy).toHaveBeenCalledWith("/runs/run-005/events?cursor=c-0&limit=100");
    expect(res.events.length).toBe(1);
    expect(res.next_cursor).toBe("c-1");
  });

  it("triggers a new run with formData and idempotency key", async () => {
    const formData = new FormData();
    formData.append("profile_id", "prof-1");
    formData.append("run_name", "Test Trigger");

    const mockRun = {
      data: {
        run_id: "run-new-1",
        run_name: "Test Trigger",
        backend_status: "queued",
        display_status: "Running",
        created_at: "2026-08-30T12:00:00Z",
        counts: { total: 0, passed: 0, rejected: 0, skipped: 0, cvs_generated: 0 },
        progress: { completed: 0, total: 0 },
        capabilities: { inspect: true, cancel: true, archive: false, unarchive: false, delete: false, export: false },
      },
      status: 201,
    };

    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockRun as any);

    const res = await triggerRun(formData, "fixed-idem-key");
    expect(postSpy).toHaveBeenCalledWith("/runs", formData, { idempotencyKey: "fixed-idem-key" });
    expect(res.run_id).toBe("run-new-1");
  });

  it("triggers cancel, archive, and unarchive actions", async () => {
    const mockRun = {
      data: {
        run_id: "run-act-1",
        run_name: "Action Run",
        backend_status: "cancelling",
        display_status: "Running",
        capabilities: { inspect: true, cancel: false, archive: false, unarchive: false, delete: false, export: true },
      },
      status: 200,
    };

    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValue(mockRun as any);

    await cancelRun("run-act-1");
    expect(postSpy).toHaveBeenCalledWith("/runs/run-act-1/actions/cancel");

    await archiveRun("run-act-1");
    expect(postSpy).toHaveBeenCalledWith("/runs/run-act-1/actions/archive");

    await unarchiveRun("run-act-1");
    expect(postSpy).toHaveBeenCalledWith("/runs/run-act-1/actions/unarchive");
  });

  it("handles preview and delete for archived runs", async () => {
    const mockPreview = {
      data: {
        requested_run_ids: ["run-arch-1"],
        matched_run_ids: ["run-arch-1"],
        blocked_run_ids: [],
        missing_run_ids: [],
        state_tokens: ["token-1"],
        preview_revision: "prev-rev-1",
      },
      status: 200,
    };

    const mockDeleteResult = {
      data: {
        deleted_count: 1,
        run_ids: ["run-arch-1"],
      },
      status: 200,
    };

    const postSpy = vi
      .spyOn(apiClient, "post")
      .mockResolvedValueOnce(mockPreview as any)
      .mockResolvedValueOnce(mockDeleteResult as any);

    const preview = await previewDeleteArchivedRuns(["run-arch-1"]);
    expect(postSpy).toHaveBeenCalledWith("/runs/actions/delete-archived/preview", {
      run_ids: ["run-arch-1"],
    });
    expect(preview.matched_run_ids).toEqual(["run-arch-1"]);

    const deleteRes = await deleteArchivedRuns(["run-arch-1"], preview.preview_revision, "idem-del");
    expect(postSpy).toHaveBeenCalledWith(
      "/runs/actions/delete-archived",
      { run_ids: ["run-arch-1"], preview_revision: "prev-rev-1" },
      { idempotencyKey: "idem-del" }
    );
    expect(deleteRes.deleted_count).toBe(1);
  });

  it("downloads debug bundle and exports CSV", async () => {
    const downloadSpy = vi.spyOn(apiClient, "download").mockResolvedValue(undefined);

    await downloadDebugBundle("run-dbg-1");
    expect(downloadSpy).toHaveBeenCalledWith("/runs/run-dbg-1/debug-bundle", "fitcv-run-run-dbg-1-debug.zip");

    await exportRunJobsCsv("run-dbg-1", {
      stage: "screening",
      result_bucket: "passed",
      search: "Engineer",
    });
    expect(downloadSpy).toHaveBeenCalledWith(
      "/runs/run-dbg-1/jobs/export.csv?search=Engineer&stage=screening&result_bucket=passed",
      "fitcv-run-run-dbg-1-jobs.csv"
    );
  });
it("guards against invalid or object page parameter serialization in fetchRunJobs", async () => {
    const mockResponse = {
      data: {
        data: [],
        page: { number: 1, size: 10, total_items: 0, total_pages: 1 },
      },
      status: 200,
    };
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValue(mockResponse as any);

    // Test with object passed as page (e.g., event object or corrupted state)
    await fetchRunJobs("run-page-test", { page: {} as any });
    expect(getSpy).toHaveBeenCalledWith("/runs/run-page-test/jobs?page=1");
    expect(getSpy.mock.calls[0][0]).not.toContain("[object");

    getSpy.mockClear();

    // Test with valid number
    await fetchRunJobs("run-page-test", { page: 3 });
    expect(getSpy).toHaveBeenCalledWith("/runs/run-page-test/jobs?page=3");
  });

  it("extracts required skills consistently across canonical fields and evidence fallbacks", () => {
    // 1. From canonical required_skills array
    expect(extractRequiredJobSkills({ required_skills: ["TypeScript", "React"] })).toEqual(["TypeScript", "React"]);

    // 2. From top-level skills fallback
    expect(extractRequiredJobSkills({ skills: ["Python", "FastAPI"] })).toEqual(["Python", "FastAPI"]);

    // 3. From evidence.skills (common in bookmarks payload)
    expect(extractRequiredJobSkills({ evidence: { skills: ["Docker", "Kubernetes"] } })).toEqual(["Docker", "Kubernetes"]);

    // 4. From source_snapshot skills
    expect(extractRequiredJobSkills({ source_snapshot: { skills: ["SQL", "Postgres"] } })).toEqual(["SQL", "Postgres"]);

    // 5. From semicolon/newline delimited string
    expect(extractRequiredJobSkills({ required_skills: "AWS; GCP\nTerraform" })).toEqual(["AWS", "GCP", "Terraform"]);

    // 6. Empty when no skills fields exist
    expect(extractRequiredJobSkills({})).toEqual([]);
  });
});
