import React, { useState, useEffect, useCallback } from "react";
import { BookmarksTable } from "./components/BookmarksTable";
import { FitEvidenceDrawer } from "../job-evaluation/components/FitEvidenceDrawer";
import {
  fetchBookmarks,
  removeBookmarkSelection,
  previewBookmarkExport,
  exportBookmarkSelection,
} from "./api";
import { BookmarkItem } from "./types";
import { RunJobItem } from "../runs/types";
import { Button, Dialog } from "../../components";
import { notificationStore } from "../../lib/notifications";

export const BookmarksPage: React.FC = () => {
  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);

  const [stageFilter, setStageFilter] = useState("all");
  const [resultFilter, setResultFilter] = useState("all");
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
        const res = await fetchBookmarks({
          page: targetPage,
          page_size: pageSize,
          stage: stageFilter,
          result: resultFilter,
          search: activeSearch,
        });
        setBookmarks(res.data || []);
        setPage(res.page || targetPage);
        setTotal(res.total_items || 0);
      } catch (err: any) {
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
    [pageSize, stageFilter, resultFilter, activeSearch]
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
      status: bm.status || "passed",
      result_bucket: bm.result_bucket || null,
      bookmarked: true,
      interest_rating: bm.rating,
      attributes: {
        reasons: bm.reason_code ? [bm.reason_code] : [],
        fit_factor_results: bm.evidence || {},
      },
    };
    setInspectingJob(projectedJob);
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
        result: resultFilter !== "all" ? resultFilter : undefined,
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
        result: resultFilter !== "all" ? resultFilter : undefined,
        search: activeSearch || undefined,
      });

      await exportBookmarkSelection({
        selected_run_job_ids: selectedJobIds,
        stage: stageFilter !== "all" ? stageFilter : undefined,
        result: resultFilter !== "all" ? resultFilter : undefined,
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

  return (
    <div className="content-container">
      {/* Page Head */}
      <div className="page-head" style={{ marginBottom: 20 }}>
        <div>
          <p
            className="eyebrow"
            style={{
              color: "var(--accent)",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              margin: "0 0 4px",
            }}
          >
            Saved Workspace
          </p>
          <h2
            style={{
              margin: 0,
              fontFamily: "var(--display-font)",
              fontSize: 24,
              letterSpacing: "-0.02em",
            }}
          >
            Bookmarks
          </h2>
          <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>
            Review bookmarked jobs across pipeline runs with preserved fit evidence and interest ratings.
          </p>
        </div>
      </div>

      {/* Filter and Action Toolbar */}
      <div
        className="table-card"
        style={{
          padding: "16px 20px",
          marginBottom: 16,
          display: "flex",
          gap: 12,
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          {/* Stage Filter */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label htmlFor="bm-stage-select" style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)" }}>
              Stage
            </label>
            <select
              id="bm-stage-select"
              value={stageFilter}
              onChange={(e) => {
                setStageFilter(e.target.value);
                setPage(1);
              }}
              className="field-input"
              style={{ fontSize: 13, padding: "6px 10px" }}
            >
              <option value="all">All Stages</option>
              <option value="enrichment">Enrichment</option>
              <option value="screening">Screening</option>
              <option value="shortlisting">Shortlisting</option>
              <option value="ranking">Ranking</option>
              <option value="cv-analysis">CV Analysis</option>
              <option value="cv-generation">CV Generation</option>
            </select>
          </div>

          {/* Result Filter */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label htmlFor="bm-result-select" style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)" }}>
              Result
            </label>
            <select
              id="bm-result-select"
              value={resultFilter}
              onChange={(e) => {
                setResultFilter(e.target.value);
                setPage(1);
              }}
              className="field-input"
              style={{ fontSize: 13, padding: "6px 10px" }}
            >
              <option value="all">All Results</option>
              <option value="passed">Passed</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>

        {/* Search, Batch Remove, Export */}
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setActiveSearch(search.trim());
              setPage(1);
            }}
            style={{ display: "flex", gap: 6 }}
          >
            <input
              type="search"
              placeholder="Search bookmarks..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="field-input"
              style={{ fontSize: 13, padding: "6px 10px", width: 180 }}
            />
            <Button type="submit" variant="secondary" size="compact">
              Search
            </Button>
          </form>

          {selectedJobIds.length > 0 && (
            <Button
              variant="danger"
              size="compact"
              onClick={() => setConfirmRemove({ isBatch: true })}
              disabled={actionInProgress}
            >
              Remove ({selectedJobIds.length})
            </Button>
          )}

          <Button
            variant="secondary"
            size="compact"
            onClick={handleExport}
            disabled={actionInProgress || total === 0}
          >
            Export CSV
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="table-card">
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
        />
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
