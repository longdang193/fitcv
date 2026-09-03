import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  Button,
  StatusBadge,
  StatusVariant,
  LoadingState,
  EmptyState,
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
  RunStageId,
} from "../runs/types";
import { setJobBookmark, clearJobBookmark, setJobInterest, clearJobInterest } from "../job-evaluation/api";
import { fetchCvPreview, downloadCvVersion, regenerateCvVersion } from "../cv-review/api";
import { notificationStore } from "../../lib/notifications";
import { EventConsole } from "./components/EventConsole";

export interface RunDetailPageProps {
  runId: string;
  onBack: () => void;
  initialRun?: PipelineRunResource;
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

const PIPELINE_STAGES: { stage_id: RunStageId; label: string; ordinal: number }[] = [
  { stage_id: "enrichment", label: "Enrichment", ordinal: 1 },
  { stage_id: "screening", label: "Screening", ordinal: 2 },
  { stage_id: "shortlisting", label: "Shortlisting", ordinal: 3 },
  { stage_id: "ranking", label: "Ranking", ordinal: 4 },
  { stage_id: "cv-analysis", label: "CV Analysis", ordinal: 5 },
  { stage_id: "cv-generation", label: "CV Generation", ordinal: 6 },
];

const PAGE_SIZE_OPTIONS = [10, 20, 50];

export const RunDetailPage: React.FC<RunDetailPageProps> = ({ runId, onBack, initialRun }) => {
  const [run, setRun] = useState<PipelineRunResource | null>(initialRun || null);
  const [loading, setLoading] = useState(!initialRun);
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

  // Jobs state & filters (stage defaults to shortlisting per prototype)
  const [jobs, setJobs] = useState<RunJobItem[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [jobsPage, setJobsPage] = useState(1);
  const [jobsTotal, setJobsTotal] = useState(0);
  const [jobsPageSize, setJobsPageSize] = useState(10);
  const [stageFilter, setStageFilter] = useState<string>("shortlisting");
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
  const searchDebounceRef = useRef<number | null>(null);

  const isTerminal = useMemo(() => {
    if (!run) return false;
    return ["succeeded", "failed", "cancelled"].includes(run.backend_status);
  }, [run]);

  // Debounce search input
  useEffect(() => {
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }
    searchDebounceRef.current = window.setTimeout(() => {
      setActiveJobSearch(jobSearch.trim());
      setJobsPage(1);
    }, 250);
    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    };
  }, [jobSearch]);

