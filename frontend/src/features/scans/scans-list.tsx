import React, { useState, useEffect, useMemo, useCallback } from "react";
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
import {
  fetchScans,
  archiveScans,
  unarchiveScans,
  previewDeleteScans,
  deleteScans,
  buildRunSourcesHash,
} from "./api";
import { ScanResource, ScanLifecycle, DeletePreviewResult } from "./types";
import { NewScanDialog } from "./new-scan-dialog";

export interface ScansListPageProps {
  onSelectScan: (scanId: string) => void;
  lifecycle: ScanLifecycle;
  onTabChange: (tab: ScanLifecycle) => void;
  page: number;
  onPageChange: (newPage: number) => void;
}

const statusMap: Record<string, { variant: StatusVariant; label: string }> = {
  queued: { variant: "neutral", label: "Queued" },
  running: { variant: "info", label: "Running" },
  cancelling: { variant: "warn", label: "Cancelling" },
  succeeded: { variant: "success", label: "Succeeded" },
  failed: { variant: "danger", label: "Failed" },
  cancelled: { variant: "neutral", label: "Cancelled" },
};

export const ScansListPage: React.FC<ScansListPageProps> = ({
  onSelectScan,
  lifecycle,
  onTabChange,
  page,
  onPageChange,
}) => {
  const [scans, setScans] = useState<ScanResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalItems, setTotalItems] = useState(0);
  const [pageSize] = useState(20);
  const [activeCount, setActiveCount] = useState(0);
  const [archivedCount, setArchivedCount] = useState(0);

  // Multi-selection state
  const [selectedScanIds, setSelectedScanIds] = useState<Set<string>>(new Set());

  // Dialog States
  const [isNewScanOpen, setIsNewScanOpen] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Delete Preview Dialog State
  const [deletePreview, setDeletePreview] = useState<DeletePreviewResult | null>(null);
  const [isDeletePreviewOpen, setIsDeletePreviewOpen] = useState(false);

  const loadScans = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchScans({
        lifecycle,
        page,
        page_size: pageSize,
      });
      setScans(res.data || []);
      setTotalItems(res.page?.total_items ?? res.total_items ?? res.total ?? 0);
      if (res.meta) {
        if (typeof res.meta.active_count === "number") setActiveCount(res.meta.active_count);
        if (typeof res.meta.archived_count === "number") setArchivedCount(res.meta.archived_count);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load scans");
    } finally {
      setLoading(false);
    }
  }, [lifecycle, page, pageSize]);

  useEffect(() => {
    setSelectedScanIds(new Set());
    loadScans();
  }, [loadScans]);

  const handleToggleSelect = (scanId: string) => {
    setSelectedScanIds((prev) => {
      const next = new Set(prev);
      if (next.has(scanId)) {
        next.delete(scanId);
      } else {
        next.add(scanId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedScanIds.size === scans.length && scans.length > 0) {
      setSelectedScanIds(new Set());
    } else {
      setSelectedScanIds(new Set(scans.map((s) => s.scan_id)));
    }
  };

  const selectedScans = useMemo(() => {
    return scans.filter((s) => selectedScanIds.has(s.scan_id));
  }, [scans, selectedScanIds]);

  const canArchiveAllSelected = useMemo(() => {
    if (selectedScans.length === 0) return false;
    return selectedScans.every((s) => s.capabilities.archive);
  }, [selectedScans]);

  const canUnarchiveAllSelected = useMemo(() => {
    if (selectedScans.length === 0) return false;
    return selectedScans.every((s) => s.capabilities.unarchive);
  }, [selectedScans]);

  const canUseSelectedForRun = useMemo(
    () => lifecycle === "active" && selectedScans.some((s) => s.capabilities.use_for_run),
    [lifecycle, selectedScans]
  );

  const handleUseSelectedForRun = () => {
    const scanIds = selectedScans.filter((s) => s.capabilities.use_for_run).map((s) => s.scan_id);
    if (scanIds.length === 0) {
      setActionNotice("Selected scans are not eligible for a Run.");
      return;
    }
    window.location.hash = buildRunSourcesHash(scanIds);
  };

  const handleBulkArchive = async () => {
    if (selectedScans.length === 0) return;
    setActionInProgress(true);
    try {
      const items = selectedScans.map((s) => ({
        scan_id: s.scan_id,
        expected_revision: s.row_revision,
      }));
      await archiveScans(items);
      setSelectedScanIds(new Set());
      setActionNotice(`Archived ${items.length} scan(s).`);
      loadScans();
    } catch (err: any) {
      setActionNotice(`Archive failed: ${err.message}`);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleBulkUnarchive = async () => {
    if (selectedScans.length === 0) return;
    setActionInProgress(true);
    try {
      const items = selectedScans.map((s) => ({
        scan_id: s.scan_id,
        expected_revision: s.row_revision,
      }));
      await unarchiveScans(items);
      setSelectedScanIds(new Set());
      setActionNotice(`Unarchived ${items.length} scan(s).`);
      loadScans();
    } catch (err: any) {
      setActionNotice(`Unarchive failed: ${err.message}`);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleOpenDeletePreview = async () => {
    if (selectedScans.length === 0) return;
    setActionInProgress(true);
    try {
      const preview = await previewDeleteScans(Array.from(selectedScanIds));
      setDeletePreview(preview);
      setIsDeletePreviewOpen(true);
    } catch (err: any) {
      setActionNotice(`Delete preview failed: ${err.message}`);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deletePreview) return;
    setActionInProgress(true);
    try {
      await deleteScans(Array.from(selectedScanIds), deletePreview.preview_revision);
      setIsDeletePreviewOpen(false);
      setDeletePreview(null);
      setSelectedScanIds(new Set());
      setActionNotice("Selected scans deleted permanently.");
      loadScans();
    } catch (err: any) {
      setActionNotice(`Delete failed: ${err.message}`);
    } finally {
      setActionInProgress(false);
    }
  };

  const columns: TableColumn<ScanResource>[] = [
    {
      key: "scan_id",
      header: "Scan ID",
      render: (scan) => (
        <button
          type="button"
          onClick={() => onSelectScan(scan.scan_id)}
          style={{
            background: "none",
            border: "none",
            padding: 0,
            color: "var(--accent)",
            fontWeight: 600,
            fontSize: 13,
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          {scan.scan_id}
        </button>
      ),
    },
    {
      key: "execution_status",
      header: "Status",
      render: (scan) => {
        const badge = statusMap[scan.execution_status] || {
          variant: "neutral",
          label: scan.execution_status,
        };
        return <StatusBadge status={badge.variant} label={badge.label} />;
      },
    },
    {
      key: "scan_name",
      header: "Scan Name",
      render: (scan) => <span style={{ fontSize: 13 }}>{scan.scan_name}</span>,
    },
    {
      key: "created_at",
      header: "Created Time",
      render: (scan) => (
        <span style={{ fontSize: 12, color: "var(--muted)" }}>
          {new Date(scan.created_at).toLocaleString()}
        </span>
      ),
    },
    {
      key: "output_record_count",
      header: "Output Jobs",
      render: (scan) => (
        <span style={{ fontSize: 12 }}>
          {scan.output_record_count !== null && scan.output_record_count !== undefined
            ? `${scan.output_record_count} jobs`
            : "—"}
        </span>
      ),
    },
  ];

  return (
    <div className="content-container">
      <div
        className="page-head"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 20,
        }}
      >
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
            Workspace
          </p>
          <h2
            style={{
              margin: 0,
              fontFamily: "var(--display-font)",
              fontSize: 26,
              letterSpacing: "-0.03em",
            }}
          >
            Scans
          </h2>
          <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>
            Create and manage reusable FitCV job input from tracked companies.
          </p>
        </div>

        <Button variant="primary" onClick={() => setIsNewScanOpen(true)}>
          New Scan
        </Button>
      </div>

      <div style={{ marginBottom: 16 }}>
        <Tabs
          items={[
            { id: "active", label: "Active", count: activeCount || undefined },
            { id: "archived", label: "Archived", count: archivedCount || undefined },
          ]}
          activeId={lifecycle}
          onChange={(tab) => onTabChange(tab as ScanLifecycle)}
        />
      </div>

      {actionNotice && (
        <div className="notice info" role="status" style={{ marginBottom: 16 }}>
          {actionNotice}
        </div>
      )}

      {/* Bulk actions banner */}
      {selectedScanIds.size > 0 && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "10px 16px",
            marginBottom: 16,
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <div style={{ fontSize: 13 }}>
            <strong>{selectedScanIds.size} Scan(s) selected</strong>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {lifecycle === "active" && (
              <Button
                variant="primary"
                size="compact"
                onClick={handleUseSelectedForRun}
                disabled={!canUseSelectedForRun || actionInProgress}
              >
                Use in Run
              </Button>
            )}
            {lifecycle === "active" ? (
              <Button
                variant="secondary"
                size="compact"
                onClick={handleBulkArchive}
                disabled={!canArchiveAllSelected || actionInProgress}
              >
                Archive
              </Button>
            ) : (
              <>
                <Button
                  variant="secondary"
                  size="compact"
                  onClick={handleBulkUnarchive}
                  disabled={!canUnarchiveAllSelected || actionInProgress}
                >
                  Unarchive
                </Button>
                <Button
                  variant="secondary"
                  size="compact"
                  onClick={handleOpenDeletePreview}
                  disabled={actionInProgress}
                  style={{ color: "var(--danger)" }}
                >
                  Delete
                </Button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Main Table */}
      {loading ? (
        <LoadingState message="Loading scans..." />
      ) : error ? (
        <div className="notice error" role="alert">
          {error}{" "}
          <Button size="compact" variant="secondary" onClick={loadScans}>
            Retry
          </Button>
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={scans}
          keyField="scan_id"
          selectedKeys={selectedScanIds}
          onToggleSelect={handleToggleSelect}
          onSelectAll={handleSelectAll}
          isAllSelected={scans.length > 0 && selectedScanIds.size === scans.length}
          page={page}
          pageSize={pageSize}
          total={totalItems}
          onPageChange={onPageChange}
          emptyMessage={
            lifecycle === "active"
              ? "No active scans found. Start a New Scan to fetch job postings."
              : "No archived scans."
          }
        />
      )}

      {/* New Scan Dialog */}
      <NewScanDialog
        open={isNewScanOpen}
        onClose={() => setIsNewScanOpen(false)}
        onSuccess={(created) => {
          setIsNewScanOpen(false);
          onSelectScan(created.scan_id);
        }}
      />

      {/* Delete Preview Dialog */}
      <Dialog
        open={isDeletePreviewOpen}
        onClose={() => setIsDeletePreviewOpen(false)}
        title="Delete Archived Scans"
        description="Review scan deletion eligibility before permanent removal."
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, width: "100%" }}>
            <Button variant="secondary" onClick={() => setIsDeletePreviewOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleConfirmDelete}
              disabled={
                actionInProgress ||
                !deletePreview ||
                deletePreview.eligible_scan_ids.length === 0
              }
              style={{ background: "var(--danger)", borderColor: "var(--danger)" }}
            >
              {actionInProgress ? "Deleting..." : "Permanently Delete"}
            </Button>
          </div>
        }
      >
        {deletePreview && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12, fontSize: 13 }}>
            <div>
              <strong>Eligible for deletion:</strong> {deletePreview.eligible_scan_ids.length}
              {deletePreview.eligible_scan_ids.length > 0 && (
                <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 4 }}>
                  {deletePreview.eligible_scan_ids.join(", ")}
                </div>
              )}
            </div>

            {deletePreview.referenced_scan_ids.length > 0 && (
              <div style={{ color: "var(--danger)" }}>
                <strong>Blocked (referenced by Runs):</strong> {deletePreview.referenced_scan_ids.join(", ")}
              </div>
            )}

            {deletePreview.invalid_scan_ids.length > 0 && (
              <div style={{ color: "var(--danger)" }}>
                <strong>Blocked (not archived / non-terminal):</strong> {deletePreview.invalid_scan_ids.join(", ")}
              </div>
            )}

            {deletePreview.eligible_scan_ids.length === 0 && (
              <div className="notice warn">
                None of the selected scans are eligible for deletion.
              </div>
            )}
          </div>
        )}
      </Dialog>
    </div>
  );
};
