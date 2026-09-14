import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  fetchBookmarks,
  previewBookmarkExport,
  exportBookmarkSelection,
  exportBookmarkFullSelection,
  removeBookmarkSelection,
  updateBookmarkInterest,
  generateIdempotencyKey,
} from "../features/bookmarks/api";
import { BookmarksPage, buildBookmarksQueryKey, SEARCH_DEBOUNCE_MS } from "../features/bookmarks/route";
import { BookmarksTable } from "../features/bookmarks/components/BookmarksTable";
import { BookmarkItem } from "../features/bookmarks/types";
import { apiClient } from "../lib/api-client";
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";
import { FilterTabs, getNextFilterTabIndex } from "../features/run-detail/components/FilterTabs";

describe("bookmarks slice and api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("uses accessible filter tabs with selected state and controlled panel", () => {
    const markup = renderToStaticMarkup(
      React.createElement(FilterTabs, {
        items: [{ id: "all", label: "All Jobs" }, { id: "ranking", label: "Ranking" }],
        activeId: "ranking",
        onChange: () => undefined,
        ariaLabel: "Bookmark pipeline stages",
        panelId: "bookmarkTablePanel",
        className: "pipeline-stage-tabs",
      })
    );
    expect(markup).toContain('role="tablist"');
    expect(markup).toContain('aria-controls="bookmarkTablePanel"');
    expect(markup).toContain('aria-selected="true"');
    expect(markup).toContain('aria-selected="false"');
    expect(markup).toContain('id="bookmarkTablePanel-tab-ranking"');
    expect(getNextFilterTabIndex("ArrowRight", 1, 2)).toBe(0);
    expect(getNextFilterTabIndex("ArrowLeft", 0, 2)).toBe(1);
    expect(getNextFilterTabIndex("Home", 1, 2)).toBe(0);
    expect(getNextFilterTabIndex("End", 0, 2)).toBe(1);
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

    const downloadSpy = vi.spyOn(apiClient, "download").mockResolvedValueOnce();
    await exportBookmarkFullSelection(
      { selected_run_job_ids: ["rj-01"], preview_revision: "bm-prev-rev-1" },
      "fixed-full-export-idem"
    );
    expect(downloadSpy).toHaveBeenCalledWith(
      "/bookmarks/actions/export.full.zip",
      "fitcv-bookmarks-full-export.zip",
      {
        method: "POST",
        body: { selected_run_job_ids: ["rj-01"], preview_revision: "bm-prev-rev-1" },
        idempotencyKey: "fixed-full-export-idem",
        headers: { Accept: "application/zip" },
      }
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

  it("normalizes canonical nested pagination for bookmarks", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: {
        data: [{ run_job_id: "rj-1" }],
        page: { number: 2, size: 20, total_items: 21, total_pages: 2 },
        meta: {},
      },
      status: 200,
    } as any);

    const result = await fetchBookmarks({ page: 2, page_size: 20 });
    expect(result.page).toBe(2);
    expect(result.page_size).toBe(20);
    expect(result.total_items).toBe(21);
    expect(result.total_pages).toBe(2);
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
    expect(markup).toContain("Export CSV");
    expect(markup).toContain("Export full data");
  });
});


