import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Button,
  Tabs,
  DataTable,
  TableColumn,
  StatusBadge,
  StatusVariant,
  LoadingState,
  Dialog,
  Field,
} from "../../components";
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

export const RunsListPage: React.FC<RunsListPageProps> = ({
  onSelectRun,
  view,
  onViewChange,
  page,
  onPageChange,
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

  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchRuns({
        view,
        search: activeSearch,
        page,
        page_size: pageSize,
      });
      setRuns(res.data || []);
      setTotalItems(res.total_items || 0);
      if (res.meta) {
        if (typeof res.meta.active_count === "number") setActiveCount(res.meta.active_count);
        if (typeof res.meta.archived_count === "number") setArchivedCount(res.meta.archived_count);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load runs.");
    } finally {
      setLoading(false);
    }
  }, [view, activeSearch, page, pageSize]);

  useEffect(() => {
    setSelectedRunIds(new Set());
    loadRuns();
  }, [loadRuns]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveSearch(search.trim());
    onPageChange(1);
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
        await cancelRun(confirmAction.run.run_id);
        setActionNotice(`Cancellation requested for run ${confirmAction.run.run_id}.`);
      } else if (confirmAction.type === "archive") {
        await archiveRun(confirmAction.run.run_id);
        setActionNotice(`Run ${confirmAction.run.run_id} archived.`);
      } else if (confirmAction.type === "unarchive") {
        await unarchiveRun(confirmAction.run.run_id);
        setActionNotice(`Run ${confirmAction.run.run_id} restored to active.`);
      }
      setConfirmAction(null);
      await loadRuns();
    } catch (err: any) {
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
      setActionNotice(`Successfully deleted ${deletePreview.matched_run_ids.length} archived runs.`);
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
              {item.run_name || item.run_id}
            </button>
            <span style={{ fontSize: 12, color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
              {item.run_id}
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
          return (
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <StatusBadge status={cfg.variant} label={item.display_status || cfg.label} />
              {item.status_detail && (
                <span style={{ fontSize: 11, color: "var(--muted)" }}>{item.status_detail}</span>
              )}
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
                {new Date(item.created_at).toLocaleString()}
              </span>
            );
          } catch {
            return <span style={{ fontSize: 12, color: "var(--muted)" }}>{item.created_at}</span>;
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
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header controls */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ margin: "0 0 4px 0", fontSize: 24, fontWeight: 700 }}>Runs</h1>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 14 }}>
            Monitor pipeline executions, stage progression, fit results, and grounded CV generations.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
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
        <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
          <div style={{ width: 260 }}>
            <Field
              label=""
              type="search"
              placeholder="Search runs by ID, name, input..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
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
          emptyMessage="No runs found."
        />
      )}

      {/* New Run Dialog */}
      <NewRunDialog
        open={isNewRunOpen}
        onClose={() => setIsNewRunOpen(false)}
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
                deletePreview.matched_run_ids.length === 0
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
              <strong>Eligible for deletion:</strong> {deletePreview.matched_run_ids.length} run(s)
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
