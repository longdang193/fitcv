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
import { setJobBookmark, clearJobBookmark, setJobInterest, clearJobInterest } from "../job-evaluation/api";
import { fetchCvPreview, downloadCvVersion, regenerateCvVersion } from "../cv-review/api";
import { notificationStore } from "../../lib/notifications";
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
  // CV Preview dialog state
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewContent, setPreviewContent] = useState("");
  const [previewTitle, setPreviewTitle] = useState("");

  // CV Regenerate dialog state
  const [regenerateJob, setRegenerateJob] = useState<RunJobItem | null>(null);
  const [regeneratePrompt, setRegeneratePrompt] = useState("");
  const [regenerating, setRegenerating] = useState(false);
  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([]);


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
      const cancelledRun = await cancelRun(runId);
      setActionNotice(
        cancelledRun.backend_status === "cancelled"
          ? "Run cancelled."
          : "Cancellation request sent."
      );
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
  };
  // Bookmark toggle
  const handleToggleBookmark = async (job: RunJobItem) => {
    const isBookmarked = Boolean(job.bookmarked);
    setJobs((prev) =>
      prev.map((j) => (j.run_job_id === job.run_job_id ? { ...j, bookmarked: !isBookmarked } : j))
    );
    try {
      if (isBookmarked) {
        await clearJobBookmark(runId, job.run_job_id);
      } else {
        await setJobBookmark(runId, job.run_job_id);
      }
    } catch (err: any) {
      setJobs((prev) =>
        prev.map((j) => (j.run_job_id === job.run_job_id ? { ...j, bookmarked: isBookmarked } : j))
      );
      notificationStore.notify({
        dedupe: `bm:err:${job.run_job_id}`,
        type: "error",
        title: "Bookmark failed",
        message: err.message || "Could not update bookmark.",
      });
    }
  };

  // Interest rating
  const handleRateJob = async (job: RunJobItem, rating: number) => {
    const currentRating = typeof job.rating === "number" ? job.rating : job.interest_rating;
    const newRating = currentRating === rating ? null : rating;
    setJobs((prev) =>
      prev.map((j) =>
        j.run_job_id === job.run_job_id ? { ...j, rating: newRating, interest_rating: newRating } : j
      )
    );
    try {
      if (newRating === null) {
        await clearJobInterest(runId, job.run_job_id);
      } else {
        await setJobInterest(runId, job.run_job_id, newRating);
      }
    } catch (err: any) {
      setJobs((prev) =>
        prev.map((j) =>
          j.run_job_id === job.run_job_id ? { ...j, rating: currentRating, interest_rating: currentRating } : j
        )
      );
      notificationStore.notify({
        dedupe: `rate:err:${job.run_job_id}`,
        type: "error",
        title: "Rating failed",
        message: err.message || "Could not save rating.",
      });
    }
  };

  // View CV Preview
  const handleViewCv = async (job: RunJobItem) => {
    const versionId = String(job.current_cv_version_id || "");
    if (!versionId) return;
    setPreviewTitle(`${job.title || "Job"} · CV Preview`);
    setPreviewOpen(true);
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const res = await fetchCvPreview(versionId);
      setPreviewContent(res.content);
    } catch (err: any) {
      setPreviewError(err.message || "Failed to load CV preview.");
    } finally {
      setPreviewLoading(false);
    }
  };

  // Download CV
  const handleDownloadCv = async (job: RunJobItem) => {
    const versionId = String(job.current_cv_version_id || "");
    if (!versionId) return;
    try {
      await downloadCvVersion(versionId, `cv-${job.run_job_id.slice(0, 8)}.md`);
    } catch (err: any) {
      notificationStore.notify({
        dedupe: `cv:dl:err:${versionId}`,
        type: "error",
        title: "Download failed",
        message: err.message || "Could not download CV.",
      });
    }
  };

  // Open Regenerate Dialog
  const handleOpenRegenerate = (job: RunJobItem) => {
    setRegenerateJob(job);
    setRegeneratePrompt("");
  };

  // Confirm Regenerate
  const handleConfirmRegenerate = async () => {
    if (!regenerateJob) return;
    setRegenerating(true);
    try {
      await regenerateCvVersion(
        runId,
        regenerateJob.run_job_id,
        typeof regenerateJob.current_cv_version_id === "string" ? regenerateJob.current_cv_version_id : null
      );
      notificationStore.notify({
        dedupe: `cv:regen:${regenerateJob.run_job_id}`,
        type: "success",
        title: "Regeneration Queued",
        message: `CV regeneration started for ${regenerateJob.title}.`,
      });
      setRegenerateJob(null);
      loadJobs(jobsPage);
    } catch (err: any) {
      notificationStore.notify({
        dedupe: `cv:regen:err:${regenerateJob.run_job_id}`,
        type: "error",
        title: "Regeneration Failed",
        message: err.message || "Could not queue regeneration.",
      });
    } finally {
      setRegenerating(false);
    }
  };

  // Helper to extract application URL safely
  const getJobApplicationUrl = (item: RunJobItem): string => {
    const rawUrl =
      item.source_url ||
      item.job_url ||
      (item.source_snapshot as any)?.job_url ||
      (item.source_snapshot as any)?.jobUrl ||
      (item.source_snapshot as any)?.applyUrl ||
      (item.source_snapshot as any)?.url ||
      "";
    if (!rawUrl || typeof rawUrl !== "string") {
      return "#";
    }
    const clean = rawUrl.trim();
    return clean.startsWith("http://") || clean.startsWith("https://") ? clean : "#";
  };

  // Format skills list with prototype 5 + overflow chip
  const renderSkillChips = (item: RunJobItem) => {
    const rawSkills = item.skills || (item.source_snapshot as any)?.skills || (item.attributes as any)?.skills || [];
    const skillsList: string[] = Array.isArray(rawSkills) ? rawSkills.map(String) : [];
    if (skillsList.length === 0) {
      return <span style={{ color: "var(--muted)", fontSize: 12 }}>—</span>;
    }
    const visible = skillsList.slice(0, 5);
    const extra = skillsList.length - visible.length;
    return (
      <div className="skill-list">
        {visible.map((s, idx) => (
          <span key={idx} className="skill-chip">
            {s}
          </span>
        ))}
        {extra > 0 && <span className="skill-chip">+{extra} more</span>}
      </div>
    );
  };

  // Format job attributes
  const renderJobAttributes = (item: RunJobItem) => {
    const snapshot = (item.source_snapshot || item.attributes || {}) as Record<string, any>;
    const loc = item.location || snapshot.location || snapshot.city || "—";
    const mode = snapshot.work_mode || snapshot.workMode || item.work_mode || "—";
    const lang = snapshot.language || item.language || "—";
    const sen = snapshot.seniority || item.seniority || "—";
    const fam = snapshot.role_family || snapshot.job_family || snapshot.roleFamily || item.role_family || "—";
    const dom = snapshot.domain || snapshot.industry || item.domain || "—";

    const attrs = [
      ["Location", loc],
      ["Work Mode", mode],
      ["Language", lang],
      ["Seniority", sen],
      ["Job Family", fam],
      ["Domain", dom],
    ];

    return (
      <div className="job-attributes">
        {attrs.map(([label, val]) => (
          <div key={label} className="job-attribute">
            <span>{label}</span>
            <strong>{String(val)}</strong>
          </div>
        ))}
      </div>
    );
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

  // Job columns matching prototype specification
  const jobColumns: TableColumn<RunJobItem>[] = useMemo(() => {
    return [
      {
        key: "title_actions",
        header: "Job & Actions",
        render: (item) => {
          const appUrl = getJobApplicationUrl(item);
          const hasCv = Boolean(item.current_cv_version_id || (item.cv_versions_count && item.cv_versions_count > 0));
          const currentRating = typeof item.rating === "number" ? item.rating : item.interest_rating || 0;
          const isBookmarked = Boolean(item.bookmarked);
          const cvCanRegenerate = Boolean(item.capabilities?.regenerate_cv ?? hasCv);

          return (
            <div className="job-primary">
              <div className="job-title-row">
                <a
                  className="job-title-link"
                  href={appUrl !== "#" ? appUrl : undefined}
                  target={appUrl !== "#" ? "_blank" : undefined}
                  rel={appUrl !== "#" ? "noopener noreferrer" : undefined}
                  title={item.title || "Untitled Job"}
                >
                  {item.title || "Untitled Job"}
                </a>
              </div>

              {/* Interest Rating & Bookmark */}
              <div className="interest-rating" aria-label={`Application Interest for ${item.title || "Job"}`}>
                {[1, 2, 3, 4, 5].map((val) => (
                  <button
                    key={val}
                    type="button"
                    className="star-btn"
                    aria-label={`Rate ${val} of 5`}
                    aria-pressed={val <= currentRating}
                    onClick={() => handleRateJob(item, val)}
                  >
                    ★
                  </button>
                ))}
                <button
                  type="button"
                  className="small-action clear-rating"
                  disabled={!currentRating}
                  onClick={() => handleRateJob(item, 0)}
                >
                  Clear
                </button>
                <button
                  type="button"
                  className="small-action icon-only bookmark-btn"
                  aria-pressed={isBookmarked}
                  aria-label={`${isBookmarked ? "Remove" : "Add"} bookmark for ${item.title || "Job"}`}
                  title={`${isBookmarked ? "Remove" : "Add"} bookmark`}
                  onClick={() => handleToggleBookmark(item)}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M6 4.5A1.5 1.5 0 0 1 7.5 3h9A1.5 1.5 0 0 1 18 4.5V21l-6-3.75L6 21V4.5Z" />
                  </svg>
                </button>
              </div>

              {/* CV Actions in same table */}
              {(hasCv || cvCanRegenerate) && (
                <div className="job-action-row">
                  {hasCv && (
                    <>
                      <button
                        type="button"
                        className="small-action"
                        onClick={() => handleViewCv(item)}
                        aria-label={`View generated CV for ${item.title || "Job"}`}
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="13" height="13">
                          <path d="M2.5 12s3.5-5 9.5-5 9.5 5 9.5 5-3.5 5-9.5 5-9.5-5-9.5-5Z" />
                          <circle cx="12" cy="12" r="2.5" />
                        </svg>
                        <span>View CV</span>
                      </button>
                      <button
                        type="button"
                        className="small-action"
                        onClick={() => handleDownloadCv(item)}
                        aria-label={`Download generated CV for ${item.title || "Job"}`}
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="13" height="13">
                          <path d="M12 3v12m0 0 4-4m-4 4-4-4M5 19h14" />
                        </svg>
                        <span>Download CV</span>
                      </button>
                    </>
                  )}
                  {cvCanRegenerate && (
                    <button
                      type="button"
                      className="small-action"
                      onClick={() => handleOpenRegenerate(item)}
                      aria-label={`Regenerate CV for ${item.title || "Job"}`}
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="13" height="13">
                        <path d="M20 6v5h-5M4 18v-5h5M6.1 8A7 7 0 0 1 18 6l2 2M17.9 16A7 7 0 0 1 6 18l-2-2" />
                      </svg>
                      <span>Regenerate CV</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        },
      },
      {
        key: "job_attributes",
        header: "Job Attributes",
        render: (item) => renderJobAttributes(item),
      },
      {
        key: "required_skills",
        header: "Required Skills",
        render: (item) => renderSkillChips(item),
      },
      {
        key: "pipeline_outcome",
        header: "Pipeline Outcome",
        width: "200px",
        render: (item) => {
          const isPassed = item.result_bucket === "passed" || item.status === "passed" || item.status === "generated";
          const isRejected = item.result_bucket === "rejected" || item.status === "rejected" || item.status === "failed";
          const badgeStatus: StatusVariant = isPassed ? "success" : isRejected ? "danger" : "neutral";
          const label = String(item.outcome_code || (isPassed ? "Passed" : isRejected ? "Rejected" : item.status || "Pending"));
          const reason = String(item.reason_code || (item as any).stage_outcome_reason || (item as any).reject_reason || "");
          const isStretch = item.latest_cv_review_state === "stretch" || (item as any).cv_review_state === "stretch";

          return (
            <div className="pipeline-outcome">
              <StatusBadge status={badgeStatus} label={label} />
              {reason && <span className="outcome-reason">{reason}</span>}
              {isStretch && <span className="cv-review-tag">Stretch review</span>}
            </div>
          );
        },
      },
    ];
  }, [runId]);

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
  const runStatusLabel = run.backend_status === "cancelled"
    ? runStatusCfg.label
    : run.display_status || runStatusCfg.label;

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
          <StatusBadge status={runStatusCfg.variant} label={runStatusLabel} />
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
            {run.backend_status === "cancelled"
              ? "Run Cancelled"
              : run.backend_status === "failed"
              ? "Run Failed or Interrupted"
              : "Run Completed with Warnings / Partial Completion"}
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
            className="jobs-table"
            columns={jobColumns}
            data={jobs}
            keyField="run_job_id"
            selectedKeys={new Set(selectedJobIds)}
            onToggleSelect={(id) => setSelectedJobIds((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id])}
            onSelectAll={() => setSelectedJobIds((prev) => prev.length === jobs.length ? [] : jobs.map((j) => j.run_job_id))}
            isAllSelected={jobs.length > 0 && selectedJobIds.length === jobs.length}
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

            {/* CV Preview Dialog */}
      <Dialog
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        title={previewTitle || "CV Preview"}
        description="Review generated content without downloading a file."
        footer={
          <Button variant="primary" onClick={() => setPreviewOpen(false)}>
            Close
          </Button>
        }
      >
        {previewLoading && <LoadingState message="Loading CV preview..." />}
        {previewError && <div className="notice error">{previewError}</div>}
        {!previewLoading && !previewError && (
          <pre
            style={{
              padding: 16,
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-md)",
              fontFamily: "var(--font-mono)",
              fontSize: 13,
              whiteSpace: "pre-wrap",
              maxHeight: "60vh",
              overflowY: "auto",
            }}
          >
            {previewContent}
          </pre>
        )}
      </Dialog>

      {/* CV Regenerate Prompt Dialog */}
      <Dialog
        open={regenerateJob !== null}
        onClose={() => setRegenerateJob(null)}
        title={regenerateJob ? `Regenerate CV for ${regenerateJob.title}` : "Regenerate CV"}
        description="This creates a new CV artifact for this job using verified Candidate Profile evidence."
        footer={
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", width: "100%" }}>
            <Button variant="secondary" onClick={() => setRegenerateJob(null)} disabled={regenerating}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleConfirmRegenerate} loading={regenerating}>
              Regenerate CV
            </Button>
          </div>
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Field
            label="Regeneration Guidance (Optional)"
            placeholder="Focus on data engineering and Python architecture experience..."
            value={regeneratePrompt}
            onChange={(e) => setRegeneratePrompt(e.target.value)}
          />
        </div>
      </Dialog>

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
