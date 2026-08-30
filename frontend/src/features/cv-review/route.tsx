import React, { useState, useEffect, useCallback } from "react";
import { CvVersionResource } from "./types";
import { fetchCvVersions, regenerateCvVersion } from "./api";
import { CvVersionHistory } from "./components/CvVersionHistory";
import { CvPreviewPane } from "./components/CvPreviewPane";
import { CvEvaluationCard } from "./components/CvEvaluationCard";
import { CvRegenerateDialog } from "./components/CvRegenerateDialog";
import { fetchRuns, fetchRunJobs } from "../runs/api";
import { PipelineRunResource, RunJobItem } from "../runs/types";
import { Button, LoadingState, EmptyState, LiveStatus } from "../../components";
import { notificationStore } from "../../lib/notifications";

export const CvReviewPage: React.FC = () => {
  const [runs, setRuns] = useState<PipelineRunResource[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [jobs, setJobs] = useState<RunJobItem[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [versions, setVersions] = useState<CvVersionResource[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

  const [loadingRuns, setLoadingRuns] = useState(true);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [liveMessage, setLiveMessage] = useState("");

  const [isRegenerateOpen, setIsRegenerateOpen] = useState(false);

  // Parse initial query params from hash: #/cv-review?run_id=...&job_id=...&version_id=...
  useEffect(() => {
    const parseHash = () => {
      const hash = window.location.hash || "";
      const parts = hash.split("?");
      if (parts.length > 1) {
        const params = new URLSearchParams(parts[1]);
        const rId = params.get("run_id");
        const jId = params.get("job_id");
        const vId = params.get("version_id");
        if (rId) setSelectedRunId(rId);
        if (jId) setSelectedJobId(jId);
        if (vId) setSelectedVersionId(vId);
      }
    };
    parseHash();
  }, []);

  // Load available runs
  useEffect(() => {
    async function loadRuns() {
      setLoadingRuns(true);
      try {
        const res = await fetchRuns({ view: "active", page: 1, page_size: 50 });
        const items = res.data || [];
        setRuns(items);
        if (items.length > 0 && !selectedRunId) {
          setSelectedRunId(items[0].run_id);
        }
      } catch (err: any) {
        notificationStore.notify({
          dedupe: `cv:load_runs_err:${Date.now()}`,
          type: "error",
          title: "Failed to load runs",
          message: err.message || "Could not retrieve runs list.",
        });
      } finally {
        setLoadingRuns(false);
      }
    }
    loadRuns();
  }, []);

  // Load jobs for selected run
  useEffect(() => {
    if (!selectedRunId) {
      setJobs([]);
      setSelectedJobId("");
      return;
    }
    async function loadJobs() {
      setLoadingJobs(true);
      try {
        const res = await fetchRunJobs(selectedRunId, { page: 1, page_size: 100 });
        const items = res.data || [];
        setJobs(items);
        if (items.length > 0) {
          const hasCurrent = items.some((j) => j.run_job_id === selectedJobId);
          if (!hasCurrent) {
            const cvJob = items.find((j) => (j.cv_versions_count || 0) > 0) || items[0];
            setSelectedJobId(cvJob.run_job_id);
          }
        } else {
          setSelectedJobId("");
        }
      } catch (err: any) {
        notificationStore.notify({
          dedupe: `cv:load_jobs_err:${Date.now()}`,
          type: "error",
          title: "Failed to load jobs",
          message: err.message || "Could not retrieve jobs for run.",
        });
      } finally {
        setLoadingJobs(false);
      }
    }
    loadJobs();
  }, [selectedRunId]);

  // Load CV versions for selected run job
  const loadVersions = useCallback(async (runId: string, jobId: string, targetVersionId?: string | null) => {
    if (!runId || !jobId) {
      setVersions([]);
      setSelectedVersionId(null);
      return;
    }
    setLoadingVersions(true);
    try {
      const data = await fetchCvVersions(runId, jobId);
      setVersions(data);
      if (data.length > 0) {
        if (targetVersionId && data.some((v) => v.version_id === targetVersionId)) {
          setSelectedVersionId(targetVersionId);
        } else if (!selectedVersionId || !data.some((v) => v.version_id === selectedVersionId)) {
          setSelectedVersionId(data[0].version_id);
        }
      } else {
        setSelectedVersionId(null);
      }
    } catch (err: any) {
      notificationStore.notify({
        dedupe: `cv:load_versions_err:${Date.now()}`,
        type: "error",
        title: "Failed to load CV versions",
        message: err.message || "Could not load CV history.",
      });
    } finally {
      setLoadingVersions(false);
    }
  }, [selectedVersionId]);

  useEffect(() => {
    if (selectedRunId && selectedJobId) {
      loadVersions(selectedRunId, selectedJobId, selectedVersionId);
    } else {
      setVersions([]);
      setSelectedVersionId(null);
    }
  }, [selectedRunId, selectedJobId]);

  const handleSelectVersion = (versionId: string) => {
    setSelectedVersionId(versionId);
    setLiveMessage(`Selected CV version ${versionId.slice(0, 8)}`);
    const params = new URLSearchParams();
    if (selectedRunId) params.set("run_id", selectedRunId);
    if (selectedJobId) params.set("job_id", selectedJobId);
    params.set("version_id", versionId);
    window.location.hash = `#/cv-review?${params.toString()}`;
  };

  const handleConfirmRegenerate = async (parentVersionId: string | null) => {
    if (!selectedRunId || !selectedJobId) return;
    const res = await regenerateCvVersion(selectedRunId, selectedJobId, parentVersionId);
    notificationStore.notify({
      dedupe: `cv:regen:${res.action_id}`,
      type: "success",
      title: "Regeneration Queued",
      message: "New CV version generation has been queued.",
    });
    await loadVersions(selectedRunId, selectedJobId);
  };

  const selectedVersion = versions.find((v) => v.version_id === selectedVersionId) || (versions.length > 0 ? versions[0] : null);

  return (
    <div className="content-container cv-review-feature" style={{ maxWidth: 1200, margin: "0 auto" }}>
      <LiveStatus message={liveMessage} />

      {/* Page Header */}
      <div className="page-head" style={{ marginBottom: 20 }}>
        <p
          className="eyebrow"
          style={{
            color: "var(--accent)",
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            margin: "0 0 6px",
          }}
        >
          Grounded CV Generation & Review
        </p>
        <h2
          style={{
            margin: 0,
            fontFamily: "var(--display-font)",
            fontSize: 26,
            letterSpacing: "-0.03em",
          }}
        >
          CV Review & Artifacts
        </h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", fontSize: 13 }}>
          Inspect immutable CV version history, safe Markdown preview, download artifacts, and review evaluations.
        </p>
      </div>

      {/* Selection Filters Bar */}
      <div
        className="table-card"
        style={{
          padding: "16px 20px",
          marginBottom: 20,
          display: "flex",
          flexWrap: "wrap",
          alignItems: "flex-end",
          gap: 16,
          background: "var(--surface)",
        }}
      >
        {/* Run Selector */}
        <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 220 }}>
          <label htmlFor="cv-run-select" style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)" }}>
            Select Run
          </label>
          <select
            id="cv-run-select"
            value={selectedRunId}
            onChange={(e) => {
              setSelectedRunId(e.target.value);
              setSelectedJobId("");
              setSelectedVersionId(null);
            }}
            disabled={loadingRuns || runs.length === 0}
            className="field-input"
            style={{ fontSize: 13, padding: "6px 10px" }}
          >
            {runs.length === 0 ? (
              <option value="">No runs available</option>
            ) : (
              runs.map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  {r.run_name || r.run_id} ({r.counts?.cvs_generated || 0} CVs)
                </option>
              ))
            )}
          </select>
        </div>

        {/* Job Selector */}
        <div style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1, minWidth: 260 }}>
          <label htmlFor="cv-job-select" style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)" }}>
            Select Job
          </label>
          <select
            id="cv-job-select"
            value={selectedJobId}
            onChange={(e) => {
              setSelectedJobId(e.target.value);
              setSelectedVersionId(null);
            }}
            disabled={loadingJobs || jobs.length === 0}
            className="field-input"
            style={{ fontSize: 13, padding: "6px 10px" }}
          >
            {jobs.length === 0 ? (
              <option value="">{loadingJobs ? "Loading jobs..." : "No jobs for this run"}</option>
            ) : (
              jobs.map((j) => (
                <option key={j.run_job_id} value={j.run_job_id}>
                  {j.title || j.job_id} · {j.company || "Unknown"} {(j.cv_versions_count || 0) > 0 ? `(${j.cv_versions_count} versions)` : ""}
                </option>
              ))
            )}
          </select>
        </div>

        {/* Refresh button */}
        <Button
          variant="secondary"
          size="compact"
          onClick={() => {
            if (selectedRunId && selectedJobId) {
              loadVersions(selectedRunId, selectedJobId, selectedVersionId);
            }
          }}
          disabled={loadingVersions || !selectedJobId}
        >
          Refresh History
        </Button>
      </div>

      {/* Main Workspace Layout */}
      {loadingRuns ? (
        <LoadingState message="Loading runs..." />
      ) : !selectedJobId ? (
        <EmptyState
          title="No Job Selected"
          description="Select a pipeline run and a job to inspect generated CV versions and evaluations."
        />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(260px, 320px) minmax(0, 1fr)", gap: 20, alignItems: "start" }}>
          {/* Left Column: Version History */}
          <div style={{ display: "grid", gap: 16 }}>
            <div className="table-card" style={{ padding: "16px 18px", background: "var(--surface)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: 14 }}>Version History</h3>
                <span style={{ fontSize: 12, color: "var(--muted)" }}>
                  {versions.length} version{versions.length === 1 ? "" : "s"}
                </span>
              </div>
              <CvVersionHistory
                versions={versions}
                selectedVersionId={selectedVersionId}
                onSelectVersion={handleSelectVersion}
                loading={loadingVersions}
              />
            </div>

            {/* Evaluation & Review State */}
            <CvEvaluationCard version={selectedVersion} />
          </div>

          {/* Right Column: Selected Version Preview Pane */}
          <div>
            <CvPreviewPane
              version={selectedVersion}
              onRegenerateRequest={() => setIsRegenerateOpen(true)}
            />
          </div>
        </div>
      )}

      {/* Regenerate Confirmation Dialog */}
      <CvRegenerateDialog
        open={isRegenerateOpen}
        onClose={() => setIsRegenerateOpen(false)}
        onConfirm={handleConfirmRegenerate}
        currentVersion={selectedVersion}
        runId={selectedRunId}
        runJobId={selectedJobId}
      />
    </div>
  );
};

export const route = {
  id: "cv-review",
  path: "#/cv-review",
  title: "CV Review",
  group: "workspace" as const,
  order: 55,
  component: CvReviewPage,
};

export default route;
