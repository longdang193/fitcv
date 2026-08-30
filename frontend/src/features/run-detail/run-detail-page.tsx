import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  Button,
  StatusBadge,
  StatusVariant,
  LoadingState,
  EmptyState,
  DataTable,
  TableColumn,
  Dialog,
  Field,
} from "../../components";
import {
  fetchRun,
  fetchRunJobs,
  fetchRunEvents,
  cancelRun,
  archiveRun,
  unarchiveRun,
  downloadDebugBundle,
  exportRunJobsCsv,
} from "../runs/api";
import {
  PipelineRunResource,
  RunJobItem,
  RunEventRecord,
  RunStageResource,
  RunStageId,
} from "../runs/types";
import { StageCards } from "./components/StageCards";
import { InputSummaryCard } from "./components/InputSummaryCard";
import { EventConsole } from "./components/EventConsole";

export interface RunDetailPageProps {
  runId: string;
  onBack: () => void;
}

const statusMap: Record<string, { variant: StatusVariant; label: string }> = {
  queued: { variant: "neutral", label: "Queued" },
  running: { variant: "info", label: "Running" },
  awaiting_continue: { variant: "warn", label: "Awaiting Continue" },
  cancelling: { variant: "warn", label: "Cancelling" },
  succeeded: { variant: "success", label: "Succeeded" },
  failed: { variant: "danger", label: "Failed" },
  cancelled: { variant: "neutral", label: "Cancelled" },
};

const DEFAULT_STAGES: { stage_id: RunStageId; label: string; ordinal: number }[] = [
  { stage_id: "enrichment", label: "Enrichment", ordinal: 1 },
  { stage_id: "screening", label: "Screening", ordinal: 2 },
  { stage_id: "shortlisting", label: "Shortlisting", ordinal: 3 },
  { stage_id: "ranking", label: "Ranking", ordinal: 4 },
  { stage_id: "cv-analysis", label: "CV Analysis", ordinal: 5 },
  { stage_id: "cv-generation", label: "CV Generation", ordinal: 6 },
];

