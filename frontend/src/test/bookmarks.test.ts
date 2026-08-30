import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchBookmarks,
  previewBookmarkExport,
  removeBookmarkSelection,
  generateIdempotencyKey,
} from "../features/bookmarks/api";
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
      .mockResolvedValueOnce(mockRemove as any);

    const preview = await previewBookmarkExport({
      selected_run_job_ids: ["rj-01"],
    });

    expect(postSpy).toHaveBeenCalledWith("/bookmarks/actions/export/preview", {
      selected_run_job_ids: ["rj-01"],
    });
    expect(preview.matched_count).toBe(1);

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
});
