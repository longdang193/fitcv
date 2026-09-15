import { DateRange, DateRangeFilter, parseDateRange, getClientTimezone } from "../../components/DateRangeFilter";
import React, { useState, useEffect, useCallback, useRef } from "react";

export const SEARCH_DEBOUNCE_MS = 250;

export interface BookmarksRouteState {
  dateRange: DateRange;
  page: number;
  stage: string;
  search: string;
}

export function parseBookmarksRoute(hash: string): BookmarksRouteState {
  const queryIndex = hash.indexOf("?");
  const params = queryIndex >= 0 ? new URLSearchParams(hash.slice(queryIndex + 1)) : new URLSearchParams();
  const dateRange = parseDateRange(params.get("date_range"));
  const p = Number(params.get("page"));
  const page = Number.isInteger(p) && p > 0 ? p : 1;
  const stage = params.get("stage") || "all";
  const search = params.get("search") || "";
  return { dateRange, page, stage, search };
}

export function buildBookmarksQueryKey(
  stage: string = "all",
  search: string = "",
  page: number = 1,
  pageSize: number = 20,
  dateRange: DateRange = "today"
): string {
  return `${stage}::${search.trim()}::${page}::${pageSize}::${dateRange}`;
}
import { BookmarksTable } from "./components/BookmarksTable";
import { FitEvidenceDrawer } from "../job-evaluation/components/FitEvidenceDrawer";
import {
  fetchBookmarks,
  removeBookmarkSelection,
  previewBookmarkExport,
  exportBookmarkSelection,
  exportBookmarkFullSelection,
  updateBookmarkInterest,
} from "./api";
import { BookmarkItem } from "./types";
import { RunJobItem } from "../runs/types";
import { Button, Dialog } from "../../components";
import { notificationStore } from "../../lib/notifications";
import { FilterTabs } from "../run-detail/components/FilterTabs";

const PIPELINE_STAGES: { id: string; label: string }[] = [
  { id: "all", label: "All Jobs" },
  { id: "enrichment", label: "Enrichment" },
  { id: "screening", label: "Screening" },
  { id: "shortlisting", label: "Shortlisting" },
  { id: "ranking", label: "Ranking" },
  { id: "cv-analysis", label: "CV Analysis" },
  { id: "cv-generation", label: "CV Generation" },
];