export const RunDetailPage: React.FC<RunDetailPageProps> = ({ runId, onBack }) => {
  const [run, setRun] = useState<PipelineRunResource | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Confirmation dialog
  const [confirmAction, setConfirmAction] = useState<"cancel" | "archive" | "unarchive" | null>(null);

  // Jobs state & filters
  const [jobs, setJobs] = useState<RunJobItem[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [jobsPage, setJobsPage] = useState(1);
  const [jobsTotal, setJobsTotal] = useState(0);
  const [jobsPageSize] = useState(10);
  const [stageFilter, setStageFilter] = useState<string>("all");
  const [resultBucketFilter, setResultBucketFilter] = useState<string>("all");
  const [jobSearch, setJobSearch] = useState("");
  const [activeJobSearch, setActiveJobSearch] = useState("");
  const [jobsMeta, setJobsMeta] = useState<{
    total_evaluated: number;
    passed: number;
    rejected: number;
    skipped: number;
  }>({ total_evaluated: 0, passed: 0, rejected: 0, skipped: 0 });

  // Events / Console State
  const [events, setEvents] = useState<RunEventRecord[]>([]);
  const eventCursorRef = useRef<string | null>(null);
  const pollTimerRef = useRef<number | null>(null);

  const isTerminal = useMemo(() => {
    if (!run) return false;
    return ["succeeded", "failed", "cancelled"].includes(run.backend_status);
  }, [run]);

  // Load main run detail
  const loadRunDetail = useCallback(async (isInitial = false) => {
    if (isInitial) setLoading(true);
    try {
      const res = await fetchRun(runId);
      setRun(res);
      setError(null);
    } catch (err: any) {
      if (isInitial) setError(err.message || "Failed to load run details.");
    } finally {
      if (isInitial) setLoading(false);
    }
  }, [runId]);

  // Load jobs
  const loadJobs = useCallback(async (page = 1) => {
    setJobsLoading(true);
    try {
      const res = await fetchRunJobs(runId, {
        page,
        page_size: jobsPageSize,
        stage: stageFilter,
        result_bucket: resultBucketFilter,
        search: activeJobSearch,
      });
      setJobs(res.data || []);
      setJobsPage(res.page || page);
      setJobsTotal(res.total_items || 0);
      if (res.meta) {
        setJobsMeta({
          total_evaluated: Number(res.meta.total_evaluated || 0),
          passed: Number(res.meta.passed || 0),
          rejected: Number(res.meta.rejected || 0),
          skipped: Number(res.meta.skipped || 0),
        });
      }
    } catch {
      // Ignored if output not ready yet
    } finally {
      setJobsLoading(false);
    }
  }, [runId, jobsPageSize, stageFilter, resultBucketFilter, activeJobSearch]);

  // Poll events
  const pollEvents = useCallback(async () => {
    try {
      const eventsRes = await fetchRunEvents(runId, eventCursorRef.current, 100);
      if (eventsRes.events && eventsRes.events.length > 0) {
        setEvents((prev) => {
          const existingIds = new Set(prev.map((e) => e.event_id));
          const fresh = eventsRes.events.filter((e) => !existingIds.has(e.event_id));
          return [...prev, ...fresh];
        });
        if (eventsRes.next_cursor) {
          eventCursorRef.current = eventsRes.next_cursor;
        }
      }
    } catch {
      // Background poll failure tolerated
    }
  }, [runId]);

  // Initial load
  useEffect(() => {
    loadRunDetail(true);
    loadJobs(1);
    pollEvents();
  }, [loadRunDetail, loadJobs, pollEvents]);

  // Polling loop for active runs
  useEffect(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
    }

    if (!isTerminal) {
      pollTimerRef.current = window.setInterval(() => {
        loadRunDetail(false);
        loadJobs(jobsPage);
        pollEvents();
      }, 2500);
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [isTerminal, loadRunDetail, loadJobs, pollEvents, jobsPage]);

  // Handlers for actions
  const handleCancel = async () => {
    setActionInProgress(true);
    setActionNotice(null);
    try {
      await cancelRun(runId);
      setActionNotice("Cancellation request sent.");
      setConfirmAction(null);
      await loadRunDetail(false);
      await pollEvents();
    } catch (err: any) {
      setError(err.message || "Failed to cancel run.");
    } finally {
      setActionInProgress(false);
    }
  };

  const handleArchive = async () => {
    setActionInProgress(true);
    setActionNotice(null);
    try {
      await archiveRun(runId);
      setActionNotice("Run archived.");
      setConfirmAction(null);
      await loadRunDetail(false);
    } catch (err: any) {
      setError(err.message || "Failed to archive run.");
    } finally {
      setActionInProgress(false);
    }
  };

  const handleUnarchive = async () => {
    setActionInProgress(true);
    setActionNotice(null);
    try {
      await unarchiveRun(runId);
      setActionNotice("Run restored to active.");
      setConfirmAction(null);
      await loadRunDetail(false);
    } catch (err: any) {
      setError(err.message || "Failed to restore run.");
    } finally {
      setActionInProgress(false);
    }
  };

  const handleDownloadDebugBundle = async () => {
    setActionInProgress(true);
    try {
      await downloadDebugBundle(runId);
    } catch (err: any) {
      setError(err.message || "Failed to download debug bundle.");
    } finally {
      setActionInProgress(false);
    }
  };

  const handleExportCsv = async () => {
    setActionInProgress(true);
    try {
      await exportRunJobsCsv(runId, {
        stage: stageFilter,
        result_bucket: resultBucketFilter,
        search: activeJobSearch,
      });
    } catch (err: any) {
      setError(err.message || "Failed to export jobs CSV.");
    } finally {
      setActionInProgress(false);
    }
  };

  const handleJobSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveJobSearch(jobSearch.trim());
    setJobsPage(1);
    loadJobs(1);
  };

  // Stages display
  const stages: RunStageResource[] = useMemo(() => {
    if (run?.stages && run.stages.length > 0) {
      return run.stages;
    }
    return DEFAULT_STAGES.map((s) => ({
      stage_id: s.stage_id,
      label: s.label,
      ordinal: s.ordinal,
      status: "pending",
    }));
  }, [run]);

  // Job columns
  const jobColumns: TableColumn<RunJobItem>[] = useMemo(() => {
    return [
      {
        key: "title",
        header: "Job Title & Company",
        render: (item) => (
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>{item.title || "Untitled Job"}</span>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>
              {item.company} {item.location ? `· ${item.location}` : ""} · <span style={{ fontFamily: "var(--font-mono)" }}>{item.job_id || item.run_job_id}</span>
            </span>
          </div>
        ),
      },
      {
        key: "current_stage_id",
        header: "Current Stage",
        width: "140px",
        render: (item) => (
          <span style={{ fontSize: 13, textTransform: "capitalize" }}>
            {item.current_stage_id || "—"}
          </span>
        ),
      },
      {
        key: "result_bucket",
        header: "Result",
        width: "110px",
        render: (item) => {
          if (item.result_bucket === "passed") {
            return <StatusBadge status="success" label="Passed" />;
          }
          if (item.result_bucket === "rejected") {
            return <StatusBadge status="danger" label="Rejected" />;
          }
          return <span style={{ color: "var(--muted)", fontSize: 13 }}>—</span>;
        },
      },
      {
        key: "status",
        header: "Stage Outcome",
        width: "130px",
        render: (item) => {
          const variant: StatusVariant =
            item.status === "passed" || item.status === "generated"
              ? "success"
              : item.status === "rejected" || item.status === "failed" || item.status === "blocked"
              ? "danger"
              : item.status === "review_required"
              ? "warn"
              : "neutral";
          return <StatusBadge status={variant} label={item.status || "pending"} />;
        },
      },
      {
        key: "cv_status",
        header: "CV Generation",
        width: "140px",
        render: (item) => {
          if (item.cv_versions_count && item.cv_versions_count > 0) {
            return (
              <span style={{ fontSize: 13, color: "var(--info)", fontWeight: 500 }}>
                {item.cv_versions_count} version(s)
              </span>
            );
          }
          if (item.latest_cv_generation_status) {
            return <span style={{ fontSize: 12 }}>{item.latest_cv_generation_status}</span>;
          }
          return <span style={{ color: "var(--muted)", fontSize: 12 }}>None</span>;
        },
      },
    ];
  }, []);

  if (loading) {
    return <LoadingState message="Loading run details..." />;
  }

  if (error && !run) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Button variant="secondary" onClick={onBack} style={{ alignSelf: "flex-start" }}>
          ← Back to Runs
        </Button>
        <div className="notice error" role="alert">
          {error}
        </div>
      </div>
    );
  }

  if (!run) {
    return (
      <EmptyState
        title="Run not found"
        description="The requested run could not be located."
        actionLabel="Back to Runs"
        onAction={onBack}
      />
    );
  }

  const runStatusCfg = statusMap[run.backend_status] || {
    variant: "neutral" as StatusVariant,
    label: run.display_status || run.backend_status,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Top Bar Navigation */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Button variant="secondary" size="compact" onClick={onBack}>
            ← Back to Runs
          </Button>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>
            {run.run_name || run.run_id}
          </h1>
          <StatusBadge status={runStatusCfg.variant} label={run.display_status || runStatusCfg.label} />
        </div>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Button
            size="compact"
            variant="secondary"
            onClick={() => {
              loadRunDetail(false);
              loadJobs(jobsPage);
              pollEvents();
            }}
            disabled={actionInProgress}
          >
            Refresh
          </Button>

          {run.capabilities.export && (
            <Button
              size="compact"
              variant="secondary"
              onClick={handleExportCsv}
              disabled={actionInProgress}
            >
              Export CSV
            </Button>
          )}

          {run.debug_bundle?.status === "available" && (
            <Button
              size="compact"
              variant="secondary"
              onClick={handleDownloadDebugBundle}
              disabled={actionInProgress}
            >
              Download Debug Bundle
            </Button>
          )}

          {run.capabilities.cancel && (
            <Button
              size="compact"
              variant="danger"
              onClick={() => setConfirmAction("cancel")}
              disabled={actionInProgress}
            >
              Cancel Run
            </Button>
          )}

          {run.capabilities.archive && (
            <Button
              size="compact"
              variant="subtle"
              onClick={() => setConfirmAction("archive")}
              disabled={actionInProgress}
            >
              Archive
            </Button>
          )}

          {run.capabilities.unarchive && (
            <Button
              size="compact"
              variant="subtle"
              onClick={() => setConfirmAction("unarchive")}
              disabled={actionInProgress}
            >
              Restore
            </Button>
          )}
        </div>
      </div>

      {actionNotice && (
        <div className="notice success" role="status">
          {actionNotice}
        </div>
      )}

      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}

      {/* Terminal / Recovery / Failure Banner */}
      {(run.backend_status === "failed" || run.partial_completion || run.errors?.code || (run.integrity_warnings && run.integrity_warnings.length > 0)) && (
        <div className="notice danger" role="alert" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontWeight: 600, fontSize: 15 }}>
            {run.backend_status === "failed" ? "Run Failed or Interrupted" : "Run Completed with Warnings / Partial Completion"}
          </div>
          {run.errors?.message && <div>{run.errors.message}</div>}
          {run.status_detail && <div style={{ fontSize: 13 }}>Detail: {run.status_detail}</div>}
          {run.partial_completion && (
            <div style={{ fontSize: 13 }}>
              Partial completion: evaluated stages and usable results have been retained and remain inspectable below.
            </div>
          )}
          {run.integrity_warnings && run.integrity_warnings.length > 0 && (
            <div style={{ fontSize: 12 }}>
              <strong>Integrity checks:</strong> {run.integrity_warnings.map((w) => w.code).join(", ")}
            </div>
          )}
        </div>
      )}

      {/* Input Summary & Metrics Card */}
      <InputSummaryCard run={run} />

      {/* 6-Stage Stepper Cards */}
      <StageCards
        stages={stages}
        selectedStage={stageFilter}
        onSelectStage={(st) => {
          setStageFilter(st);
          setJobsPage(1);
        }}
      />

      {/* Jobs Table & Filter Bar */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 600, margin: "0 0 4px 0" }}>
              Pipeline Results & Jobs {stageFilter !== "all" ? `(${stageFilter})` : ""}
            </h2>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>
              Evaluated: <strong>{jobsMeta.total_evaluated}</strong> · Passed: <strong style={{ color: "var(--success)" }}>{jobsMeta.passed}</strong> · Rejected: <strong style={{ color: "var(--danger)" }}>{jobsMeta.rejected}</strong> · Skipped: <strong>{jobsMeta.skipped}</strong>
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <select
              value={stageFilter}
              onChange={(e) => {
                setStageFilter(e.target.value);
                setJobsPage(1);
              }}
              className="field-input"
              style={{ fontSize: 13, padding: "6px 10px" }}
              aria-label="Filter by stage"
            >
              <option value="all">All Stages</option>
              {DEFAULT_STAGES.map((s) => (
                <option key={s.stage_id} value={s.stage_id}>
                  Stage {s.ordinal}: {s.label}
                </option>
              ))}
            </select>

            <select
              value={resultBucketFilter}
              onChange={(e) => {
                setResultBucketFilter(e.target.value);
                setJobsPage(1);
              }}
              className="field-input"
              style={{ fontSize: 13, padding: "6px 10px" }}
              aria-label="Filter by result"
            >
              <option value="all">All Results</option>
              <option value="passed">Passed</option>
              <option value="rejected">Rejected</option>
            </select>

            <form onSubmit={handleJobSearchSubmit} style={{ display: "flex", gap: 6, alignItems: "flex-end" }}>
              <div style={{ width: 180 }}>
                <Field
                  label=""
                  type="search"
                  placeholder="Search jobs..."
                  value={jobSearch}
                  onChange={(e) => setJobSearch(e.target.value)}
                />
              </div>
              <Button type="submit" variant="secondary" size="compact">
                Filter
              </Button>
            </form>
          </div>
        </div>

        {jobsLoading ? (
          <LoadingState message="Loading jobs..." />
        ) : (
          <DataTable
            columns={jobColumns}
            data={jobs}
            keyField="run_job_id"
            page={jobsPage}
            pageSize={jobsPageSize}
            total={jobsTotal}
            onPageChange={(p) => {
              setJobsPage(p);
              loadJobs(p);
            }}
            emptyMessage="No jobs found matching criteria."
          />
        )}
      </div>

      {/* Live Console & Event Stream */}
      <EventConsole
        events={events}
        isLive={!isTerminal}
        onRefresh={pollEvents}
      />

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmAction !== null}
        onClose={() => setConfirmAction(null)}
        title={
          confirmAction === "cancel"
            ? "Cancel Run?"
            : confirmAction === "archive"
            ? "Archive Run?"
            : "Restore Run?"
        }
        description={
          confirmAction === "cancel"
            ? `Are you sure you want to cancel run ${run.run_id}? Current stage processing will be interrupted.`
            : confirmAction === "archive"
            ? `Archiving run ${run.run_id} will move it to historical archives.`
            : `Restore run ${run.run_id} to active workspace.`
        }
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, width: "100%" }}>
            <Button
              variant="secondary"
              onClick={() => setConfirmAction(null)}
              disabled={actionInProgress}
            >
              Cancel
            </Button>
            <Button
              variant={confirmAction === "cancel" ? "danger" : "primary"}
              onClick={
                confirmAction === "cancel"
                  ? handleCancel
                  : confirmAction === "archive"
                  ? handleArchive
                  : handleUnarchive
              }
              disabled={actionInProgress}
            >
              {actionInProgress ? "Processing..." : "Confirm"}
            </Button>
          </div>
        }
      >
        <div style={{ fontSize: 14 }}>
          <strong>Run ID:</strong> {run.run_id}
          <br />
          <strong>Run Name:</strong> {run.run_name || "N/A"}
        </div>
      </Dialog>
    </div>
  );
};
