import React, { useState, useEffect, useMemo } from "react";
import { Dialog, Button, Field, LoadingState, EmptyState } from "../../components";
import { fetchScans } from "./api";
import { ScanResource } from "./types";
import { formatIdentifier } from "../../lib/format";

export interface RunSourceSelectionProps {
  open: boolean;
  onClose: () => void;
  selectedScanIds: string[];
  onApply: (scanIds: string[]) => void;
}

export const RunSourceSelectionDialog: React.FC<RunSourceSelectionProps> = ({
  open,
  onClose,
  selectedScanIds,
  onApply,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scans, setScans] = useState<ScanResource[]>([]);
  const [draftSelectedIds, setDraftSelectedIds] = useState<string[]>([]);
  const [search, setSearch] = useState("");

  const loadEligibleScans = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchScans({
        lifecycle: "active",
        execution_status: "succeeded",
        usable_for_run: true,
        page: 1,
        page_size: 50,
      });
      const eligible = (res.data || []).filter((s) => s.capabilities.use_for_run);
      setScans(eligible);
    } catch (err: any) {
      setError(err.message || "Failed to load eligible scans");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      setDraftSelectedIds([...selectedScanIds]);
      setSearch("");
      loadEligibleScans();
    }
  }, [open, selectedScanIds]);

  const filteredScans = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return scans;
    return scans.filter((s) => {
      const text = `${s.scan_id} ${s.scan_name} ${(s.company_snapshots || [])
        .map((c) => c.company_name)
        .join(" ")}`.toLowerCase();
      return text.includes(q);
    });
  }, [scans, search]);

  const toggleScan = (id: string) => {
    setDraftSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const selectAllFiltered = () => {
    const idsToAdd = filteredScans.map((s) => s.scan_id);
    setDraftSelectedIds((prev) => {
      const next = [...prev];
      for (const id of idsToAdd) {
        if (!next.includes(id)) {
          next.push(id);
        }
      }
      return next;
    });
  };

  const clearSelection = () => {
    setDraftSelectedIds([]);
  };

  const handleApply = () => {
    onApply(draftSelectedIds);
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Manage Eligible Scan Outputs"
      description="Search and select successful Scan outputs for this Run."
      className="managed-selection-dialog"
      footer={
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, width: "100%" }}>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleApply}>
            Apply
          </Button>
        </div>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Field
          label="Search Scans"
          type="search"
          placeholder="Search Scan ID, name, or company"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: 8 }}>
            <Button size="compact" variant="secondary" onClick={selectAllFiltered}>
              Select all filtered
            </Button>
            <Button size="compact" variant="secondary" onClick={clearSelection}>
              Clear selection
            </Button>
          </div>
          <span style={{ fontSize: 13, color: "var(--muted)" }}>
            {draftSelectedIds.length} selected
          </span>
        </div>

        {loading ? (
          <LoadingState message="Loading eligible scans..." />
        ) : error ? (
          <div className="notice error" role="alert">
            {error}{" "}
            <Button size="compact" variant="secondary" onClick={loadEligibleScans}>
              Retry
            </Button>
          </div>
        ) : filteredScans.length === 0 ? (
          <EmptyState
            title="No eligible scans found"
            description={
              scans.length === 0
                ? "No active, succeeded Scans with valid outputs are available."
                : "No Scans match your search query."
            }
          />
        ) : (
          <div
            style={{
              maxHeight: 320,
              overflowY: "auto",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-md)",
              display: "flex",
              flexDirection: "column",
            }}
          >
            {filteredScans.map((scan) => {
              const checked = draftSelectedIds.includes(scan.scan_id);
              const companyNames = (scan.company_snapshots || [])
                .map((c) => c.company_name)
                .join(", ");
              return (
                <label
                  key={scan.scan_id}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 12,
                    padding: "10px 14px",
                    borderBottom: "1px solid var(--border-soft)",
                    cursor: "pointer",
                    background: checked ? "var(--surface-2)" : "transparent",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleScan(scan.scan_id)}
                    style={{ marginTop: 3 }}
                  />
                  <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <strong title={scan.scan_id} style={{ fontSize: 13 }}>{formatIdentifier(scan.scan_id)}</strong>
                      <span style={{ fontSize: 13, color: "var(--text)" }}>{scan.scan_name}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--muted)" }}>
                      {companyNames || "All Tracked Companies"} · {scan.output_record_count ?? 0} jobs
                    </div>
                  </div>
                </label>
              );
            })}
          </div>
        )}
      </div>
    </Dialog>
  );
};
