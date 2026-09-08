import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  Dialog,
  Button,
  Field,
  LoadingState,
  EmptyState,
} from "../../components";
import {
  fetchTrackedCompanies,
  verifyTrackedCompany,
  createTrackedCompany,
  createScan,
  fetchCompanyCatalog,
  trackCompanyFromCatalog,
} from "./api";
import {
  TrackedCompanyResource,
  PublishedWindow,
  ScanResource,
  CompanyCatalogItem,
} from "./types";
import { getApiErrorMessage } from "../../lib/api-client";

export interface NewScanDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (scan: ScanResource) => void;
}

const PUBLISHED_WINDOW_OPTIONS: Array<{ value: PublishedWindow; label: string }> = [
  { value: "any", label: "Any time" },
  { value: "past_12_hours", label: "Past 12 hours" },
  { value: "past_24_hours", label: "Past 24 hours" },
  { value: "past_7_days", label: "Past week" },
  { value: "past_30_days", label: "Past month" },
  { value: "past_180_days", label: "Past 6 months" },
];

// ponytail: inline text distinction for company profiles vs ATS/source platforms; upgrade to structured metadata badges if catalog expands.
export const NewScanDialog: React.FC<NewScanDialogProps> = ({
  open,
  onClose,
  onSuccess,
}) => {
  const [companies, setCompanies] = useState<TrackedCompanyResource[]>([]);
  const [loadingCompanies, setLoadingCompanies] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Form State
  const [scanName, setScanName] = useState("");
  const [selectedCompanyIds, setSelectedCompanyIds] = useState<string[]>([]);
  const [jobTitles, setJobTitles] = useState("");
  const [locations, setLocations] = useState("");
  const [publishedWindow, setPublishedWindow] = useState<PublishedWindow>("any");
  const [totalRows, setTotalRows] = useState(50);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Manage Companies Sub-Dialog
  const [isManageOpen, setIsManageOpen] = useState(false);
  const [manageTab, setManageTab] = useState<"tracked" | "catalog">("tracked");
  const [companySearch, setCompanySearch] = useState("");
  const [catalogItems, setCatalogItems] = useState<CompanyCatalogItem[]>([]);
  const [catalogSearch, setCatalogSearch] = useState("");
  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [trackingCatalogId, setTrackingCatalogId] = useState<string | null>(null);
  const [trackError, setTrackError] = useState<string | null>(null);
  const catalogSearchTimerRef = useRef<any>(null);

  // Add Company inline / sub-flow
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [addName, setAddName] = useState("");
  const [addUrl, setAddUrl] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [verifiedProvider, setVerifiedProvider] = useState<string | null>(null);
  const [addError, setAddError] = useState<string | null>(null);

  const loadCatalog = async (query = catalogSearch) => {
    setLoadingCatalog(true);
    setCatalogError(null);
    try {
      const res = await fetchCompanyCatalog({ search: query.trim(), page_size: 50 });
      setCatalogItems(res.data || []);
    } catch (err: any) {
      setCatalogError(getApiErrorMessage(err, "Failed to load company catalog."));
    } finally {
      setLoadingCatalog(false);
    }
  };

  const handleCatalogSearchChange = (value: string) => {
    setCatalogSearch(value);
    if (catalogSearchTimerRef.current) {
      clearTimeout(catalogSearchTimerRef.current);
    }
    catalogSearchTimerRef.current = setTimeout(() => {
      loadCatalog(value);
    }, 250);
  };

  const handleTrackFromCatalog = async (catalogId: string) => {
    setTrackingCatalogId(catalogId);
    setTrackError(null);
    try {
      const tracked = await trackCompanyFromCatalog(catalogId);
      setCompanies((prev) => {
        if (prev.some((c) => c.company_id === tracked.company_id)) {
          return prev;
        }
        return [...prev, tracked];
      });
      setSelectedCompanyIds((prev) =>
        prev.includes(tracked.company_id) ? prev : [...prev, tracked.company_id]
      );
      setCatalogItems((prev) =>
        prev.map((item) =>
          item.catalog_id === catalogId
            ? { ...item, is_tracked: true, tracked_company_id: tracked.company_id }
            : item
        )
      );
    } catch (err: any) {
      setTrackError(getApiErrorMessage(err, "Failed to track company from catalog."));
    } finally {
      setTrackingCatalogId(null);
    }
  };

  useEffect(() => {
    return () => {
      if (catalogSearchTimerRef.current) {
        clearTimeout(catalogSearchTimerRef.current);
      }
    };
  }, []);

  const loadCompanies = async () => {
    setLoadingCompanies(true);
    setLoadError(null);
    try {
      const data = await fetchTrackedCompanies();
      setCompanies(data);
      if (selectedCompanyIds.length === 0 && data.length > 0) {
        setSelectedCompanyIds(data.map((c) => c.company_id));
      }
    } catch (err: any) {
      setLoadError(err.message || "Failed to load tracked companies");
    } finally {
      setLoadingCompanies(false);
    }
  };

  useEffect(() => {
    if (open) {
      setScanName("");
      setJobTitles("");
      setLocations("");
      setPublishedWindow("any");
      setTotalRows(50);
      setSubmitError(null);
      loadCompanies();
    }
  }, [open]);

  const filteredCompanies = useMemo(() => {
    const q = companySearch.trim().toLowerCase();
    if (!q) return companies;
    return companies.filter((c) =>
      `${c.company_name} ${c.provider_id} ${c.careers_url}`.toLowerCase().includes(q)
    );
  }, [companies, companySearch]);

  const toggleCompany = (id: string) => {
    setSelectedCompanyIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const selectAllFiltered = () => {
    const idsToAdd = filteredCompanies.map((c) => c.company_id);
    setSelectedCompanyIds((prev) => {
      const set = new Set([...prev, ...idsToAdd]);
      return Array.from(set);
    });
  };

  const clearSelectedCompanies = () => {
    setSelectedCompanyIds([]);
  };

  const handleVerifyAndAddCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    setVerifying(true);
    setAddError(null);
    setVerifiedProvider(null);
    try {
      const verified = await verifyTrackedCompany({
        company_name: addName.trim(),
        careers_url: addUrl.trim(),
      });
      setVerifiedProvider(verified.provider_label || verified.provider_id);
      const created = await createTrackedCompany({
        company_name: addName.trim(),
        careers_url: addUrl.trim(),
      });
      setCompanies((prev) => [...prev, created]);
      setSelectedCompanyIds((prev) => [...prev, created.company_id]);
      setIsAddOpen(false);
      setAddName("");
      setAddUrl("");
    } catch (err: any) {
      setAddError(err.message || "Verification or company creation failed.");
    } finally {
      setVerifying(false);
    }
  };

  const handleSubmitScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedCompanyIds.length === 0) {
      setSubmitError("At least one tracked company must be selected.");
      return;
    }

    setSubmitting(true);
    setSubmitError(null);

    const splitLines = (str: string) =>
      str
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);

    try {
      const scan = await createScan({
        scan_name: scanName.trim() || undefined,
        company_ids: selectedCompanyIds,
        job_titles: splitLines(jobTitles),
        locations: splitLines(locations),
        published_window: publishedWindow,
        total_rows: Number(totalRows),
      });
      onSuccess(scan);
      onClose();
    } catch (err: any) {
      setSubmitError(err.message || "Failed to create scan");
    } finally {
      setSubmitting(false);
    }
  };

  const companySummaryText = useMemo(() => {
    if (companies.length === 0) return "No companies tracked";
    if (selectedCompanyIds.length === 0) {
      return "None selected";
    }
    const selectedNames = companies
      .filter((c) => selectedCompanyIds.includes(c.company_id))
      .map((c) => c.company_name);
    return `${selectedCompanyIds.length} selected: ${selectedNames.slice(0, 3).join(", ")}${
      selectedNames.length > 3 ? "..." : ""
    }`;
  }, [companies, selectedCompanyIds]);

  return (
    <>
      <Dialog
        open={open && !isManageOpen && !isAddOpen}
        onClose={onClose}
        title="New Scan"
        description="Search careers portals for active tracked company profiles and create reusable FitCV job input."
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, width: "100%" }}>
            <Button variant="secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSubmitScan}
              disabled={submitting || selectedCompanyIds.length === 0}
            >
              {submitting ? "Starting..." : "Start Scan"}
            </Button>
          </div>
        }
      >
        <form onSubmit={handleSubmitScan} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {submitError && (
            <div className="notice error" role="alert">
              {submitError}
            </div>
          )}

          <Field
            label="Scan Name"
            hint="Optional label. Uses companies & timestamp when empty."
            placeholder="e.g. Daily Tech Radar"
            value={scanName}
            onChange={(e) => setScanName(e.target.value)}
          />

          <div className="field-group">
            <label className="field-label">
              Tracked Companies <span className="required-mark">*</span>
            </label>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "8px 12px",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-md)",
                background: "var(--surface-2)",
              }}
            >
              <div style={{ fontSize: 13, color: "var(--text)" }}>{companySummaryText}</div>
              <Button
                size="compact"
                variant="secondary"
                type="button"
                onClick={() => setIsManageOpen(true)}
              >
                Manage
              </Button>
            </div>
            {companies.length === 0 && !loadingCompanies && (
              <div style={{ marginTop: 6, fontSize: 12, color: "var(--danger)" }}>
                No tracked companies available. Open Manage, then Company Catalog, and Track a bundled company before scanning.
              </div>
            )}
          </div>

          <Field
            label="Job Titles"
            type="textarea"
            rows={2}
            hint="One filter per line. Matches any if empty."
            placeholder="Software Engineer&#10;Data Scientist"
            value={jobTitles}
            onChange={(e) => setJobTitles(e.target.value)}
          />

          <Field
            label="Job Locations"
            type="textarea"
            rows={2}
            hint="One location per line. Matches any if empty."
            placeholder="Remote&#10;Berlin"
            value={locations}
            onChange={(e) => setLocations(e.target.value)}
          />

          <Field
            label="Published At"
            type="select"
            value={publishedWindow}
            options={PUBLISHED_WINDOW_OPTIONS}
            hint="Rolling window resolved when the Scan starts."
            onChange={(e) => setPublishedWindow(e.target.value as PublishedWindow)}
          />

          <Field
            label="Max Total Rows"
            type="number"
            value={totalRows}
            hint="Bounds total acquired job rows (1 to 200)."
            onChange={(e) => setTotalRows(Number(e.target.value))}
          />
        </form>
      </Dialog>

      {/* Manage Tracked Companies Dialog */}
      <Dialog
        open={open && isManageOpen}
        onClose={() => setIsManageOpen(false)}
        title="Manage Tracked Companies"
        description="Search catalog or registry to select companies for this Scan."
        footer={
          <div style={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
            {manageTab === "tracked" ? (
              <Button
                variant="secondary"
                type="button"
                onClick={() => {
                  setIsManageOpen(false);
                  setIsAddOpen(true);
                }}
              >
                + Add Company
              </Button>
            ) : (
              <div />
            )}
            <Button variant="primary" onClick={() => setIsManageOpen(false)}>
              Done
            </Button>
          </div>
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div className="tab-list" role="tablist" aria-label="Company management tabs">
            <button
              type="button"
              role="tab"
              id="tab-tracked"
              aria-selected={manageTab === "tracked"}
              aria-controls="panel-tracked"
              className="tab-button"
              onClick={() => setManageTab("tracked")}
            >
              Tracked Companies ({companies.length})
            </button>
            <button
              type="button"
              role="tab"
              id="tab-catalog"
              aria-selected={manageTab === "catalog"}
              aria-controls="panel-catalog"
              className="tab-button"
              onClick={() => {
                setManageTab("catalog");
                if (catalogItems.length === 0 && !loadingCatalog) {
                  loadCatalog();
                }
              }}
            >
              Company Catalog
            </button>
          </div>

          {manageTab === "tracked" ? (
            <div id="panel-tracked" role="tabpanel" aria-labelledby="tab-tracked" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <Field
                label="Search Tracked Companies"
                type="search"
                placeholder="Search by company name, ATS / source platform, or domain..."
                value={companySearch}
                onChange={(e) => setCompanySearch(e.target.value)}
              />

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                <div style={{ display: "flex", gap: 8 }}>
                  <Button size="compact" variant="secondary" onClick={selectAllFiltered}>
                    Select all filtered
                  </Button>
                  <Button size="compact" variant="secondary" onClick={clearSelectedCompanies}>
                    Clear selection
                  </Button>
                </div>
                <span style={{ fontSize: 13, color: "var(--muted)" }}>
                  {selectedCompanyIds.length} of {companies.length} selected
                </span>
              </div>

              {loadingCompanies ? (
                <LoadingState message="Loading companies..." />
              ) : loadError ? (
                <div className="notice error" role="alert">
                  {loadError}{" "}
                  <Button size="compact" variant="secondary" onClick={loadCompanies}>
                    Retry
                  </Button>
                </div>
              ) : filteredCompanies.length === 0 ? (
                <EmptyState
                  title="No tracked companies"
                  description="Track a bundled company from Company Catalog before creating a Scan, or add a company profile with a supported ATS / source platform."
                />
              ) : (
                <div
                  style={{
                    maxHeight: 280,
                    overflowY: "auto",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-md)",
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  {filteredCompanies.map((c) => {
                    const checked = selectedCompanyIds.includes(c.company_id);
                    return (
                      <label
                        key={c.company_id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 12,
                          padding: "8px 12px",
                          borderBottom: "1px solid var(--border-soft)",
                          cursor: "pointer",
                          background: checked ? "var(--surface-2)" : "transparent",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleCompany(c.company_id)}
                        />
                        <div style={{ display: "flex", flexDirection: "column", minWidth: 0, flex: 1 }}>
                          <div style={{ fontSize: 13, wordBreak: "break-word" }}>
                            <span style={{ color: "var(--muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.04em", marginRight: 6 }}>Company</span>
                            <strong>{c.company_name}</strong>
                          </div>
                          <span style={{ fontSize: 11, color: "var(--muted)", wordBreak: "break-all" }}>
                            ATS / Source: {c.provider_label || c.provider_id} · {c.careers_url}
                          </span>
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            <div id="panel-catalog" role="tabpanel" aria-labelledby="tab-catalog" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <Field
                label="Search Catalog"
                type="search"
                placeholder="Search catalog by company name or ATS / source platform..."
                value={catalogSearch}
                onChange={(e) => handleCatalogSearchChange(e.target.value)}
              />

              {trackError && (
                <div className="notice error" role="alert">
                  {trackError}
                </div>
              )}

              {loadingCatalog ? (
                <LoadingState message="Loading catalog companies..." />
              ) : catalogError ? (
                <div className="notice error" role="alert">
                  {catalogError}{" "}
                  <Button size="compact" variant="secondary" onClick={() => loadCatalog(catalogSearch)}>
                    Retry
                  </Button>
                </div>
              ) : catalogItems.length === 0 ? (
                <EmptyState
                  title="No catalog company profiles found"
                  description="Try a different search term or clear the filter."
                />
              ) : (
                <div
                  style={{
                    maxHeight: 280,
                    overflowY: "auto",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-md)",
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  {catalogItems.map((item) => {
                    const isAlreadyTracked =
                      item.is_tracked ||
                      Boolean(item.tracked_company_id) ||
                      companies.some(
                        (c) =>
                          (item.tracked_company_id && c.company_id === item.tracked_company_id) ||
                          (item.catalog_id && c.catalog_id === item.catalog_id) ||
                          c.company_name.toLowerCase() === item.company_name.toLowerCase()
                      );

                    return (
                      <div
                        key={item.catalog_id}
                        data-catalog-id={item.catalog_id}
                        className="catalog-item-row"
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: 12,
                          padding: "10px 12px",
                          borderBottom: "1px solid var(--border-soft)",
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ display: "flex", flexDirection: "column", minWidth: 0, flex: "1 1 180px" }}>
                          <div style={{ fontSize: 13, wordBreak: "break-word" }}>
                            <span style={{ color: "var(--muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.04em", marginRight: 6 }}>Company</span>
                            <strong>{item.company_name}</strong>
                          </div>
                          <span style={{ fontSize: 11, color: "var(--muted)", wordBreak: "break-all" }}>
                            ATS / Source: {item.provider_label || item.provider_id} · {item.careers_url}
                          </span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                          {item.discovery_only ? (
                            <>
                              <span className="status-badge status-badge-neutral" style={{ fontSize: 11 }}>
                                Marketplace / Discovery only
                              </span>
                              <Button
                                size="compact"
                                variant="secondary"
                                disabled
                                aria-disabled="true"
                                title="Marketplace / Discovery only"
                              >
                                Track
                              </Button>
                            </>
                          ) : isAlreadyTracked ? (
                            <>
                              <span className="status-badge status-badge-success" style={{ fontSize: 11 }}>
                                Tracked
                              </span>
                              <Button
                                size="compact"
                                variant="secondary"
                                disabled
                                aria-disabled="true"
                              >
                                Tracked
                              </Button>
                            </>
                          ) : (
                            <Button
                              size="compact"
                              variant="primary"
                              onClick={() => handleTrackFromCatalog(item.catalog_id)}
                              disabled={trackingCatalogId === item.catalog_id}
                              aria-label={`Track ${item.company_name}`}
                            >
                              {trackingCatalogId === item.catalog_id ? "Tracking..." : "Track"}
                            </Button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </Dialog>

      {/* Add Company Dialog */}
      <Dialog
        open={open && isAddOpen}
        onClose={() => {
          setIsAddOpen(false);
          setIsManageOpen(true);
        }}
        title="Add Tracked Company Profile"
        description="Verify public careers portal URL before adding to tracked company registry."
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, width: "100%" }}>
            <Button
              variant="secondary"
              onClick={() => {
                setIsAddOpen(false);
                setIsManageOpen(true);
              }}
              disabled={verifying}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleVerifyAndAddCompany}
              disabled={verifying || !addName.trim() || !addUrl.trim()}
            >
              {verifying ? "Verifying..." : "Verify & Add"}
            </Button>
          </div>
        }
      >
        <form onSubmit={handleVerifyAndAddCompany} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {addError && (
            <div className="notice error" role="alert">
              {addError}
            </div>
          )}

          {verifiedProvider && (
            <div className="notice success" role="status">
              Verified ATS / Source: {verifiedProvider}
            </div>
          )}

          <Field
            label="Company Name"
            required
            placeholder="e.g. Acme Corp"
            value={addName}
            onChange={(e) => setAddName(e.target.value)}
          />

          <Field
            label="Careers Portal URL"
            required
            placeholder="https://careers.example.com or supported portal URL"
            hint="Must be a public HTTPS URL supported by an integrated ATS / source platform."
            value={addUrl}
            onChange={(e) => setAddUrl(e.target.value)}
          />
        </form>
      </Dialog>
    </>
  );
};
