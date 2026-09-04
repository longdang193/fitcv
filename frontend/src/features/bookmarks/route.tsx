import React, { useState, useEffect, useCallback } from "react";
import { BookmarksTable } from "./components/BookmarksTable";
import { FitEvidenceDrawer } from "../job-evaluation/components/FitEvidenceDrawer";
import {
  fetchBookmarks,
  removeBookmarkSelection,
  previewBookmarkExport,
  exportBookmarkSelection,
  updateBookmarkInterest,
} from "./api";
import { BookmarkItem } from "./types";
import { RunJobItem } from "../runs/types";
import { Button, Dialog } from "../../components";
import { notificationStore } from "../../lib/notifications";

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

  const loadBookmarkList = useCallback(
    async (targetPage = 1) => {
      setLoading(true);
      try {
        setLoadError(null);
        const res = await fetchBookmarks({
          page: targetPage,
          page_size: pageSize,
          stage: stageFilter !== "all" ? stageFilter : undefined,
          search: activeSearch,
        });
        setBookmarks(res.data || []);
        setPage(res.page || targetPage);
        setTotal(res.total_items || 0);
      } catch (err: any) {
        setLoadError(err.message || "Failed to load bookmarks.");
        notificationStore.notify({
          dedupe: `req:load_bookmarks:${Date.now()}`,
          type: "error",
          title: "Failed to load bookmarks",
          message: err.message,
        });
      } finally {
        setLoading(false);
      }
    },
    [pageSize, stageFilter, activeSearch]
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

  const handleExport = async () => {
    setActionInProgress(true);
    try {
      const preview = await previewBookmarkExport({
        selected_run_job_ids: selectedJobIds,
        stage: stageFilter !== "all" ? stageFilter : undefined,
        search: activeSearch || undefined,
      });

      await exportBookmarkSelection({
        selected_run_job_ids: selectedJobIds,
        stage: stageFilter !== "all" ? stageFilter : undefined,
        search: activeSearch || undefined,
        preview_revision: preview.preview_revision,
      });

      notificationStore.notify({
        dedupe: `action:export_bookmarks:${Date.now()}`,
        type: "info",
        title: "Bookmark export started",
        message: `Exporting ${preview.matched_count} bookmarks to CSV.`,
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
        <div className="pipeline-stage-tabs" role="tablist" aria-label="Bookmark pipeline stages">
          {PIPELINE_STAGES.map((stage) => (
            <button
              key={stage.id}
              className="btn"
              type="button"
              role="tab"
              data-bookmark-stage={stage.id}
              aria-selected={stageFilter === stage.id}
              tabIndex={stageFilter === stage.id ? 0 : -1}
              onClick={() => {
                setStageFilter(stage.id);
                setPage(1);
                setSelectedJobIds([]);
              }}
            >
              {stage.label}
            </button>
          ))}
        </div>

        {/* Results Toolbar */}
        <div className="results-toolbar">
          <input
            className="field results-search"
            id="bookmarkSearch"
            type="search"
            value={search}
            onChange={(e) => {
              const val = e.target.value;
              setSearch(val);
              setActiveSearch(val.trim());
              setPage(1);
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
              onClick={handleExport}
            >
              Export
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
        <div id="bookmarkTablePanel">
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
              setPage(p);
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
