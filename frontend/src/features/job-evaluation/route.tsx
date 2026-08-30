import React, { useState, useEffect, useCallback } from "react";
import { JobEvaluationTable } from "./components/JobEvaluationTable";
import { FitEvidenceDrawer } from "./components/FitEvidenceDrawer";
import {
  setJobBookmark,
  clearJobBookmark,
  setJobInterest,
  clearJobInterest,
  previewRunJobExport,
  exportRunJobSelection,
} from "./api";
import { fetchRunJobs, fetchRuns } from "../runs/api";
import { RunJobItem, PipelineRunResource } from "../runs/types";
import { Button, LoadingState, EmptyState } from "../../components";
import { notificationStore } from "../../lib/notifications";

export const JobEvaluationPage: React.FC = () => {
  const [runs, setRuns] = useState<PipelineRunResource[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [loadingRuns, setLoadingRuns] = useState(true);

  const [jobs, setJobs] = useState<RunJobItem[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [stageFilter, setStageFilter] = useState("all");
  const [resultFilter, setResultFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [activeSearch, setActiveSearch] = useState("");

  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([]);
  const [inspectingJob, setInspectingJob] = useState<RunJobItem | null>(null);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Load available runs
  useEffect(() => {
    async function loadInitialRuns() {
      setLoadingRuns(true);
      try {
        const res = await fetchRuns({ view: "active", page: 1, page_size: 50 });
        const items = res.data || [];
        setRuns(items);
        if (items.length > 0) {
          // parse hash run_id if present
          const hash = window.location.hash || "";
          const parts = hash.split("?");
          if (parts.length > 1) {
            const params = new URLSearchParams(parts[1]);
            const rid = params.get("run_id");
            if (rid && items.some((r) => r.run_id === rid)) {
              setSelectedRunId(rid);
              return;
            }
          }
          setSelectedRunId(items[0].run_id);
        }
      } catch (err: any) {
        notificationStore.notify({
          dedupe: `req:load_runs:${Date.now()}`,
          type: "error",
          title: "Failed to load runs",
          message: err.message,
        });
      } finally {
        setLoadingRuns(false);
      }
    }
    loadInitialRuns();
  }, []);

  // Load jobs for selected run
  const loadEvaluationJobs = useCallback(
    async (targetPage = 1) => {
      if (!selectedRunId) return;
      setJobsLoading(true);
      try {
        const res = await fetchRunJobs(selectedRunId, {
          page: targetPage,
          page_size: 10,
          stage: stageFilter,
          result_bucket: resultFilter,
          search: activeSearch,
        });
        setJobs(res.data || []);
        setPage(res.page || targetPage);
        setTotal(res.total_items || 0);
      } catch (err: any) {
        notificationStore.notify({
          dedupe: `req:load_jobs:${Date.now()}`,
          type: "error",
          title: "Failed to load run jobs",
          message: err.message,
        });
      } finally {
        setJobsLoading(false);
      }
    },
    [selectedRunId, stageFilter, resultFilter, activeSearch]
  );

  useEffect(() => {
    if (selectedRunId) {
      loadEvaluationJobs(1);
    }
  }, [selectedRunId, loadEvaluationJobs]);

  const handleToggleBookmark = async (job: RunJobItem) => {
    const isBookmarked = !!job.bookmarked;
    // Optimistic update
    setJobs((prev) =>
      prev.map((j) => (j.run_job_id === job.run_job_id ? { ...j, bookmarked: !isBookmarked } : j))
    );

    try {
      if (isBookmarked) {
        await clearJobBookmark(selectedRunId, job.run_job_id);
        notificationStore.notify({
          dedupe: `bm:${job.run_job_id}:cleared:${Date.now()}`,
          type: "info",
          title: "Bookmark removed",
          message: `${job.title} removed from bookmarks.`,
        });
      } else {
        await setJobBookmark(selectedRunId, job.run_job_id);
        notificationStore.notify({
          dedupe: `bm:${job.run_job_id}:saved:${Date.now()}`,
          type: "success",
          title: "Bookmark saved",
          message: `${job.title} saved to bookmarks.`,
        });
      }
    } catch (err: any) {
      // Rollback
      setJobs((prev) =>
        prev.map((j) => (j.run_job_id === job.run_job_id ? { ...j, bookmarked: isBookmarked } : j))
      );
      notificationStore.notify({
        dedupe: `bm:err:${job.run_job_id}:${Date.now()}`,
        type: "error",
        title: "Bookmark action failed",
        message: err.message,
      });
    }
  };

  const handleChangeInterest = async (job: RunJobItem, newRating: number | null) => {
    const prevRating = job.interest_rating;
    // Optimistic update
    setJobs((prev) =>
      prev.map((j) => (j.run_job_id === job.run_job_id ? { ...j, interest_rating: newRating } : j))
    );

    try {
      if (newRating === null) {
        await clearJobInterest(selectedRunId, job.run_job_id);
      } else {
        await setJobInterest(selectedRunId, job.run_job_id, newRating);
      }
    } catch (err: any) {
      // Rollback
      setJobs((prev) =>
        prev.map((j) => (j.run_job_id === job.run_job_id ? { ...j, interest_rating: prevRating } : j))
      );
      notificationStore.notify({
        dedupe: `interest:err:${job.run_job_id}:${Date.now()}`,
        type: "error",
        title: "Interest update failed",
        message: err.message || "Failed to update Application Interest rating.",
      });
    }
  };

  const handleToggleSelectJob = (runJobId: string) => {
    setSelectedJobIds((prev) =>
      prev.includes(runJobId) ? prev.filter((id) => id !== runJobId) : [...prev, runJobId]
    );
  };

  const handleToggleSelectAll = () => {
    if (jobs.every((j) => selectedJobIds.includes(j.run_job_id))) {
      const visibleIds = new Set(jobs.map((j) => j.run_job_id));
      setSelectedJobIds((prev) => prev.filter((id) => !visibleIds.has(id)));
    } else {
      const combined = new Set([...selectedJobIds, ...jobs.map((j) => j.run_job_id)]);
      setSelectedJobIds(Array.from(combined));
    }
  };

  const handleExportFiltered = async () => {
    if (!selectedRunId) return;
    setActionInProgress(true);
    try {
      const preview = await previewRunJobExport(selectedRunId, {
        selected_run_job_ids: selectedJobIds,
        stage: stageFilter !== "all" ? stageFilter : undefined,
        result: resultFilter !== "all" ? resultFilter : undefined,
        search: activeSearch || undefined,
      });

      await exportRunJobSelection(selectedRunId, {
        selected_run_job_ids: selectedJobIds,
        stage: stageFilter !== "all" ? stageFilter : undefined,
        result: resultFilter !== "all" ? resultFilter : undefined,
        search: activeSearch || undefined,
        preview_revision: preview.preview_revision,
      });

      notificationStore.notify({
        dedupe: `export:run_jobs:${Date.now()}`,
        type: "info",
        title: "Export started",
        message: `Exporting ${preview.matched_count} matching jobs.`,
      });
    } catch (err: any) {
      notificationStore.notify({
        dedupe: `export:err:${Date.now()}`,
        type: "error",
        title: "Export failed",
        message: err.message || "Failed to export evaluated jobs.",
      });
    } finally {
      setActionInProgress(false);
    }
  };

  if (loadingRuns) {
    return <LoadingState message="Loading runs..." />;
  }

  if (runs.length === 0) {
    return (
      <div className="content-container">
        <EmptyState
          title="No Runs Available"
          description="Trigger a Run first to evaluate job suitability and record Application Interest."
          actionLabel="Go to Runs"
          onAction={() => {
            window.location.hash = "#/runs";
          }}
        />
      </div>
    );
  }

  return (
    <div className="content-container">
      {/* Page Header */}
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
            Evaluation & Fit
          </p>
          <h2
            style={{
              margin: 0,
              fontFamily: "var(--display-font)",
              fontSize: 24,
              letterSpacing: "-0.02em",
            }}
          >
            Job Evaluation & Results
          </h2>
          <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>
            Inspect server-evaluated fit evidence, record independent Application Interest, and bookmark jobs.
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
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
          {/* Run Selector */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label htmlFor="eval-run-select" style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)" }}>
              Run
            </label>
            <select
              id="eval-run-select"
              value={selectedRunId}
              onChange={(e) => {
                setSelectedRunId(e.target.value);
                setPage(1);
              }}
              className="field-input"
              style={{ fontSize: 13, padding: "6px 10px", minWidth: 200 }}
            >
              {runs.map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  {r.run_name || r.run_id} ({r.backend_status})
                </option>
              ))}
            </select>
          </div>

          {/* Stage Filter */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label htmlFor="eval-stage-select" style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)" }}>
              Stage
            </label>
            <select
              id="eval-stage-select"
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
            <label htmlFor="eval-result-select" style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)" }}>
              Result
            </label>
            <select
              id="eval-result-select"
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

        {/* Search & Export Action */}
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
              placeholder="Search jobs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="field-input"
              style={{ fontSize: 13, padding: "6px 10px", width: 180 }}
            />
            <Button type="submit" variant="secondary" size="compact">
              Search
            </Button>
          </form>

          <Button
            variant="secondary"
            size="compact"
            onClick={handleExportFiltered}
            disabled={actionInProgress || total === 0}
          >
            {selectedJobIds.length > 0
              ? `Export (${selectedJobIds.length} selected)`
              : "Export Filtered"}
          </Button>
        </div>
      </div>

      {/* Main Results Table */}
      <div className="table-card">
        <JobEvaluationTable
          jobs={jobs}
          loading={jobsLoading}
          page={page}
          pageSize={10}
          total={total}
          onPageChange={(p) => {
            setPage(p);
            loadEvaluationJobs(p);
          }}
          onToggleBookmark={handleToggleBookmark}
          onChangeInterest={handleChangeInterest}
          onInspectEvidence={(job) => setInspectingJob(job)}
          selectedJobIds={selectedJobIds}
          onToggleSelectJob={handleToggleSelectJob}
          onToggleSelectAll={handleToggleSelectAll}
        />
      </div>

      {/* Evidence Inspection Drawer */}
      <FitEvidenceDrawer
        job={inspectingJob}
        open={inspectingJob !== null}
        onClose={() => setInspectingJob(null)}
      />
    </div>
  );
};

export const route = {
  id: "job-evaluation",
  path: "#/job-evaluation",
  title: "Evaluation & Fit",
  group: "workspace" as const,
  order: 45,
  component: JobEvaluationPage,
};

export default route;
