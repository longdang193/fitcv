import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  setJobBookmark,
  clearJobBookmark,
  setJobInterest,
  clearJobInterest,
  previewRunJobExport,
  exportRunJobSelection,
} from "../features/job-evaluation/api";
import { apiClient } from "../lib/api-client";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { FitEvidenceDrawer } from "../features/job-evaluation/components/FitEvidenceDrawer";
import { RunJobItem } from "../features/runs/types";


describe("job evaluation slice and api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });



  it("sets and clears job bookmark via PUT/DELETE endpoints", async () => {
    const putSpy = vi.spyOn(apiClient, "put").mockResolvedValueOnce({
      data: {
        data: { run_job_id: "job-1", bookmarked: true, bookmark_id: "bm-1" },
      },
      status: 200,
    } as any);

    const deleteSpy = vi.spyOn(apiClient, "delete").mockResolvedValueOnce({
      data: {
        data: { run_job_id: "job-1", bookmarked: false, bookmark_id: null },
      },
      status: 200,
    } as any);

    const setRes = await setJobBookmark("run-1", "job-1");
    expect(putSpy).toHaveBeenCalledWith("/runs/run-1/jobs/job-1/bookmark");
    expect(setRes.bookmarked).toBe(true);

    const clearRes = await clearJobBookmark("run-1", "job-1");
    expect(deleteSpy).toHaveBeenCalledWith("/runs/run-1/jobs/job-1/bookmark");
    expect(clearRes.bookmarked).toBe(false);
  });

  it("sets and clears job interest with application-interest-v1 revision", async () => {
    const putSpy = vi.spyOn(apiClient, "put").mockResolvedValueOnce({
      data: {
        data: { run_job_id: "job-2", rating: 5, rating_contract_revision: "application-interest-v1" },
      },
      status: 200,
    } as any);

    const deleteSpy = vi.spyOn(apiClient, "delete").mockResolvedValueOnce({
      data: {
        data: { run_job_id: "job-2", rating: null },
      },
      status: 200,
    } as any);

    const interestRes = await setJobInterest("run-1", "job-2", 5);
    expect(putSpy).toHaveBeenCalledWith("/runs/run-1/jobs/job-2/interest", {
      rating: 5,
      rating_contract_revision: "application-interest-v1",
    });
    expect(interestRes.rating).toBe(5);

    const clearRes = await clearJobInterest("run-1", "job-2");
    expect(deleteSpy).toHaveBeenCalledWith("/runs/run-1/jobs/job-2/interest");
    expect(clearRes.rating).toBeNull();
  });

  it("handles preview and export of filtered run jobs", async () => {
    const mockPreview = {
      data: {
        data: {
          selected_count: 2,
          matched_count: 2,
          excluded_count: 0,
          matched_run_job_ids: ["job-1", "job-2"],
          excluded_run_job_ids: [],
          preview_revision: "prev-rev-123",
          expires_in_seconds: 300,
          expires_at: "2026-08-30T12:00:00Z",
        },
      },
      status: 200,
    };

    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockPreview as any);

    const preview = await previewRunJobExport("run-1", {
      selected_run_job_ids: ["job-1", "job-2"],
      stage: "screening",
      result: "passed",
    });

    expect(postSpy).toHaveBeenCalledWith("/runs/run-1/jobs/actions/export/preview", {
      selected_run_job_ids: ["job-1", "job-2"],
      stage: "screening",
      result: "passed",
    });
    expect(preview.matched_count).toBe(2);
    expect(preview.preview_revision).toBe("prev-rev-123");

    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      blob: async () => new Blob(["col1,col2\nval1,val2"], { type: "text/csv" }),
    });

    // Mock URL and DOM APIs
    if (typeof window !== "undefined") {
      window.URL.createObjectURL = vi.fn().mockReturnValue("blob:mock-url");
      window.URL.revokeObjectURL = vi.fn();
    }

    await exportRunJobSelection("run-1", {
      selected_run_job_ids: ["job-1"],
      preview_revision: "prev-rev-123",
    });

    expect(globalThis.fetch).toHaveBeenCalled();
  });
  it("renders FitEvidenceDrawer with user-facing factor labels and status wording", () => {
    const mockJob: RunJobItem = {
      run_job_id: "job-1",
      title: "Senior Backend Engineer",
      company: "Acme Corp",
      status: "rejected",
      result_bucket: "rejected",
      reason_code: "reranker_fit_below_threshold",
      attributes: {
        fit_factor_results: {
          evidence_ref: { artifact: "results.json" },
          pipeline_status: "ranked_no_cv",
          skip_is_terminal_rejection: false,
          reranker_fit: { passed: false, reason: "reranker_fit_below_threshold" },
        },
      },
    };

    const markup = renderToStaticMarkup(
      React.createElement(FitEvidenceDrawer, {
        job: mockJob,
        open: true,
        onClose: () => {},
      })
    );

    // Verify user-facing wording is present
    expect(markup).toContain("Evidence Reference");
    expect(markup).toContain("results.json");
    expect(markup).toContain("Pipeline Status");
    expect(markup).toContain("Ranked without CV");
    expect(markup).toContain("Skip Terminal Rejection");
    expect(markup).toContain("No");
    expect(markup).toContain("Reranker Fit");
    expect(markup).toContain("Reranker fit below threshold");

    // Verify technical underscore identifiers are NOT rendered directly as factor labels
    expect(markup).not.toContain("<span>evidence_ref</span>");
    expect(markup).not.toContain("<span>pipeline_status</span>");
    expect(markup).not.toContain("<span>skip_is_terminal_rejection</span>");
    expect(markup).not.toContain("<span>reranker_fit</span>");
  });
});