export const BookmarksPage: React.FC = () => {
  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);

  const [dateRange, setDateRange] = useState<DateRange>("today");
  const [stageFilter, setStageFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [activeSearch, setActiveSearch] = useState("");

  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([]);
  const [inspectingJob, setInspectingJob] = useState<RunJobItem | null>(null);

  const [confirmRemove, setConfirmRemove] = useState<{
    singleJobId?: string;
    singleTitle?: string;
    isBatch?: boolean;
  } | null>(null);
  const [actionInProgress, setActionInProgress] = useState(false);

  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestIdRef = useRef<number>(0);
  const isMountedRef = useRef<boolean>(true);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const updateUrl = useCallback((
    newDateRange: DateRange,
    newPage: number,
    newStage: string,
    newSearch: string
  ) => {
    const params = new URLSearchParams();
    if (newDateRange !== "today") params.set("date_range", newDateRange);
    if (newPage > 1) params.set("page", String(newPage));
    if (newStage && newStage !== "all") params.set("stage", newStage);
    if (newSearch) params.set("search", newSearch);

    const qs = params.toString();
    const newHash = qs ? `#/bookmarks?${qs}` : `#/bookmarks`;
    if (window.location.hash !== newHash) {
      window.location.hash = newHash;
    }
  }, []);

  useEffect(() => {
    const readHash = () => {
      const state = parseBookmarksRoute(window.location.hash || "#/bookmarks");
      setDateRange(state.dateRange);
      setPage(state.page);
      setStageFilter(state.stage);
      setSearch(state.search);
      setActiveSearch(state.search);
    };

    readHash();
    window.addEventListener("hashchange", readHash);
    return () => window.removeEventListener("hashchange", readHash);
  }, []);

  const handleDateRangeChange = (newRange: DateRange) => {
    setDateRange(newRange);
    setPage(1);
    setSelectedJobIds([]);
    updateUrl(newRange, 1, stageFilter, activeSearch);
  };

  const handleStageChange = (stageId: string) => {
    setStageFilter(stageId);
    setPage(1);
    setSelectedJobIds([]);
    updateUrl(dateRange, 1, stageId, activeSearch);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    updateUrl(dateRange, newPage, stageFilter, activeSearch);
  };

  // Debounce search input and reset page to 1
  useEffect(() => {
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }
    searchDebounceRef.current = setTimeout(() => {
      const trimmed = search.trim();
      setActiveSearch(trimmed);
      setPage(1);
      updateUrl(dateRange, 1, stageFilter, trimmed);
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current);
      }
    };
  }, [search, dateRange, stageFilter, updateUrl]);

  // ponytail: guarded bookmark list loader rejecting stale responses by request identity; add LRU cache if stage hopping is frequent.
  const loadBookmarkList = useCallback(
    async (targetPage = 1) => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
      abortControllerRef.current = controller;

      const requestId = ++requestIdRef.current;
      const queryKey = buildBookmarksQueryKey(stageFilter, activeSearch, targetPage, pageSize, dateRange);
      const ownsRequest = () => (
        isMountedRef.current &&
        requestId === requestIdRef.current &&
        queryKey === buildBookmarksQueryKey(stageFilter, activeSearch, targetPage, pageSize, dateRange)
      );
      if (ownsRequest()) {
        setLoading(true);
        setLoadError(null);
      }
      try {
        const res = await fetchBookmarks({
          page: targetPage,
          page_size: pageSize,
          stage: stageFilter !== "all" ? stageFilter : undefined,
          search: activeSearch,
          date_range: dateRange,
          timezone: getClientTimezone(),
          signal: controller?.signal,
        });
        if (!ownsRequest()) {
          return false;
        }
        setBookmarks(res.data || []);
        setPage(res.page || targetPage);
        setTotal(res.total_items || 0);
        return true;
      } catch (err: any) {
        if (!ownsRequest() || err?.name === "AbortError") {
          return false;
        }
        setLoadError(err.message || "Failed to load bookmarks.");
        notificationStore.notify({
          dedupe: `req:load_bookmarks:${Date.now()}`,
          type: "error",
          title: "Failed to load bookmarks",
          message: err.message,
        });
        return false;
      } finally {
        if (ownsRequest()) {
          setLoading(false);
        }
      }
    },
    [pageSize, stageFilter, activeSearch, dateRange]
  );

  useEffect(() => {
    loadBookmarkList(1);
  }, [loadBookmarkList]);

  const handleToggleSelectJob = (runJobId: string) => {
    setSelectedJobIds((prev) =>
      prev.includes(runJobId) ? prev.filter((id) => id !== runJobId) : [...prev, runJobId]
    );
  };

  const handleToggleSelectAll = () => {
    if (bookmarks.every((b) => selectedJobIds.includes(b.run_job_id))) {
      const visibleIds = new Set(bookmarks.map((b) => b.run_job_id));
      setSelectedJobIds((prev) => prev.filter((id) => !visibleIds.has(id)));
    } else {
      const combined = new Set([...selectedJobIds, ...bookmarks.map((b) => b.run_job_id)]);
      setSelectedJobIds(Array.from(combined));
    }
  };

  const handleInspect = (bm: BookmarkItem) => {
    const projectedJob: RunJobItem = {
      run_job_id: bm.run_job_id,
      job_id: bm.run_job_id,
      title: bm.title,
      company: bm.company,
      location: bm.location,
      current_stage_id: bm.stage_id || "screening",
      status: bm.status as any || "passed",
      result_bucket: (bm.result_bucket as any) || null,
      bookmarked: true,
      interest_rating: bm.rating,
      attributes: {
        reasons: bm.reason_code ? [bm.reason_code] : [],
        fit_factor_results: bm.evidence || {},
      },
    };
    setInspectingJob(projectedJob);
  };

  const handleChangeInterest = async (bookmark: BookmarkItem, newRating: number | null) => {
    const oldRating = bookmark.rating;
    setBookmarks((prev) =>
      prev.map((b) =>
        b.run_job_id === bookmark.run_job_id ? { ...b, rating: newRating } : b
      )
    );

    try {
      await updateBookmarkInterest(bookmark.run_id, bookmark.run_job_id, newRating);
    } catch (err: any) {
      setBookmarks((prev) =>
        prev.map((b) =>
          b.run_job_id === bookmark.run_job_id ? { ...b, rating: oldRating } : b
        )
      );
      notificationStore.notify({
        dedupe: `interest:err:${bookmark.run_job_id}`,
        type: "error",
        title: "Interest update failed",
        message: err.message || "Could not update interest rating.",
      });
    }
  };

  const handleConfirmRemove = async () => {
    if (!confirmRemove) return;
    setActionInProgress(true);
    const idsToRemove = confirmRemove.singleJobId
      ? [confirmRemove.singleJobId]
      : selectedJobIds;

    try {
      const res = await removeBookmarkSelection({
        selected_run_job_ids: idsToRemove,
        stage: stageFilter !== "all" ? stageFilter : undefined,
        search: activeSearch || undefined,
      });

      notificationStore.notify({
        dedupe: `action:remove_bookmarks:${Date.now()}`,
        type: "info",
        title: "Bookmarks removed",
        message: `Removed ${res.removed_count} bookmark(s).`,
      });

      setSelectedJobIds((prev) => prev.filter((id) => !idsToRemove.includes(id)));
      setConfirmRemove(null);
      await loadBookmarkList(page);
    } catch (err: any) {
      notificationStore.notify({
        dedupe: `error:remove_bookmarks:${Date.now()}`,
        type: "error",
        title: "Removal failed",
        message: err.message || "Failed to remove bookmark selection.",
      });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleExport = async (full = false) => {
    setActionInProgress(true);
    try {
      const preview = await previewBookmarkExport({
        selected_run_job_ids: selectedJobIds,
        stage: stageFilter !== "all" ? stageFilter : undefined,
        search: activeSearch || undefined,
      });

      const exportPayload = {
        selected_run_job_ids: selectedJobIds,
        stage: stageFilter !== "all" ? stageFilter : undefined,
        search: activeSearch || undefined,
        preview_revision: preview.preview_revision,
      };
      if (full) {
        await exportBookmarkFullSelection(exportPayload);
      } else {
        await exportBookmarkSelection(exportPayload);
      }

      notificationStore.notify({
        dedupe: `action:export_bookmarks:${Date.now()}`,
        type: "info",
        title: "Bookmark export started",
        message: `Exporting ${preview.matched_count} bookmarks to ${full ? "full data ZIP" : "CSV"}.`,
      });
    } catch (err: any) {
      notificationStore.notify({
        dedupe: `error:export_bookmarks:${Date.now()}`,
        type: "error",
        title: "Export failed",
        message: err.message || "Failed to export bookmarks.",
      });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleSelectRun = (runId: string) => {
    window.location.hash = `#/runs?run_id=${encodeURIComponent(runId)}`;
  };

  return (
    <div className="content-container">
      {/* Page Head */}
      <div className="page-head" style={{ marginBottom: 20 }}>
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>Bookmarks</h2>
          <p>Review bookmarked jobs across runs using the same pipeline evidence as Run Details.</p>
        </div>
      </div>

      <div className="run-panel">
        {/* Pipeline Stage Tabs */}
        <FilterTabs
          className="pipeline-stage-tabs"
          items={PIPELINE_STAGES.map((stage) => ({ ...stage, dataAttribute: "data-bookmark-stage" }))}
          activeId={stageFilter}
          ariaLabel="Bookmark pipeline stages"
          panelId="bookmarkTablePanel"
          onChange={handleStageChange}
        />

        {/* Results Toolbar */}
        <div className="results-toolbar">
          <DateRangeFilter
            value={dateRange}
            onChange={handleDateRangeChange}
          />
          <input
            className="field page-search-input results-search"
            id="bookmarkSearch"
            type="search"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
            }}
            placeholder="Search bookmarked jobs, runs, attributes, skills, or outcomes"
            aria-label="Search bookmarked jobs"
          />
          <div className="results-toolbar-actions">
            <Button
              id="exportBookmarks"
              type="button"
              variant="secondary"
              disabled={selectedJobIds.length === 0 || actionInProgress}
              onClick={() => handleExport(false)}
            >
              Export CSV
            </Button>
            <Button
              id="exportBookmarksFull"
              type="button"
              variant="secondary"
              disabled={selectedJobIds.length === 0 || actionInProgress}
              onClick={() => handleExport(true)}
            >
              Export full data
            </Button>
          </div>
        </div>

        {/* Run Selection Bar */}
        {selectedJobIds.length > 0 && (
          <div className="run-selection">
            <div className="run-selection-copy">
              <strong>
                {selectedJobIds.length} bookmarked job{selectedJobIds.length === 1 ? "" : "s"} selected
              </strong>
              <span>Export and Remove Bookmarks apply only to selected jobs in the current stage and search.</span>
            </div>
            <div className="run-selection-actions">
              <Button
                id="removeSelectedBookmarks"
                type="button"
                variant="danger"
                size="compact"
                disabled={actionInProgress}
                onClick={() => setConfirmRemove({ isBatch: true })}
              >
                Remove Bookmarks
              </Button>
            </div>
          </div>
        )}

        {/* Bookmarks Table Panel */}
        <div id="bookmarkTablePanel" role="tabpanel" aria-label="Bookmarked jobs">
          {loadError && (
            <div className="notice error" role="alert" style={{ marginBottom: 16 }}>
              Failed to load bookmarks: {loadError}{" "}
              <Button variant="secondary" size="compact" onClick={() => loadBookmarkList(page)}>
                Retry
              </Button>
            </div>
          )}
          <BookmarksTable
            bookmarks={bookmarks}
            loading={loading}
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={(p) => {
              handlePageChange(p);
              loadBookmarkList(p);
            }}
            selectedJobIds={selectedJobIds}
            onToggleSelectJob={handleToggleSelectJob}
            onToggleSelectAll={handleToggleSelectAll}
            onRemoveSingle={(bm) =>
              setConfirmRemove({
                singleJobId: bm.run_job_id,
                singleTitle: bm.title,
              })
            }
            onInspectEvidence={handleInspect}
            onChangeInterest={handleChangeInterest}
            onSelectRun={handleSelectRun}
            hasFilters={stageFilter !== "all" || Boolean(activeSearch) || dateRange !== "all"}
            dateRange={dateRange}
            onDateRangeChange={handleDateRangeChange}
          />
        </div>
      </div>

      {/* Removal Confirmation Dialog */}
      <Dialog
        open={confirmRemove !== null}
        onClose={() => setConfirmRemove(null)}
        title="Remove Bookmark?"
        description={
          confirmRemove?.singleTitle
            ? `Are you sure you want to remove "${confirmRemove.singleTitle}" from your bookmarks?`
            : `Are you sure you want to remove ${selectedJobIds.length} selected bookmarks?`
        }
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button
              variant="secondary"
              onClick={() => setConfirmRemove(null)}
              disabled={actionInProgress}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleConfirmRemove}
              disabled={actionInProgress}
            >
              {actionInProgress ? "Removing..." : "Remove"}
            </Button>
          </div>
        }
      >
        <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
          Note: Removing a bookmark preserves the underlying job and run history. If an archived run is deleted later, associated bookmarks are automatically cleaned.
        </p>
      </Dialog>

      {/* Evidence Drawer */}
      <FitEvidenceDrawer
        job={inspectingJob}
        open={inspectingJob !== null}
        onClose={() => setInspectingJob(null)}
      />
    </div>
  );
};

export const route = {
  id: "bookmarks",
  path: "#/bookmarks",
  title: "Bookmarks",
  group: "workspace" as const,
  order: 50,
  component: BookmarksPage,
};

export default route;
