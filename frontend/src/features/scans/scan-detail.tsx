import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Button,
  StatusBadge,
  StatusVariant,
  LoadingState,
  EmptyState,
  Tabs,
  DataTable,
  TableColumn,
} from "../../components";
import {
  fetchScan,
  cancelScan,
  runScanAgain,
  archiveScans,
  unarchiveScans,
  fetchScanEvents,
  fetchScanJobs,
  fetchScanOutputJson,
} from "./api";
import {
  ScanResource,
  ScanExecutionStatus,
  ProcessEventRecord,
  ScanJobItem,
} from "./types";
import { apiClient } from "../../lib/api-client";

export interface ScanDetailProps {
  scanId: string;
  onBack: () => void;
}

export function shouldLoadScanOutput(
  status: ScanExecutionStatus | undefined,
  loaded: boolean,
  loading: boolean,
): boolean {
  return status === "succeeded" && !loaded && !loading;
}

const statusMap: Record<string, { variant: StatusVariant; label: string }> = {
  queued: { variant: "neutral", label: "Queued" },
  running: { variant: "info", label: "Running" },
  cancelling: { variant: "warn", label: "Cancelling" },
  succeeded: { variant: "success", label: "Succeeded" },
  failed: { variant: "danger", label: "Failed" },
  cancelled: { variant: "neutral", label: "Cancelled" },
};

