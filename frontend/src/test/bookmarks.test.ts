import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  fetchBookmarks,
  previewBookmarkExport,
  exportBookmarkSelection,
  removeBookmarkSelection,
  updateBookmarkInterest,
  generateIdempotencyKey,
} from "../features/bookmarks/api";
import { BookmarksPage } from "../features/bookmarks/route";
import { BookmarksTable } from "../features/bookmarks/components/BookmarksTable";
import { BookmarkItem } from "../features/bookmarks/types";
import { apiClient } from "../lib/api-client";
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";

describe("bookmarks slice and api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("registers and matches bookmarks feature route", () => {
    const routes = discoverFeatureRoutes();
    const bmRoute = routes.find((r) => r.id === "bookmarks");
    expect(bmRoute).toBeDefined();
    expect(bmRoute?.path).toBe("#/bookmarks");
    expect(bmRoute?.group).toBe("workspace");

    const matched = matchRoute("#/bookmarks", routes);
    expect(matched.id).toBe("bookmarks");
  });

  it("generates bookmark idempotency keys", () => {
    const key1 = generateIdempotencyKey();
    const key2 = generateIdempotencyKey();
    expect(key1).toBeTruthy();
    expect(key2).toBeTruthy();
    expect(key1).not.toBe(key2);
  });

  it("fetches bookmarks collection with filters and default sort", async () => {
    const mockRes = {
      data: {
        data: [
          {
            bookmark_id: "bm-01",
            bookmarked_at: "2026-08-30T10:00:00Z",
            run_id: "run-01",
            run_name: "Run Alpha",
            run_job_id: "rj-01",
            title: "Senior Platform Engineer",
            company: "Tech Corp",
            rating: 5,
            cv_available: 1,
            result_bucket: "passed",
          },
        ],
        page: 1,
        page_size: 20,
        total_items: 1,
      },
      status: 200,
    };

    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockRes as any);

    const result = await fetchBookmarks({
      stage: "screening",
      result: "passed",
      search: "Platform",
    });

    expect(getSpy).toHaveBeenCalledWith(
      "/bookmarks?stage=screening&result=passed&search=Platform&sort=bookmarked_desc"
    );
    expect(result.data.length).toBe(1);
    expect(result.data[0].title).toBe("Senior Platform Engineer");
  });

  it("updates and clears bookmark interest via rating endpoint", async () => {
    const putSpy = vi.spyOn(apiClient, "put").mockResolvedValueOnce({
      data: { run_job_id: "rj-01", rating: 4, rating_contract_revision: "application-interest-v1" },
      status: 200,
    } as any);

    const setRes = await updateBookmarkInterest("run-01", "rj-01", 4);
    expect(putSpy).toHaveBeenCalledWith("/runs/run-01/jobs/rj-01/interest", {
      rating: 4,
      rating_contract_revision: "application-interest-v1",
    });
    expect(setRes.rating).toBe(4);

    const deleteSpy = vi.spyOn(apiClient, "delete").mockResolvedValueOnce({
      data: { run_job_id: "rj-01", rating: null },
      status: 200,
    } as any);

    const clearRes = await updateBookmarkInterest("run-01", "rj-01", null);
    expect(deleteSpy).toHaveBeenCalledWith("/runs/run-01/jobs/rj-01/interest");
    expect(clearRes.rating).toBeNull();
  });

  it("handles export preview and removal of bookmarks", async () => {
    const mockPreview = {
      data: {
        data: {
          selected_count: 1,
          matched_count: 1,
          excluded_count: 0,
          matched_run_job_ids: ["rj-01"],
          excluded_run_job_ids: [],
          preview_revision: "bm-prev-rev-1",
          expires_in_seconds: 300,
          expires_at: "2026-08-30T12:00:00Z",
        },
      },
      status: 200,
    };

    const mockExport = {
      data: "run_id,run_job_id\nrun-01,rj-01\n",
      status: 200,
    };

    const mockRemove = {
      data: {
        data: {
          removed_count: 1,
        },
      },
      status: 200,
    };

    const postSpy = vi
      .spyOn(apiClient, "post")
      .mockResolvedValueOnce(mockPreview as any)
      .mockResolvedValueOnce(mockExport as any)
      .mockResolvedValueOnce(mockRemove as any);

    const preview = await previewBookmarkExport({
      selected_run_job_ids: ["rj-01"],
    });

    expect(postSpy).toHaveBeenCalledWith("/bookmarks/actions/export/preview", {
      selected_run_job_ids: ["rj-01"],
    });
    expect(preview.matched_count).toBe(1);

    await exportBookmarkSelection(
      { selected_run_job_ids: ["rj-01"], preview_revision: "bm-prev-rev-1" },
      "fixed-export-idem"
    );
    expect(postSpy).toHaveBeenCalledWith(
      "/bookmarks/actions/export",
      { selected_run_job_ids: ["rj-01"], preview_revision: "bm-prev-rev-1" },
      { idempotencyKey: "fixed-export-idem", headers: { Accept: "text/csv" } }
    );

    const removeRes = await removeBookmarkSelection(
      { selected_run_job_ids: ["rj-01"] },
      "fixed-idem-bm"
    );
    expect(postSpy).toHaveBeenCalledWith(
      "/bookmarks/actions/remove",
      { selected_run_job_ids: ["rj-01"] },
      { idempotencyKey: "fixed-idem-bm" }
    );
    expect(removeRes.removed_count).toBe(1);
  });

  it("renders prototype-aligned BookmarksTable structure and interactive controls", () => {
    const mockItem: BookmarkItem = {
      bookmark_id: "bm-01",
      bookmarked_at: "2026-08-30T10:00:00Z",
      run_id: "RUN-7E4A92C1",
      run_name: "Data Platform Lead",
      run_job_id: "JOB-001",
      title: "Senior Data Product Manager",
      company: "Acme",
      location: "Berlin, Germany",
      work_mode: "Hybrid",
      language: "English",
      seniority: "Senior",
      role_family: "Product Management",
      domain: "Data Platforms",
      skills: ["Product Strategy", "SQL", "Data Modeling", "Roadmapping", "Stakeholder Management", "Experimentation"],
      rating: 4,
      status: "passed",
      result_bucket: "passed",
      outcome_code: "Passed Shortlisting",
      reason_code: "Met Shortlisting requirements.",
    };

    const markup = renderToStaticMarkup(
      React.createElement(BookmarksTable, {
        bookmarks: [mockItem],
        loading: false,
        page: 1,
        pageSize: 20,
        total: 1,
        onPageChange: () => {},
        selectedJobIds: [],
        onToggleSelectJob: () => {},
        onToggleSelectAll: () => {},
        onRemoveSingle: () => {},
        onInspectEvidence: () => {},
        onChangeInterest: () => {},
        onSelectRun: () => {},
      })
    );

    expect(markup).toContain("RUN-7E4A92C1");
    expect(markup).toContain("Senior Data Product Manager");
    expect(markup).toContain("Job Attributes");
    expect(markup).toContain("Required Skills");
    expect(markup).toContain("Pipeline Outcome");
    expect(markup).toContain("Evidence");
    expect(markup).toContain("Remove");
    expect(markup).toContain("Application Interest for Senior Data Product Manager");
    expect(markup).toContain("+1 more");
  });

  it("renders BookmarksPage structure with prototype headings and pipeline stage tabs", () => {
    vi.spyOn(apiClient, "get").mockResolvedValue({
      data: { data: [], page: 1, page_size: 20, total_items: 0 },
      status: 200,
    } as any);

    const markup = renderToStaticMarkup(React.createElement(BookmarksPage));

    expect(markup).toContain("Workspace");
    expect(markup).toContain("Bookmarks");
    expect(markup).toContain("Review bookmarked jobs across runs using the same pipeline evidence as Run Details.");
    expect(markup).toContain("pipeline-stage-tabs");
    expect(markup).toContain("All Jobs");
    expect(markup).toContain("Enrichment");
    expect(markup).toContain("Screening");
    expect(markup).toContain("Shortlisting");
    expect(markup).toContain("Ranking");
    expect(markup).toContain("CV Analysis");
    expect(markup).toContain("CV Generation");
    expect(markup).toContain("Search bookmarked jobs, runs, attributes, skills, or outcomes");
  });
});