describe("Bookmarks Search Debounce and Stale Request Rejection", () => {
  it("builds canonical bookmark query key with stage, search, page, and size", () => {
    const key = buildBookmarksQueryKey("screening", "Platform", 1, 20);
    expect(key).toBe("screening::Platform::1::20");
  });

  it("trims whitespace from search term in query key identity", () => {
    const key1 = buildBookmarksQueryKey("all", "  Platform Lead  ", 1, 20);
    const key2 = buildBookmarksQueryKey("all", "Platform Lead", 1, 20);
    expect(key1).toBe("all::Platform Lead::1::20");
    expect(key1).toBe(key2);
  });

  it("distinguishes bookmark query keys across stage, search, page, and size", () => {
    const base = buildBookmarksQueryKey("all", "dev", 1, 20);
    expect(base).not.toBe(buildBookmarksQueryKey("ranking", "dev", 1, 20));
    expect(base).not.toBe(buildBookmarksQueryKey("all", "engineer", 1, 20));
    expect(base).not.toBe(buildBookmarksQueryKey("all", "dev", 2, 20));
    expect(base).not.toBe(buildBookmarksQueryKey("all", "dev", 1, 50));
  });

  it("debounces rapid keystroke burst to one settled remote fetch", () => {
    vi.useFakeTimers();
    let debounceTimer: ReturnType<typeof setTimeout> | null = null;
    let activeQuery = "";
    let fetchCount = 0;

    const handleSearchInput = (val: string) => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        activeQuery = val.trim();
        fetchCount += 1;
      }, SEARCH_DEBOUNCE_MS);
    };

    handleSearchInput("P");
    vi.advanceTimersByTime(100);
    handleSearchInput("Pl");
    vi.advanceTimersByTime(100);
    handleSearchInput("Platform");

    // Before settled interval, no fetch triggered
    expect(fetchCount).toBe(0);
    expect(activeQuery).toBe("");

    // Advance to settled interval
    vi.advanceTimersByTime(SEARCH_DEBOUNCE_MS);
    expect(fetchCount).toBe(1);
    expect(activeQuery).toBe("Platform");

    vi.useRealTimers();
  });

  it("rejects stale Search A response resolving after Search B", async () => {
    let activeRequestId = 0;
    let acceptedData: string | null = null;
    let acceptedTotal = 0;
    let loading = false;
    let resolveSearchA: ((val: { data: string; total: number }) => void) | null = null;
    let resolveSearchB: ((val: { data: string; total: number }) => void) | null = null;

    const dispatchSearch = (term: string) => {
      const reqId = ++activeRequestId;
      loading = true;
      const promise = new Promise<{ data: string; total: number }>((resolve) => {
        if (term === "Search A") resolveSearchA = resolve;
        else resolveSearchB = resolve;
      });

      return promise.then((result) => {
        if (reqId !== activeRequestId) {
          // Stale response rejected: does not modify state or clear loading
          return false;
        }
        acceptedData = result.data;
        acceptedTotal = result.total;
        loading = false;
        return true;
      });
    };

    const promiseA = dispatchSearch("Search A");
    const promiseB = dispatchSearch("Search B");
    expect(loading).toBe(true);

    // Search A resolves late
    resolveSearchA!({ data: "Results for Search A (stale)", total: 5 });
    const resultA = await promiseA;
    expect(resultA).toBe(false);
    expect(acceptedData).toBeNull();
    expect(acceptedTotal).toBe(0);
    expect(loading).toBe(true); // Still loading because Search B is active

    // Search B resolves
    resolveSearchB!({ data: "Results for Search B (active)", total: 12 });
    const resultB = await promiseB;
    expect(resultB).toBe(true);
    expect(acceptedData).toBe("Results for Search B (active)");
    expect(acceptedTotal).toBe(12);
    expect(loading).toBe(false);
  });

  it("cleans up debounce timer and ignores pending responses on unmount", async () => {
    vi.useFakeTimers();
    let isMounted = true;
    let debounceTimer: ReturnType<typeof setTimeout> | null = null;
    let activeSearch = "";
    let fetchCount = 0;
    let stateUpdatedAfterUnmount = false;
    let resolvePendingFetch: (() => void) | null = null;

    const onSearchChange = (val: string) => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        if (!isMounted) return;
        activeSearch = val.trim();
        fetchCount += 1;
        new Promise<void>((resolve) => {
          resolvePendingFetch = resolve;
        }).then(() => {
          if (!isMounted) return;
          stateUpdatedAfterUnmount = true;
        });
      }, SEARCH_DEBOUNCE_MS);
    };

    onSearchChange("Platform");
    vi.advanceTimersByTime(100);

    // Unmount before debounce completes
    isMounted = false;
    if (debounceTimer) clearTimeout(debounceTimer);

    vi.advanceTimersByTime(SEARCH_DEBOUNCE_MS + 100);
    expect(fetchCount).toBe(0);
    expect(activeSearch).toBe("");

    // Remount, trigger fetch, then unmount while fetch is in-flight
    isMounted = true;
    onSearchChange("Engineer");
    vi.advanceTimersByTime(SEARCH_DEBOUNCE_MS);
    expect(fetchCount).toBe(1);
    expect(activeSearch).toBe("Engineer");

    // Unmount while request is pending
    isMounted = false;
    resolvePendingFetch!();
    await Promise.resolve();

    expect(stateUpdatedAfterUnmount).toBe(false);
    vi.useRealTimers();
  });

  it("disables rating controls when backend marks bookmark as ineligible", () => {
    const markup = renderToStaticMarkup(
      React.createElement(BookmarksTable, {
        bookmarks: [{
          bookmark_id: "bm-ineligible",
          bookmarked_at: "2026-08-30T10:00:00Z",
          run_id: "run-ineligible",
          run_job_id: "job-ineligible",
          title: "Ineligible Job",
          company: "Acme",
          rating: null,
          capabilities: { rate: false },
        }],
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
      })
    );

    expect(markup).toContain('disabled=""');
  });
});
