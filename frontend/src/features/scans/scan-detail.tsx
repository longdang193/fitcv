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
  const [jobsLoaded, setJobsLoaded] = useState(false);
  const [jobsPage, setJobsPage] = useState(1);
  const [jobsTotal, setJobsTotal] = useState(0);
  const [jsonOutput, setJsonOutput] = useState<string | null>(null);
  const [jsonLoading, setJsonLoading] = useState(false);
  const [jsonLoaded, setJsonLoaded] = useState(false);

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
    setJobsLoading(true);
    try {
      const res = await fetchScanJobs(scanId, page, 20);
      setJobs(res.data || []);
      setJobsPage(res.page || page);
      setJobsTotal(res.total_items || res.total || 0);
    } catch {
      setJobs([]);
    } finally {
      setJobsLoaded(true);
      setJobsLoading(false);
    }
  }, [scanId]);

  const loadJson = useCallback(async () => {
    setJsonLoading(true);
    try {
       const data = await fetchScanOutputJson(scanId);
       setJsonOutput(data);
    } catch {
      setJsonOutput(null);
    } finally {
      setJsonLoaded(true);
      setJsonLoading(false);
    }
  }, [scanId]);

  // Initial load
  useEffect(() => {
    eventCursorRef.current = null;
    setEvents([]);
    setJobs([]);
    setJobsLoaded(false);
    setJobsPage(1);
    setJobsTotal(0);
    setJsonOutput(null);
    setJsonLoaded(false);
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
      if (outputTab === "table" && shouldLoadScanOutput(scan.execution_status, jobsLoaded, jobsLoading)) {
        loadJobs(1);
      } else if (outputTab === "json" && shouldLoadScanOutput(scan.execution_status, jsonLoaded, jsonLoading)) {
        loadJson();
      }
    }
  }, [scan?.execution_status, outputTab, jobsLoaded, jobsLoading, jsonLoaded, jsonLoading, loadJobs, loadJson]);

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

  const jobColumns: TableColumn<ScanJobItem>[] = [
    {
      key: "title",
      header: "Title",
      render: (job) => (
        <div>
          <strong style={{ fontSize: 13 }}>{job.title}</strong>
          {job.jobUrl && (
              <a
              href={job.jobUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{ display: "block", fontSize: 11, color: "var(--accent)", textDecoration: "none" }}
            >
              View Posting ↗
            </a>
          )}
        </div>
      ),
    },
    { key: "companyName", header: "Company", render: (job) => job.companyName || "—" },
    { key: "location", header: "Location", render: (job) => job.location || "—" },
    { key: "publishedAt", header: "Posted", render: (job) => job.publishedAt || "—" },
  ];

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
              <dd style={{ margin: 0 }}>{scan.output_record_count ?? "None"}</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Console Events Section */}
      <div className="table-card" style={{ padding: 16, marginBottom: 24 }}>
        <h3 style={{ margin: "0 0 12px", fontSize: 14, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)" }}>
          Console & Events
        </h3>
        {events.length === 0 ? (
          <div style={{ color: "var(--muted)", fontSize: 13, padding: "12px 0" }}>
            No process events recorded.
          </div>
        ) : (
          <div
            style={{
              maxHeight: 220,
              overflowY: "auto",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              background: "var(--surface-2)",
              padding: 12,
              borderRadius: "var(--radius-md)",
              display: "flex",
              flexDirection: "column",
              gap: 4,
            }}
          >
            {events.map((evt) => (
              <div key={evt.event_id} style={{ display: "flex", gap: 8 }}>
                <span style={{ color: "var(--muted)" }}>
                  {new Date(evt.recorded_at).toLocaleTimeString()}
                </span>
                <span style={{ color: evt.level === "error" ? "var(--danger)" : "var(--accent)" }}>
                  [{evt.operation}:{evt.state}]
                </span>
                <span>{evt.message}{evt.payload_json ? ` · ${evt.payload_json}` : ""}</span>
              </div>
            ))}
          </div>
        )}
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
          ) : (
            <DataTable
              columns={jobColumns}
              data={jobs}
              keyField={(job) => job.id || job.title + (job.companyName || "")}
              page={jobsPage}
              pageSize={20}
              total={jobsTotal}
              onPageChange={(p) => loadJobs(p)}
              emptyMessage="No job records in output."
            />
          )
        ) : jsonLoading ? (
          <LoadingState message="Loading JSON payload..." />
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
    </div>
  );
};