  // Load main run detail
  const loadRunDetail = useCallback(async (isInitial = false) => {
    if (isInitial) setLoading(true);
    try {
      const res = await fetchRun(runId);
      setRun(res);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load run details.");
    } finally {
      if (isInitial) setLoading(false);
    }
  }, [runId]);
  // Load jobs
  const loadJobs = useCallback(async (page = 1, overridePageSize?: number) => {
    setJobsLoading(true);
    try {
      const res = await fetchRunJobs(runId, {
        page,
        page_size: overridePageSize || jobsPageSize,
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
      // Background tolerance
    } finally {
      setJobsLoading(false);
    }
  }, [runId, jobsPageSize, stageFilter, resultBucketFilter, activeJobSearch]);

  // Poll events without reloading page
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

  // Reload jobs on filter / search changes
  useEffect(() => {
    loadJobs(1);
  }, [stageFilter, resultBucketFilter, activeJobSearch]);

  // Polling loop for active runs
  useEffect(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
    }

    if (!isTerminal) {
      pollTimerRef.current = window.setInterval(() => {
        loadRunDetail(false);
        pollEvents();
      }, 2500);
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [isTerminal, loadRunDetail, pollEvents]);

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
        dedupe: "bm:err:" + job.run_job_id,
        type: "error",
        title: "Bookmark failed",
        message: err.message || "Could not update bookmark.",
      });
    }
  };

  // Interest rating
  const handleRateJob = async (job: RunJobItem, rating: number) => {
    const currentRating = typeof job.rating === "number" ? job.rating : job.interest_rating || 0;
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
        dedupe: "rate:err:" + job.run_job_id,
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
    setPreviewTitle((job.title || "Job") + " — CV Preview");
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
      await downloadCvVersion(versionId, "cv-" + job.run_job_id.slice(0, 8) + ".md");
    } catch (err: any) {
      notificationStore.notify({
        dedupe: "cv:dl:err:" + versionId,
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
        dedupe: "cv:regen:" + regenerateJob.run_job_id,
        type: "success",
        title: "Regeneration Queued",
        message: "CV regeneration started for " + regenerateJob.title + ".",
      });
      setRegenerateJob(null);
      loadJobs(jobsPage);
    } catch (err: any) {
      notificationStore.notify({
        dedupe: "cv:regen:err:" + regenerateJob.run_job_id,
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

  // Pagination calculation
  const totalPages = Math.max(1, Math.ceil(jobsTotal / jobsPageSize));
  const pageStart = jobsTotal ? (jobsPage - 1) * jobsPageSize + 1 : 0;
  const pageEnd = Math.min(jobsTotal, jobsPage * jobsPageSize);

  // Toggle select all visible jobs
  const isAllVisibleSelected = jobs.length > 0 && jobs.every((j) => selectedJobIds.includes(j.run_job_id));
  const isSomeVisibleSelected = !isAllVisibleSelected && jobs.some((j) => selectedJobIds.includes(j.run_job_id));

  const handleToggleSelectAllVisible = () => {
    if (isAllVisibleSelected) {
      const visibleIds = new Set(jobs.map((j) => j.run_job_id));
      setSelectedJobIds((prev) => prev.filter((id) => !visibleIds.has(id)));
    } else {
      const combined = new Set([...selectedJobIds, ...jobs.map((j) => j.run_job_id)]);
      setSelectedJobIds(Array.from(combined));
    }
  };
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

  // Extract input details
  const input = run.input;
  let parsedProfile: Record<string, any> | null = null;
  let parsedSources: any[] = [];
  if (input?.candidate_profile_json) {
    try { parsedProfile = JSON.parse(input.candidate_profile_json); } catch {}
  }
  if (input?.jobs_input_manifest_json) {
    try {
      const manifest = JSON.parse(input.jobs_input_manifest_json);
      if (manifest.sources && Array.isArray(manifest.sources)) {
        parsedSources = manifest.sources;
      }
    } catch {}
  }
  const profileName = parsedProfile?.name || parsedProfile?.profile_name || input?.candidate_profile_source || "Candidate Profile";
  const profileId = parsedProfile?.id || parsedProfile?.profile_id || "—";
  const profileState = parsedProfile?.archived ? "Archived · historical reference" : "Active";
  const uploadFileName = input?.upload_file_name || input?.filename || "";
  const scanSources = parsedSources.filter((s: any) => s.type === "scan");

  return (
    <div className="run-detail-page details-page-layout" style={{ display: "flex", flexDirection: "column", gap: 18, width: "100%" }}>
      {/* Top Header Navigation */}
      <div className="details-page-head">
        <a
          className="details-page-back"
          href="#/runs"
          onClick={(e) => {
            e.preventDefault();
            onBack();
          }}
        >
          ← Back to Runs
        </a>
        <div className="page-head">
          <div>
            <p className="eyebrow">Run Details</p>
            <h2>Run {run.run_name || run.run_id}</h2>
            <p>Review run inputs and pipeline results.</p>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
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
                variant="secondary"
                onClick={() => setConfirmAction("archive")}
                disabled={actionInProgress}
              >
                Archive
              </Button>
            )}

            {run.capabilities.unarchive && (
              <Button
                size="compact"
                variant="secondary"
                onClick={() => setConfirmAction("unarchive")}
                disabled={actionInProgress}
              >
                Restore
              </Button>
            )}
          </div>
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
      {/* Section 1: Run Overview */}
      <details className="section-card collapsible-section drawer-section" open>
        <summary>
          <span className="section-heading">
            <strong>Run Overview</strong>
            <span>Current lifecycle information for this run.</span>
          </span>
          <span className="drawer-status">
            <StatusBadge status={runStatusCfg.variant} label={runStatusLabel} />
          </span>
        </summary>
        <div className="section-content drawer-section-content">
          <dl className="details-grid">
            <div className="detail-item">
              <dt>Run ID</dt>
              <dd>{run.run_id}</dd>
            </div>
            <div className="detail-item">
              <dt>Run Name</dt>
              <dd>{run.run_name || run.run_id}</dd>
            </div>
            <div className="detail-item">
              <dt>Created</dt>
              <dd>{new Date(run.created_at).toLocaleString()}</dd>
            </div>
            <div className="detail-item">
              <dt>Started</dt>
              <dd>{run.started_at ? new Date(run.started_at).toLocaleString() : new Date(run.created_at).toLocaleString()}</dd>
            </div>
            <div className="detail-item">
              <dt>Finished</dt>
              <dd>{run.finished_at ? new Date(run.finished_at).toLocaleString() : "—"}</dd>
            </div>
          </dl>
        </div>
      </details>

      {/* Section 2: Run Input */}
      <details className="section-card collapsible-section drawer-section" open>
        <summary>
          <span className="section-heading">
            <strong>Run Input</strong>
            <span>Read-only inputs used when this run was triggered.</span>
          </span>
        </summary>
        <div className="section-content drawer-section-content">
          <dl className="details-grid run-input-details">
            <div className="detail-item">
              <dt>Job Input</dt>
              <dd>
                {uploadFileName && scanSources.length > 0
                  ? "Upload + Scan outputs"
                  : scanSources.length > 0
                  ? "Output from Scan"
                  : String(uploadFileName || (input?.jobs_input_source as string) || "Upload")}
              </dd>
            </div>
            {uploadFileName && (
              <div className="detail-item">
                <dt>Uploaded File</dt>
                <dd>{String(uploadFileName)}</dd>
              </div>
            )}
            {scanSources.length > 0 && (
              <div className="detail-item">
                <dt>Source Scans</dt>
                <dd>{scanSources.map((s: any) => s.scan_name || s.scan_id).join(", ")}</dd>
              </div>
            )}
            <div className="detail-item">
              <dt>Candidate Profile</dt>
              <dd>{profileName}</dd>
            </div>
            <div className="detail-item">
              <dt>Profile ID</dt>
              <dd>{profileId}</dd>
            </div>
            <div className="detail-item">
              <dt>Profile State</dt>
              <dd>{profileState}</dd>
            </div>
            <div className="detail-item">
              <dt>Configuration Snapshot</dt>
              <dd>Pipeline Settings and Synonyms captured when this run was triggered.</dd>
            </div>
          </dl>
        </div>
      </details>

      {/* Section 3: Pipeline Results */}
      <details className="section-card collapsible-section drawer-section" open>
        <summary>
          <span className="section-heading">
            <strong>Pipeline Results</strong>
            <span>Includes passed and rejected jobs evaluated at the selected stage.</span>
          </span>
        </summary>
        <div className="section-content drawer-section-content">
          {/* Stage Tabs Filter */}
          <div className="results-filters">
            <div className="stage-filter" style={{ width: "100%" }}>
              <div className="pipeline-stage-tabs" role="tablist" aria-label="Pipeline stages">
                {PIPELINE_STAGES.map((stage) => (
                  <button
                    key={stage.stage_id}
                    className="btn"
                    type="button"
                    role="tab"
                    data-pipeline-stage={stage.stage_id}
                    aria-selected={stageFilter === stage.stage_id}
                    tabIndex={stageFilter === stage.stage_id ? 0 : -1}
                    onClick={() => {
                      setStageFilter(stage.stage_id);
                      setResultBucketFilter("all");
                      setJobsPage(1);
                      setSelectedJobIds([]);
                    }}
                  >
                    {stage.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Results Toolbar with Search, Summary Cards, and Export Button */}
          <div className="results-toolbar">
            <input
              className="field results-search"
              id="jobResultsSearch"
              type="search"
              value={jobSearch}
              onChange={(e) => setJobSearch(e.target.value)}
              placeholder="Search jobs, attributes, skills, or outcomes"
              aria-label="Search pipeline results"
            />
            <div className="results-toolbar-actions">
              <div className="pipeline-summary" role="tablist" aria-label="Pipeline result filter">
                <button
                  className="summary-card"
                  type="button"
                  role="tab"
                  data-pipeline-result="all"
                  aria-selected={resultBucketFilter === "all"}
                  tabIndex={resultBucketFilter === "all" ? 0 : -1}
                  onClick={() => {
                    setResultBucketFilter("all");
                    setJobsPage(1);
                  }}
                >
                  <span>Total Evaluated</span>
                  <strong>{jobsMeta.total_evaluated}</strong>
                </button>
                <button
                  className="summary-card"
                  type="button"
                  role="tab"
                  data-pipeline-result="passed"
                  aria-selected={resultBucketFilter === "passed"}
                  tabIndex={resultBucketFilter === "passed" ? 0 : -1}
                  onClick={() => {
                    setResultBucketFilter("passed");
                    setJobsPage(1);
                  }}
                >
                  <span>Passed</span>
                  <strong style={{ color: "var(--success)" }}>{jobsMeta.passed}</strong>
                </button>
                <button
                  className="summary-card"
                  type="button"
                  role="tab"
                  data-pipeline-result="rejected"
                  aria-selected={resultBucketFilter === "rejected"}
                  tabIndex={resultBucketFilter === "rejected" ? 0 : -1}
                  onClick={() => {
                    setResultBucketFilter("rejected");
                    setJobsPage(1);
                  }}
                >
                  <span>Rejected</span>
                  <strong style={{ color: "var(--danger)" }}>{jobsMeta.rejected}</strong>
                </button>
              </div>

              {run.capabilities.export && (
                <Button
                  id="exportRunResults"
                  size="compact"
                  variant="secondary"
                  onClick={handleExportCsv}
                  disabled={actionInProgress}
                >
                  Export
                </Button>
              )}
            </div>
          </div>
          {/* Run Panel with Selection Banner, Table, and Pagination */}
          <div className="run-panel">
            {selectedJobIds.length > 0 && (
              <div className="run-selection">
                <div className="run-selection-copy">
                  <strong>{selectedJobIds.length} job{selectedJobIds.length === 1 ? "" : "s"} selected</strong>
                  <span>Export applies only to selected jobs in the current stage and filters.</span>
                </div>
              </div>
            )}

            {jobsLoading ? (
              <LoadingState message="Loading jobs..." />
            ) : (
              <div className="table-card">
                <div className="table-scroll" tabIndex={0} role="region" aria-label="Pipeline job results">
                  <table className="run-table jobs-table">
                    <thead>
                      <tr>
                        <th>
                          <input
                            id="selectAllJobResults"
                            type="checkbox"
                            aria-label="Select all visible job results"
                            checked={isAllVisibleSelected}
                            ref={(el) => {
                              if (el) el.indeterminate = isSomeVisibleSelected;
                            }}
                            onChange={handleToggleSelectAllVisible}
                          />{" "}
                          Job &amp; Actions
                        </th>
                        <th>Job Attributes</th>
                        <th>Required Skills</th>
                        <th>Pipeline Outcome</th>
                      </tr>
                    </thead>
                    <tbody>
                      {jobs.length === 0 ? (
                        <tr>
                          <td colSpan={4} style={{ textAlign: "center", padding: "32px 16px", color: "var(--muted)" }}>
                            No jobs match current filters.
                          </td>
                        </tr>
                      ) : (
                        jobs.map((item) => {
                          const appUrl = getJobApplicationUrl(item);
                          const hasCv = Boolean(item.current_cv_version_id || (item.cv_versions_count && item.cv_versions_count > 0));
                          const currentRating = typeof item.rating === "number" ? item.rating : item.interest_rating || 0;
                          const isBookmarked = Boolean(item.bookmarked);
                          const cvCanRegenerate = Boolean(item.capabilities?.regenerate_cv ?? hasCv);
                          const isSelected = selectedJobIds.includes(item.run_job_id);

                          const isPassed = item.result_bucket === "passed" || item.status === "passed" || item.status === "generated";
                          const isRejected = item.result_bucket === "rejected" || item.status === "rejected" || item.status === "failed";
                          const badgeStatus: StatusVariant = isPassed ? "success" : isRejected ? "danger" : "neutral";
                          const label = String(item.outcome_code || (isPassed ? "Passed" : isRejected ? "Rejected" : item.status || "Pending"));
                          const reason = String(item.reason_code || (item as any).stage_outcome_reason || (item as any).reject_reason || "");
                          const isStretch = item.latest_cv_review_state === "stretch" || (item as any).cv_review_state === "stretch";

                          return (
                            <tr key={item.run_job_id} className={isSelected ? "is-selected" : undefined}>
                              <td>
                                <div className="job-primary">
                                  <div className="job-title-row">
                                    <input
                                      type="checkbox"
                                      data-job-result-select={item.run_job_id}
                                      aria-label={"Select " + (item.title || "job")}
                                      checked={isSelected}
                                      onChange={() =>
                                        setSelectedJobIds((prev) =>
                                          prev.includes(item.run_job_id)
                                            ? prev.filter((x) => x !== item.run_job_id)
                                            : [...prev, item.run_job_id]
                                        )
                                      }
                                    />
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
                                  <div className="interest-rating" aria-label={"Application Interest for " + (item.title || "Job")}>
                                    {[1, 2, 3, 4, 5].map((val) => (
                                      <button
                                        key={val}
                                        type="button"
                                        className="star-btn"
                                        aria-label={"Rate " + val + " of 5"}
                                        aria-pressed={val <= currentRating}
                                        onClick={() => handleRateJob(item, val)}
                                      >
                                        ★
                                      </button>
                                    ))}
                                    {currentRating > 0 && (
                                      <button
                                        type="button"
                                        className="small-action clear-rating"
                                        onClick={() => handleRateJob(item, 0)}
                                        aria-label="Clear interest rating"
                                      >
                                        Clear
                                      </button>
                                    )}

                                    <button
                                      type="button"
                                      className="small-action bookmark-btn"
                                      aria-label={isBookmarked ? "Remove Bookmark" : "Bookmark Job"}
                                      aria-pressed={isBookmarked}
                                      onClick={() => handleToggleBookmark(item)}
                                      style={{ marginLeft: 6 }}
                                    >
                                      <svg viewBox="0 0 24 24" aria-hidden="true">
                                        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                                      </svg>
                                      <span>{isBookmarked ? "Bookmarked" : "Bookmark"}</span>
                                    </button>
                                  </div>

                                  {/* CV Actions */}
                                  {hasCv && (
                                    <div className="job-action-row">
                                      <button
                                        type="button"
                                        className="small-action"
                                        onClick={() => handleViewCv(item)}
                                      >
                                        View CV
                                      </button>
                                      <button
                                        type="button"
                                        className="small-action"
                                        onClick={() => handleDownloadCv(item)}
                                      >
                                        Download CV
                                      </button>
                                      {cvCanRegenerate && (
                                        <button
                                          type="button"
                                          className="small-action"
                                          onClick={() => handleOpenRegenerate(item)}
                                        >
                                          Regenerate CV
                                        </button>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </td>

                              <td>{renderJobAttributes(item)}</td>
                              <td>{renderSkillChips(item)}</td>
                              <td>
                                <div className="pipeline-outcome">
                                  <StatusBadge status={badgeStatus} label={label} />
                                  {reason && <span className="outcome-reason">{reason}</span>}
                                  {isStretch && <span className="cv-review-tag">Stretch review</span>}
                                </div>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Table Pagination per Prototype */}
                <div className="run-pagination">
                  <span>
                    Showing <strong>{pageStart}</strong> to <strong>{pageEnd}</strong> of <strong>{jobsTotal}</strong> results
                  </span>
                  <div className="run-pagination-controls">
                    <label className="run-page-size" htmlFor="jobResultsPageSize">
                      Rows:
                      <select
                        id="jobResultsPageSize"
                        className="field"
                        value={jobsPageSize}
                        onChange={(e) => {
                          const newSize = Number(e.target.value);
                          setJobsPageSize(newSize);
                          setJobsPage(1);
                          loadJobs(1, newSize);
                        }}
                      >
                        {PAGE_SIZE_OPTIONS.map((size) => (
                          <option key={size} value={size}>
                            {size}
                          </option>
                        ))}
                      </select>
                    </label>

                    <div className="run-page-numbers" aria-label="Job results pagination">
                      <Button
                        size="compact"
                        variant="secondary"
                        disabled={jobsPage <= 1}
                        onClick={() => {
                          const p = jobsPage - 1;
                          setJobsPage(p);
                          loadJobs(p);
                        }}
                        aria-label="Previous page"
                      >
                        ‹
                      </Button>
                      {Array.from({ length: totalPages }, (_, idx) => idx + 1)
                        .filter((p) => p === 1 || p === totalPages || Math.abs(p - jobsPage) <= 2)
                        .map((p, idx, arr) => {
                          const prev = arr[idx - 1];
                          const showGap = prev && p - prev > 1;
                          return (
                            <React.Fragment key={p}>
                              {showGap && <span className="run-page-gap" aria-hidden="true">…</span>}
                              <Button
                                size="compact"
                                variant={p === jobsPage ? "primary" : "secondary"}
                                onClick={() => {
                                  setJobsPage(p);
                                  loadJobs(p);
                                }}
                                aria-label={"Page " + p}
                                aria-current={p === jobsPage ? "page" : undefined}
                              >
                                {p}
                              </Button>
                            </React.Fragment>
                          );
                        })}
                      <Button
                        size="compact"
                        variant="secondary"
                        disabled={jobsPage >= totalPages}
                        onClick={() => {
                          const p = jobsPage + 1;
                          setJobsPage(p);
                          loadJobs(p);
                        }}
                        aria-label="Next page"
                      >
                        ›
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </details>
      {/* Section 4: Console Log */}
      <details className="section-card collapsible-section drawer-section">
        <summary>
          <span className="section-heading">
            <strong>Console Log</strong>
            <span>
              Canonical run events for troubleshooting. Clear View hides loaded events locally without deleting backend evidence.
            </span>
          </span>
        </summary>
        <div className="section-content drawer-section-content">
          <EventConsole
            events={events}
            isLive={!isTerminal}
            onRefresh={pollEvents}
            runId={run.run_id}
            onDownloadDebugBundle={run.debug_bundle?.status === "available" ? handleDownloadDebugBundle : undefined}
          />
        </div>
      </details>

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
        title={regenerateJob ? "Regenerate CV for " + regenerateJob.title : "Regenerate CV"}
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
            ? "Are you sure you want to cancel run " + run.run_id + "? Current stage processing will be interrupted."
            : confirmAction === "archive"
            ? "Archiving run " + run.run_id + " will move it to historical archives."
            : "Restore run " + run.run_id + " to active workspace."
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