export const ScanDetailPage: React.FC<ScanDetailProps> = ({ scanId, onBack }) => {
  const [scan, setScan] = useState<ScanResource | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Events / Console State
  const [events, setEvents] = useState<ProcessEventRecord[]>([]);
  const eventCursorRef = useRef<string | null>(null);

  // Output State
  const [outputTab, setOutputTab] = useState<"table" | "json">("table");
  const [jobs, setJobs] = useState<ScanJobItem[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [jobsPage, setJobsPage] = useState(1);
  const [jobsTotal, setJobsTotal] = useState(0);
  const [jobsLoadAttempted, setJobsLoadAttempted] = useState(false);
  const [jobsLoadError, setJobsLoadError] = useState<string | null>(null);
  const [jsonOutput, setJsonOutput] = useState<string | null>(null);
  const [jsonLoading, setJsonLoading] = useState(false);
  const [jsonLoadAttempted, setJsonLoadAttempted] = useState(false);
  const [jsonLoadError, setJsonLoadError] = useState<string | null>(null);

  const pollTimerRef = useRef<number | null>(null);

  const loadScanData = useCallback(async (isInitial = false) => {
    if (isInitial) setLoading(true);
    try {
      const [res, eventsRes] = await Promise.all([
        fetchScan(scanId),
        fetchScanEvents(scanId, eventCursorRef.current, 50),
      ]);
      setScan(res);
      setError(null);

      if (eventsRes.events && eventsRes.events.length > 0) {
        setEvents((prev) => {
          const ids = new Set(prev.map((e) => e.event_id));
          const fresh = eventsRes.events.filter((e) => !ids.has(e.event_id));
          return [...prev, ...fresh];
        });
        if (eventsRes.next_cursor) {
          eventCursorRef.current = eventsRes.next_cursor;
        }
      }
    } catch (err: any) {
      if (isInitial) setError(err.message || "Failed to load scan details");
    } finally {
      if (isInitial) setLoading(false);
    }
  }, [scanId]);

  const loadJobs = useCallback(async (page = 1) => {
    setJobsLoadAttempted(true);
    setJobsLoading(true);
    setJobsLoadError(null);
    try {
      const res = await fetchScanJobs(scanId, page, 20);
      setJobs(res.data || []);
      setJobsPage(res.page || page);
      setJobsTotal(res.total_items || res.total || 0);
    } catch (err: any) {
      setJobsLoadError(err.message || "Unable to load scan output.");
    } finally {
      setJobsLoading(false);
    }
  }, [scanId]);

  const loadJson = useCallback(async () => {
    setJsonLoadAttempted(true);
    setJsonLoading(true);
    setJsonLoadError(null);
    try {
      const data = await fetchScanOutputJson(scanId);
      setJsonOutput(data);
    } catch (err: any) {
      setJsonOutput(null);
      setJsonLoadError(err.message || "Unable to load JSON payload.");
    } finally {
      setJsonLoading(false);
    }
  }, [scanId]);

  // Initial load
  useEffect(() => {
    eventCursorRef.current = null;
    setEvents([]);
    setJobs([]);
    setJobsPage(1);
    setJobsTotal(0);
    setJobsLoadAttempted(false);
    setJobsLoadError(null);
    setJsonOutput(null);
    setJsonLoadAttempted(false);
    setJsonLoadError(null);
    loadScanData(true);
  }, [loadScanData]);

  // Polling for active execution states
  useEffect(() => {
    if (!scan) return;
    const isPending = ["queued", "running", "cancelling"].includes(scan.execution_status);
    if (!isPending) {
      return;
    }

    const poll = async () => {
      await loadScanData(false);
      pollTimerRef.current = window.setTimeout(poll, 3000);
    };

    pollTimerRef.current = window.setTimeout(poll, 3000);
    return () => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
      }
    };
  }, [scan?.execution_status, loadScanData]);

  // Load output when tab switches or scan finishes
  useEffect(() => {
    if (scan?.execution_status === "succeeded") {
      if (outputTab === "table" && !jobsLoadAttempted && !jobsLoading) {
        loadJobs(1);
      } else if (outputTab === "json" && !jsonLoadAttempted && !jsonLoading) {
        loadJson();
      }
    }
  }, [scan?.execution_status, outputTab, jobsLoadAttempted, jobsLoading, jsonLoadAttempted, jsonLoading, loadJobs, loadJson]);

  const handleCancel = async () => {
    if (!scan) return;
    setActionInProgress(true);
    setActionNotice("Cancelling scan...");
    try {
      const updated = await cancelScan(scan.scan_id, scan.row_revision);
      setScan(updated);
      setActionNotice("Cancellation requested.");
    } catch (err: any) {
      setActionNotice(`Cancel failed: ${err.message}`);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleRunAgain = async () => {
    if (!scan) return;
    setActionInProgress(true);
    setActionNotice("Starting new scan...");
    try {
      const created = await runScanAgain(scan.scan_id, undefined, scan.row_revision);
      setActionNotice(`Created new Scan ${created.scan_id}`);
       window.location.hash = `#/scans?scan_id=${encodeURIComponent(created.scan_id)}`;
    } catch (err: any) {
      setActionNotice(`Run Again failed: ${err.message}`);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleArchive = async () => {
    if (!scan) return;
    setActionInProgress(true);
    try {
      await archiveScans([{ scan_id: scan.scan_id, expected_revision: scan.row_revision }]);
      await loadScanData(false);
      setActionNotice("Scan archived.");
    } catch (err: any) {
      setActionNotice(`Archive failed: ${err.message}`);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleUnarchive = async () => {
    if (!scan) return;
    setActionInProgress(true);
    try {
      await unarchiveScans([{ scan_id: scan.scan_id, expected_revision: scan.row_revision }]);
      await loadScanData(false);
      setActionNotice("Scan unarchived.");
    } catch (err: any) {
      setActionNotice(`Unarchive failed: ${err.message}`);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleDownloadJson = async () => {
    if (!scan) return;
    try {
      await apiClient.download(
        `/scans/${encodeURIComponent(scan.scan_id)}/output?download=true`,
        `${scan.scan_id}.json`
      );
    } catch (err: any) {
      setActionNotice(`Download failed: ${err.message}`);
    }
  };

  const handleUseForRun = () => {
    if (!scan) return;
    window.location.hash = `#/runs?scan_ids=${encodeURIComponent(scan.scan_id)}`;
  };

  if (loading) {
    return <LoadingState message="Loading scan details..." />;
  }

  if (error || !scan) {
    return (
      <div className="content-container">
        <Button variant="secondary" onClick={onBack} style={{ marginBottom: 16 }}>
          ← Back to Scans
        </Button>
        <EmptyState
          title="Scan not found"
          description={error || "The requested scan could not be loaded."}
          actionLabel="Go Back"
          onAction={onBack}
        />
      </div>
    );
  }

  const badgeInfo = statusMap[scan.execution_status] || { variant: "neutral", label: scan.execution_status };

  return (
    <div className="content-container" data-page="scan-detail">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <Button variant="secondary" size="compact" onClick={onBack} style={{ marginBottom: 8 }}>
            ← Back to Scans
          </Button>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <h2 style={{ margin: 0, fontSize: 22, fontFamily: "var(--display-font)" }}>
              {scan.scan_name || scan.scan_id}
            </h2>
            <StatusBadge status={badgeInfo.variant} label={badgeInfo.label} />
            {scan.lifecycle === "archived" && <StatusBadge status="neutral" label="Archived" />}
          </div>
          <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>
            Scan ID: <code>{scan.scan_id}</code> · Created: {new Date(scan.created_at).toLocaleString()}
          </p>
        </div>

        {/* Action Buttons */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {scan.capabilities.run_again && (
            <Button
              variant="secondary"
              onClick={handleRunAgain}
              disabled={actionInProgress}
            >
              Run Again
            </Button>
          )}
          {scan.capabilities.download && (
            <Button
              variant="secondary"
              onClick={handleDownloadJson}
              disabled={actionInProgress}
            >
              Download JSON
            </Button>
          )}
          {scan.capabilities.use_for_run && (
            <Button variant="primary" onClick={handleUseForRun} disabled={actionInProgress}>
              Use in Run
            </Button>
          )}
          {scan.capabilities.cancel && (
            <Button
              variant="secondary"
              onClick={handleCancel}
              disabled={actionInProgress}
              style={{ color: "var(--danger)" }}
            >
              Cancel Scan
            </Button>
          )}
          {scan.capabilities.archive && (
            <Button
              variant="secondary"
              onClick={handleArchive}
              disabled={actionInProgress}
            >
              Archive
            </Button>
          )}
          {scan.capabilities.unarchive && (
            <Button
              variant="secondary"
              onClick={handleUnarchive}
              disabled={actionInProgress}
            >
              Unarchive
            </Button>
          )}
        </div>
      </div>

      {actionNotice && (
        <div className="notice info" role="status" style={{ marginBottom: 16 }}>
          {actionNotice}
        </div>
      )}

      {scan.failure_code && (
        <div className="notice error" role="alert" style={{ marginBottom: 16 }}>
          <strong>Execution Failure ({scan.failure_code}):</strong> {scan.failure_message}
        </div>
      )}

      {/* Overview & Input Details */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16, marginBottom: 24 }}>
        <div className="table-card" style={{ padding: 16 }}>
          <h3 style={{ margin: "0 0 12px", fontSize: 14, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)" }}>
            Scan Inputs
          </h3>
          <dl className="details-grid" style={{ margin: 0, fontSize: 13 }}>
            <div style={{ marginBottom: 8 }}>
              <dt style={{ color: "var(--muted)", fontWeight: 600 }}>Tracked Companies</dt>
              <dd style={{ margin: 0 }}>
                {(scan.company_snapshots || []).map((c) => c.company_name).join(", ") ||
                  `${scan.company_count} companies`}
              </dd>
            </div>
            <div style={{ marginBottom: 8 }}>
              <dt style={{ color: "var(--muted)", fontWeight: 600 }}>Job Titles</dt>
              <dd style={{ margin: 0 }}>{scan.input?.job_titles?.join(", ") || "Any"}</dd>
            </div>
            <div style={{ marginBottom: 8 }}>
              <dt style={{ color: "var(--muted)", fontWeight: 600 }}>Locations</dt>
              <dd style={{ margin: 0 }}>{scan.input?.locations?.join(", ") || "Any"}</dd>
            </div>
            <div style={{ marginBottom: 8 }}>
              <dt style={{ color: "var(--muted)", fontWeight: 600 }}>Publication Window</dt>
              <dd style={{ margin: 0 }}>{scan.input?.published_window?.replace(/_/g, " ") || "Any"}</dd>
            </div>
            <div>
              <dt style={{ color: "var(--muted)", fontWeight: 600 }}>Max Rows</dt>
              <dd style={{ margin: 0 }}>{scan.input?.total_rows ?? 50}</dd>
            </div>
          </dl>
        </div>

        <div className="table-card" style={{ padding: 16 }}>
          <h3 style={{ margin: "0 0 12px", fontSize: 14, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)" }}>
            Execution Timeline
          </h3>
          <dl className="details-grid" style={{ margin: 0, fontSize: 13 }}>
            <div style={{ marginBottom: 8 }}>
              <dt style={{ color: "var(--muted)", fontWeight: 600 }}>Created</dt>
              <dd style={{ margin: 0 }}>{new Date(scan.created_at).toLocaleString()}</dd>
            </div>
            <div style={{ marginBottom: 8 }}>
              <dt style={{ color: "var(--muted)", fontWeight: 600 }}>Started</dt>
              <dd style={{ margin: 0 }}>
                {scan.started_at ? new Date(scan.started_at).toLocaleString() : "Not started"}
              </dd>
            </div>
            <div style={{ marginBottom: 8 }}>
              <dt style={{ color: "var(--muted)", fontWeight: 600 }}>Finished</dt>
              <dd style={{ margin: 0 }}>
                {scan.finished_at ? new Date(scan.finished_at).toLocaleString() : "—"}
              </dd>
            </div>
            <div>
              <dt style={{ color: "var(--muted)", fontWeight: 600 }}>Output Records</dt>
              <dd style={{ margin: 0 }}>{scan.output_record_count ?? "Not available"}</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Output Section */}
      <div className="table-card" style={{ padding: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 16 }}>Scan Output</h3>
          {scan.execution_status === "succeeded" && (
            <Tabs
              items={[
                { id: "table", label: "Table View", count: scan.output_record_count ?? undefined },
                { id: "json", label: "JSON" },
              ]}
              activeId={outputTab}
              onChange={(id) => setOutputTab(id as "table" | "json")}
            />
          )}
        </div>

        {scan.execution_status !== "succeeded" ? (
          <div style={{ padding: "32px 16px", textAlign: "center", color: "var(--muted)", fontSize: 13 }}>
            {["queued", "running", "cancelling"].includes(scan.execution_status)
              ? "Scan output is not ready yet."
              : "No Scan output is available for this status."}
          </div>
        ) : outputTab === "table" ? (
          jobsLoading ? (
            <LoadingState message="Loading output jobs..." />
          ) : jobsLoadError ? (
            <div className="notice error" role="alert">
              Could not load scan output jobs: {jobsLoadError}
            </div>
          ) : (
            <DataTable
              columns={buildScanJobColumns()}
              data={jobs}
              keyField={(job) => job.id || job.title + (job.companyName || "")}
              page={jobsPage}
              pageSize={20}
              total={jobsTotal}
              onPageChange={(p) => loadJobs(p)}
              emptyMessage="No jobs were found in this scan output."
              className="jobs-table"
            />
          )
        ) : jsonLoading ? (
          <LoadingState message="Loading JSON payload..." />
        ) : jsonLoadError ? (
          <div className="notice error" role="alert">
            Could not load JSON payload: {jsonLoadError}
          </div>
        ) : (
          <pre
            style={{
              maxHeight: 400,
              overflowY: "auto",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              background: "var(--surface-2)",
              padding: 12,
              borderRadius: "var(--radius-md)",
              margin: 0,
            }}
          >
            {jsonOutput || "[]"}
          </pre>
        )}
      </div>

      {/* Console Events Section */}
      <div className="table-card" style={{ padding: 16, marginTop: 24 }}>
        <h3 style={{ margin: "0 0 4px", fontSize: 16 }}>Console &amp; Events</h3>
        <p style={{ margin: "0 0 12px", color: "var(--muted)", fontSize: 12 }}>
          Activity recorded while this scan collected job postings.
        </p>
        {events.length === 0 ? (
          <div style={{ color: "var(--muted)", fontSize: 13, padding: "12px 0" }}>
            No scan events recorded yet.
          </div>
        ) : (
          <div className="console-log" role="log" aria-label="Scan console events" tabIndex={0}>
            {events.map((evt) => {
              const message = getScanEventMessage(evt);
              const payload = evt.payload ?? parseEventJson(evt.payload_json);
              const level = evt.event_level ?? evt.level ?? "info";
              const stage = evt.stage_name ?? evt.operation ?? evt.event_type ?? evt.state ?? "Event";
              return (
                <div key={evt.event_id} className="console-line">
                  <span className="console-time">{new Date(evt.recorded_at).toLocaleTimeString()}</span>
                  <span className="console-level" data-level={level}>{level}</span>
                  <span>{stage}</span>
                  <span className="console-message">
                    {message}
                    {Object.keys(payload).length > 0 && (
                      <details>
                        <summary>Event data</summary>
                        <pre style={{ margin: "4px 0 0", whiteSpace: "pre-wrap" }}>
                          {JSON.stringify(payload, null, 2)}
                        </pre>
                      </details>
                    )}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

function getStringValue(job: ScanJobItem, ...keys: string[]): string {
  for (const key of keys) {
    const value = job[key];
    if (typeof value === "string" && value.trim()) return value.trim();
    if (typeof value === "number") return String(value);
  }
  return "";
}

export function getScanJobUrl(job: ScanJobItem): string {
  const url = getStringValue(job, "jobUrl", "applyUrl", "job_url", "apply_url", "url");
  return /^https?:\/\//i.test(url) ? url : "";
}

export function getScanJobCompany(job: ScanJobItem): string {
  return getStringValue(job, "companyName", "company_name", "company") || "Unknown company";
}

export function getScanJobPostingDate(job: ScanJobItem): string {
  return getStringValue(job, "publishedAt", "published_at", "posted_at", "posted_time") || "—";
}

export function buildScanJobColumns(): TableColumn<ScanJobItem>[] {
  return [
    {
      key: "title",
      header: "Job",
      render: (job) => {
        const url = getScanJobUrl(job);
        const title = getStringValue(job, "title") || "Untitled job";
        return (
          <div className="job-primary">
            <div className="job-title-row">
              {url ? (
                <a className="job-title-link" href={url} target="_blank" rel="noopener noreferrer">
                  {title} ↗
                </a>
              ) : (
                <strong style={{ fontSize: 14 }}>{title}</strong>
              )}
            </div>
            <div className="job-action-row">
              {url ? <span style={{ color: "var(--muted)", fontSize: 11 }}>Open posting</span> : <span style={{ color: "var(--muted)", fontSize: 11 }}>No posting link</span>}
            </div>
          </div>
        );
      },
    },
    { key: "companyName", header: "Company", render: getScanJobCompany },
    { key: "publishedAt", header: "Posting date", render: getScanJobPostingDate },
    {
      key: "metadata",
      header: "Job metadata",
      render: (job) => {
        const fields = [
          ["Location", getStringValue(job, "location")],
          ["Contract", getStringValue(job, "contractType", "contract_type")],
          ["Experience", getStringValue(job, "experienceLevel", "experience_level")],
          ["Work type", getStringValue(job, "work_type")],
          ["Salary", getStringValue(job, "salary")],
          ["Sector", getStringValue(job, "sector")],
        ].filter(([, value]) => value);
        return fields.length ? (
          <div className="job-attributes">
            {fields.map(([label, value]) => (
              <div key={label} className="job-attribute">
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        ) : <span style={{ color: "var(--muted)" }}>—</span>;
      },
    },
  ];
}

export function getScanEventMessage(event: ProcessEventRecord): string {
  const payload = event.payload ?? parseEventJson(event.payload_json);
  const payloadMessage = payload?.message;
  if (typeof payloadMessage === "string" && payloadMessage.trim()) return payloadMessage;
  if (event.message?.trim()) return event.message.trim();
  const label = event.event_type || event.operation || event.state || "event";
  return label.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function parseEventJson(value?: string | null): Record<string, unknown> {
  if (!value) return {};
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}
