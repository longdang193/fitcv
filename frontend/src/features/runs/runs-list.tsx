import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  Button,
  Tabs,
  DataTable,
  TableColumn,
  StatusBadge,
  StatusVariant,
  LoadingState,
  Dialog,
} from "../../components";
import { formatIdentifier, formatTimestamp } from "../../lib/format";
import {
  fetchRuns,
  cancelRun,
  archiveRun,
  unarchiveRun,
  previewDeleteArchivedRuns,
  deleteArchivedRuns,
  generateIdempotencyKey,
} from "./api";
import {
  PipelineRunResource,
  RunLifecycle,
  DeleteArchivedRunsPreview,
} from "./types";
import { NewRunDialog } from "./new-run-dialog";

export interface RunsListPageProps {
  onSelectRun: (runId: string) => void;
  view: RunLifecycle;
  onViewChange: (view: RunLifecycle) => void;
  page: number;
  onPageChange: (newPage: number) => void;
  initialScanIds?: string[];
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

export function buildRunsQueryKey(
  view: RunLifecycle,
  search: string,
  page: number,
  pageSize: number
): string {
  return `${view}::${search.trim()}::${page}::${pageSize}`;
}

export interface RunsPollingCoordinatorOptions {
  getQueryKey: () => string;
  hasActiveRuns: () => boolean;
  isDocumentVisible?: () => boolean;
  fetchRuns: (params: {
    queryKey: string;
    showLoading: boolean;
  }) => Promise<boolean>;
  onPollSkipped?: (reason: "hidden" | "in_flight" | "terminal" | "destroyed") => void;
  cadenceMs?: number;
}

// ponytail: fixed 1s visible cadence with single in-flight deduplication; add adaptive backoff or websocket push if active run volume spikes.
export class RunsPollingCoordinator {
  private timerId: ReturnType<typeof setInterval> | null = null;
  private inFlight = false;
  private inFlightQueryKey: string | null = null;
  private activeRequestId = 0;
  private destroyed = false;
  private visibilityListener: (() => void) | null = null;

  constructor(private readonly options: RunsPollingCoordinatorOptions) {}

  public get currentRequestId(): number {
    return this.activeRequestId;
  }

  public get isInFlight(): boolean {
    return this.inFlight;
  }

  public get inFlightKey(): string | null {
    return this.inFlightQueryKey;
  }

  public get isPolling(): boolean {
    return this.timerId !== null;
  }

  public isDocumentVisible(): boolean {
    if (this.options.isDocumentVisible) {
      return this.options.isDocumentVisible();
    }
    if (typeof document === "undefined") return true;
    return document.visibilityState === "visible";
  }

  public start(): void {
    if (this.destroyed) return;
    this.attachVisibilityListener();
    if (this.options.hasActiveRuns() && this.isDocumentVisible()) {
      this.startTimer();
    }
  }

  public sync(): void {
    if (this.destroyed) return;
    if (!this.options.hasActiveRuns()) {
      this.stopTimer();
      return;
    }
    if (this.isDocumentVisible()) {
      if (this.timerId === null) {
        this.startTimer();
      }
    } else {
      this.stopTimer();
    }
  }

  public async load(options: { showLoading?: boolean; isPolling?: boolean } = {}): Promise<boolean> {
    const { showLoading = true, isPolling = false } = options;

    if (this.destroyed) {
      this.options.onPollSkipped?.("destroyed");
      return false;
    }

    if (isPolling) {
      if (!this.options.hasActiveRuns()) {
        this.stopTimer();
        this.options.onPollSkipped?.("terminal");
        return false;
      }
      if (!this.isDocumentVisible()) {
        this.stopTimer();
        this.options.onPollSkipped?.("hidden");
        return false;
      }
      if (this.inFlight) {
        this.options.onPollSkipped?.("in_flight");
        return false;
      }
    }

    const queryKey = this.options.getQueryKey();
    const requestId = ++this.activeRequestId;
    this.inFlight = true;
    this.inFlightQueryKey = queryKey;

    try {
      const ok = await this.options.fetchRuns({ queryKey, showLoading });
      if (this.destroyed || requestId !== this.activeRequestId || queryKey !== this.options.getQueryKey()) {
        return false;
      }
      if (!this.options.hasActiveRuns()) {
        this.stopTimer();
      }
      return ok;
    } finally {
      if (requestId === this.activeRequestId) {
        this.inFlight = false;
        this.inFlightQueryKey = null;
      }
    }
  }

  public triggerTick(): Promise<boolean> {
    return this.load({ showLoading: false, isPolling: true });
  }

