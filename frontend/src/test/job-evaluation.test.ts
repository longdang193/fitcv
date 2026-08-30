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
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";

describe("job evaluation slice and api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("registers and matches job-evaluation feature route", () => {
    const routes = discoverFeatureRoutes();
    const evalRoute = routes.find((r) => r.id === "job-evaluation");
    expect(evalRoute).toBeDefined();
    expect(evalRoute?.path).toBe("#/job-evaluation");
    expect(evalRoute?.group).toBe("workspace");

    const matched = matchRoute("#/job-evaluation?run_id=run-1", routes);
    expect(matched.id).toBe("job-evaluation");
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
  });
});