  private startTimer(): void {
    if (this.timerId !== null || this.destroyed) return;
    const cadence = this.options.cadenceMs ?? 1000;
    this.timerId = setInterval(() => {
      void this.triggerTick();
    }, cadence);
  }

  private stopTimer(): void {
    if (this.timerId !== null) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
  }

  private attachVisibilityListener(): void {
    if (this.visibilityListener || typeof document === "undefined") return;
    this.visibilityListener = () => {
      if (this.destroyed) return;
      if (this.isDocumentVisible()) {
        if (this.options.hasActiveRuns()) {
          void this.triggerTick();
          this.startTimer();
        }
      } else {
        this.stopTimer();
      }
    };
    document.addEventListener("visibilitychange", this.visibilityListener);
  }

  public destroy(): void {
    this.destroyed = true;
    this.stopTimer();
    if (this.visibilityListener && typeof document !== "undefined") {
      document.removeEventListener("visibilitychange", this.visibilityListener);
      this.visibilityListener = null;
    }
  }
}

export function isRunTerminal(status: string): boolean {
  return ["succeeded", "failed", "cancelled"].includes(status);
}

export function isDistinctStatusDetail(detail: string | null | undefined, label: string): boolean {
  const normalizedDetail = detail?.trim().toLocaleLowerCase();
  return Boolean(normalizedDetail && normalizedDetail !== label.trim().toLocaleLowerCase());
}

export const RunsListPage: React.FC<RunsListPageProps> = ({
  onSelectRun,
  view,
  onViewChange,
  page,
  onPageChange,
  initialScanIds = [],
}) => {
  const [runs, setRuns] = useState<PipelineRunResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [totalItems, setTotalItems] = useState(0);
  const [pageSize] = useState(20);
  const [activeCount, setActiveCount] = useState(0);
  const [archivedCount, setArchivedCount] = useState(0);

  // Multi-selection for archived deletion
  const [selectedRunIds, setSelectedRunIds] = useState<Set<string>>(new Set());

  // Dialogs
  const [isNewRunOpen, setIsNewRunOpen] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Confirmation dialogs
  const [confirmAction, setConfirmAction] = useState<{
    type: "cancel" | "archive" | "unarchive";
    run: PipelineRunResource;
  } | null>(null);

  // Delete preview dialog
  const [deletePreview, setDeletePreview] = useState<DeleteArchivedRunsPreview | null>(null);
  const [isDeletePreviewOpen, setIsDeletePreviewOpen] = useState(false);

  const queryIdentity = buildRunsQueryKey(view, activeSearch, page, pageSize);
  const activeQueryRef = useRef(queryIdentity);
  activeQueryRef.current = queryIdentity;

  const runsRef = useRef<PipelineRunResource[]>(runs);
  runsRef.current = runs;

  const viewRef = useRef(view);
  viewRef.current = view;

  const searchRef = useRef(activeSearch);
  searchRef.current = activeSearch;

  const pageRef = useRef(page);
  pageRef.current = page;

  const isMountedRef = useRef(true);
  const coordinatorRef = useRef<RunsPollingCoordinator | null>(null);

  if (!coordinatorRef.current) {
    coordinatorRef.current = new RunsPollingCoordinator({
      getQueryKey: () => activeQueryRef.current,
      hasActiveRuns: () => runsRef.current.some((run) => !isRunTerminal(run.backend_status)),
      fetchRuns: async ({ showLoading, queryKey }) => {
        if (showLoading) setLoading(true);
        setError(null);
        try {
          const res = await fetchRuns({
            view: viewRef.current,
            search: searchRef.current,
            page: pageRef.current,
            page_size: pageSize,
          });
          if (!isMountedRef.current || queryKey !== activeQueryRef.current) {
            return false;
          }
          setRuns(res.data || []);
          setTotalItems(res.total_items || 0);
          if (res.meta) {
            if (typeof res.meta.active_count === "number") setActiveCount(res.meta.active_count);
            if (typeof res.meta.archived_count === "number") setArchivedCount(res.meta.archived_count);
          }
          return true;
        } catch (err: any) {
          if (!isMountedRef.current || queryKey !== activeQueryRef.current) {
            return false;
          }
          setError(err.message || "Failed to load runs.");
          return false;
        } finally {
          if (showLoading && isMountedRef.current) {
            setLoading(false);
          }
        }
      },
    });
  }

  const loadRuns = useCallback(async (showLoading = true): Promise<boolean> => {
    if (!coordinatorRef.current) return false;
    return coordinatorRef.current.load({ showLoading, isPolling: false });
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    coordinatorRef.current?.start();
    return () => {
      isMountedRef.current = false;
      coordinatorRef.current?.destroy();
      coordinatorRef.current = null;
    };
  }, []);

  useEffect(() => {
    setSelectedRunIds(new Set());
    void coordinatorRef.current?.load({ showLoading: true, isPolling: false });
  }, [view, activeSearch, page]);

  useEffect(() => {
    coordinatorRef.current?.sync();
  }, [runs]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const nextSearch = search.trim();
    if (nextSearch === activeSearch && page === 1) {
      void loadRuns(true);
    } else {
      setActiveSearch(nextSearch);
      onPageChange(1);
    }
  };

  const handleToggleSelect = (runId: string) => {
    setSelectedRunIds((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) {
        next.delete(runId);
      } else {
        next.add(runId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedRunIds.size === runs.length && runs.length > 0) {
      setSelectedRunIds(new Set());
    } else {
      setSelectedRunIds(new Set(runs.map((r) => r.run_id)));
    }
  };

  const handleExecuteConfirmAction = async () => {
    if (!confirmAction) return;
    setActionInProgress(true);
    setActionNotice(null);
    try {
      if (confirmAction.type === "cancel") {
        const cancelledRun = await cancelRun(confirmAction.run.run_id);
        setActionNotice(
          cancelledRun.backend_status === "cancelled"
            ? `Run ${confirmAction.run.run_id} cancelled.`
            : `Cancellation requested for run ${confirmAction.run.run_id}.`
        );
      } else if (confirmAction.type === "archive") {
        await archiveRun(confirmAction.run.run_id);
        setActionNotice(`Run ${confirmAction.run.run_id} archived.`);
      } else if (confirmAction.type === "unarchive") {
        await unarchiveRun(confirmAction.run.run_id);
        setActionNotice(`Run ${confirmAction.run.run_id} restored to active.`);
      }
      setConfirmAction(null);
      if (!(await loadRuns())) setActionNotice(null);
    } catch (err: any) {
      setActionNotice(null);
      setError(err.message || `Failed to ${confirmAction.type} run.`);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleRequestDeletePreview = async () => {
    if (selectedRunIds.size === 0) return;
    setActionInProgress(true);
    setError(null);
    try {
      const preview = await previewDeleteArchivedRuns(Array.from(selectedRunIds));
      setDeletePreview(preview);
      setIsDeletePreviewOpen(true);
    } catch (err: any) {
      setError(err.message || "Failed to generate delete preview.");
    } finally {
      setActionInProgress(false);
    }
  };

  const handleExecuteDeleteArchived = async () => {
    if (!deletePreview) return;
    setActionInProgress(true);
    setError(null);
    try {
      const idempotencyKey = generateIdempotencyKey();
      await deleteArchivedRuns(
        deletePreview.requested_run_ids,
        deletePreview.preview_revision,
        idempotencyKey
      );
      setActionNotice(`Successfully deleted ${deletePreview.eligible_run_ids.length} archived runs.`);
      setIsDeletePreviewOpen(false);
      setDeletePreview(null);
      setSelectedRunIds(new Set());
      await loadRuns();
    } catch (err: any) {
      setError(err.message || "Failed to delete archived runs.");
    } finally {
      setActionInProgress(false);
    }
  };

  const formatSourceSummary = (run: PipelineRunResource) => {
    const input = run.input;
    if (!input) return "Standard input";
    if (input.jobs_input_source === "scanner") return "Scanner input";
    if (input.jobs_input_source === "combined") return "Combined (Upload + Scans)";
    if (input.jobs_input_source === "scan") return "Scan outputs";
    if (input.sources && Array.isArray(input.sources)) {
      const scans = input.sources.filter((s) => s.type === "scan");
      const uploads = input.sources.filter((s) => s.type === "upload");
      if (scans.length > 0 && uploads.length > 0) return `Combined (${uploads.length} files, ${scans.length} scans)`;
      if (scans.length > 0) return `${scans.length} Scan output(s)`;
      if (uploads.length > 0) return `Upload: ${uploads[0].filename || "File"}`;
    }
    return input.jobs_input_source || "Upload";
  };

  const columns: TableColumn<PipelineRunResource>[] = useMemo(() => {
    return [
      {
        key: "run_name",
        header: "Run Name / ID",
        render: (item) => (
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <button
              type="button"
              onClick={() => onSelectRun(item.run_id)}
              style={{
                border: "none",
                background: "transparent",
                padding: 0,
                textAlign: "left",
                fontWeight: 600,
                color: "var(--accent)",
                cursor: "pointer",
                fontSize: 14,
              }}
            >
              {item.run_name || <span title={item.run_id}>{formatIdentifier(item.run_id)}</span>}
            </button>
            <span style={{ fontSize: 12, color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
              <span title={item.run_id}>{formatIdentifier(item.run_id)}</span>
            </span>
          </div>
        ),
      },
      {
        key: "status",
        header: "Status",
        width: "140px",
        render: (item) => {
          const cfg = statusMap[item.backend_status] || {
            variant: "neutral" as StatusVariant,
            label: item.display_status || item.backend_status,
          };
          const label = item.backend_status === "cancelled" ? cfg.label : item.display_status || cfg.label;
          const detail = item.status_detail?.trim();
          const showDetail = isDistinctStatusDetail(detail, label);
          return (
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <StatusBadge status={cfg.variant} label={label} />
              {showDetail && <span style={{ fontSize: 11, color: "var(--muted)" }}>{detail}</span>}
            </div>
          );
        },
      },
      {
        key: "source",
        header: "Input Source",
        render: (item) => (
          <span style={{ fontSize: 13 }}>{formatSourceSummary(item)}</span>
        ),
      },
      {
        key: "counts",
        header: "Jobs / CVs",
        render: (item) => {
          const c = item.counts || { total: 0, passed: 0, rejected: 0, skipped: 0, cvs_generated: 0 };
          return (
            <div style={{ fontSize: 13, display: "flex", gap: 6, alignItems: "center" }}>
              <strong>{c.total}</strong> total
              <span style={{ color: "var(--muted)" }}>·</span>
              <span style={{ color: "var(--success)" }}>{c.passed} passed</span>
              <span style={{ color: "var(--muted)" }}>·</span>
              <span style={{ color: "var(--danger)" }}>{c.rejected} rejected</span>
              {c.cvs_generated > 0 && (
                <>
                  <span style={{ color: "var(--muted)" }}>·</span>
                  <span style={{ color: "var(--info)" }}>{c.cvs_generated} CVs</span>
                </>
              )}
            </div>
          );
        },
      },
      {
        key: "created_at",
        header: "Created",
        width: "160px",
        render: (item) => {
          try {
            return (
              <span style={{ fontSize: 12, color: "var(--muted)" }}>
                {formatTimestamp(item.created_at)}
              </span>
            );
          } catch {
            return <span style={{ fontSize: 12, color: "var(--muted)" }}>{formatTimestamp(item.created_at)}</span>;
          }
        },
      },
      {
        key: "actions",
        header: "Actions",
        width: "150px",
        render: (item) => (
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <Button
              size="compact"
              variant="secondary"
              onClick={() => onSelectRun(item.run_id)}
            >
              View
            </Button>
            {item.capabilities.cancel && (
              <Button
                size="compact"
                variant="danger"
                onClick={() => setConfirmAction({ type: "cancel", run: item })}
              >
                Cancel
              </Button>
            )}
            {item.capabilities.archive && (
              <Button
                size="compact"
                variant="subtle"
                onClick={() => setConfirmAction({ type: "archive", run: item })}
              >
                Archive
              </Button>
            )}
            {item.capabilities.unarchive && (
              <Button
                size="compact"
                variant="subtle"
                onClick={() => setConfirmAction({ type: "unarchive", run: item })}
              >
                Restore
              </Button>
            )}
          </div>
        ),
      },
    ];
  }, [onSelectRun]);

  const tabItems = [
    { id: "active", label: "Active", count: activeCount },
    { id: "archived", label: "Archived", count: archivedCount },
    { id: "all", label: "All Runs" },
  ];

  return (
    <div className="content-container page-stack runs-list-page">
      {/* Header controls */}
      <div className="page-head">
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>Runs</h2>
          <p>
            Trigger, monitor, cancel, and archive local runs.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {view === "archived" && selectedRunIds.size > 0 && (
            <Button
              variant="danger"
              onClick={handleRequestDeletePreview}
              disabled={actionInProgress}
            >
              Delete Selected ({selectedRunIds.size})
            </Button>
          )}
          <Button variant="primary" onClick={() => setIsNewRunOpen(true)}>
            New Run
          </Button>
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

      {/* Tabs and Search */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <Tabs
          items={tabItems}
          activeId={view}
          onChange={(id) => {
            onViewChange(id as RunLifecycle);
          }}
        />
        <form className="page-search-form" onSubmit={handleSearchSubmit}>
          <label className="page-search">
            <span className="sr-only">Search runs</span>
            <input
              className="field page-search-input"
              type="search"
              placeholder="Search runs by ID, name, input..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <Button type="submit" variant="secondary">
            Search
          </Button>
          {activeSearch && (
            <Button
              type="button"
              variant="subtle"
              onClick={() => {
                setSearch("");
                setActiveSearch("");
                onPageChange(1);
              }}
            >
              Clear
            </Button>
          )}
        </form>
      </div>

      {/* Table */}
      {loading ? (
        <LoadingState message="Loading runs..." />
      ) : (
        <DataTable
          columns={columns}
          data={runs}
          keyField="run_id"
          selectedKeys={view === "archived" ? selectedRunIds : undefined}
          onToggleSelect={view === "archived" ? handleToggleSelect : undefined}
          onSelectAll={view === "archived" ? handleSelectAll : undefined}
          isAllSelected={view === "archived" && runs.length > 0 && selectedRunIds.size === runs.length}
          page={page}
          pageSize={pageSize}
          total={totalItems}
          onPageChange={onPageChange}
          emptyMessage={
            activeSearch
              ? "No runs match this search."
              : view === "archived"
              ? "No archived runs. Archived runs will appear here after they are moved from Active."
              : "No active runs yet. Trigger a run to process a job file with one of your Candidate Profiles."
          }
        />
      )}

      {/* New Run Dialog */}
      <NewRunDialog
        open={isNewRunOpen}
        onClose={() => setIsNewRunOpen(false)}
        initialScanIds={initialScanIds}
        onSuccess={(runId) => {
          setIsNewRunOpen(false);
          onSelectRun(runId);
        }}
      />

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmAction !== null}
        onClose={() => setConfirmAction(null)}
        title={
          confirmAction?.type === "cancel"
            ? "Cancel Run?"
            : confirmAction?.type === "archive"
            ? "Archive Run?"
            : "Restore Run?"
        }
        description={
          confirmAction?.type === "cancel"
            ? `Are you sure you want to cancel run ${confirmAction.run.run_id}? Any currently processing stage will be aborted.`
            : confirmAction?.type === "archive"
            ? `Archiving run ${confirmAction?.run.run_id} will move it to historical archives.`
            : `Restore run ${confirmAction?.run.run_id} back to active workspace.`
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
              variant={confirmAction?.type === "cancel" ? "danger" : "primary"}
              onClick={handleExecuteConfirmAction}
              disabled={actionInProgress}
            >
              {actionInProgress ? "Processing..." : "Confirm"}
            </Button>
          </div>
        }
      >
        <div style={{ fontSize: 14 }}>
          <strong>Run ID:</strong> {confirmAction?.run.run_id}
          <br />
          <strong>Run Name:</strong> {confirmAction?.run.run_name || "N/A"}
        </div>
      </Dialog>

      {/* Delete Archived Preview Dialog */}
      <Dialog
        open={isDeletePreviewOpen}
        onClose={() => setIsDeletePreviewOpen(false)}
        title="Permanently Delete Archived Runs"
        description="Review selected runs before permanent deletion. This action cannot be undone."
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, width: "100%" }}>
            <Button
              variant="secondary"
              onClick={() => setIsDeletePreviewOpen(false)}
              disabled={actionInProgress}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleExecuteDeleteArchived}
              disabled={
                actionInProgress ||
                !deletePreview ||
                deletePreview.blocked_run_ids.length > 0 ||
                deletePreview.eligible_run_ids.length === 0
              }
            >
              {actionInProgress ? "Deleting..." : "Permanently Delete"}
            </Button>
          </div>
        }
      >
        {deletePreview && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <strong>Requested:</strong> {deletePreview.requested_run_ids.length} run(s)
            </div>
            <div>
              <strong>Eligible for deletion:</strong> {deletePreview.eligible_run_ids.length} run(s)
            </div>
            {deletePreview.blocked_run_ids.length > 0 && (
              <div className="notice warn">
                <strong>Blocked ({deletePreview.blocked_run_ids.length}):</strong> Some selected runs are not archived or cannot be deleted:
                <ul>
                  {deletePreview.blocked_run_ids.map((id) => (
                    <li key={id}>{id}</li>
                  ))}
                </ul>
              </div>
            )}
            {deletePreview.missing_run_ids.length > 0 && (
              <div className="notice warn">
                <strong>Missing ({deletePreview.missing_run_ids.length}):</strong> {deletePreview.missing_run_ids.join(", ")}
              </div>
            )}
          </div>
        )}
      </Dialog>
    </div>
  );
};
