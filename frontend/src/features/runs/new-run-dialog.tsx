import React, { useState, useEffect } from "react";
import { Dialog, Button, Field, LoadingState } from "../../components";
import { fetchProfiles } from "../candidate-profile/api";
import { CandidateProfile } from "../candidate-profile/types";
import { RunSourceSelectionDialog } from "../scans/run-source-selection";
import { triggerRun, generateIdempotencyKey } from "./api";
import { ApiClientError } from "../../lib/api-client";

export const PROVIDER_SETTINGS_HREF = "/app#/settings/providers";

export interface RunErrorActionProps {
  code: string | null;
  action: string | null;
}

export const RunErrorAction: React.FC<RunErrorActionProps> = ({ code, action }) => {
  if (code !== "local_readiness_required" && !action) {
    return null;
  }

  return (
    <a href={PROVIDER_SETTINGS_HREF}>
      {action || "Open provider settings"}
    </a>
  );
};

export interface NewRunDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (runId: string) => void;
  initialScanIds?: string[];
}

export type SourceMode = "upload" | "scans" | "combined";

export const NewRunDialog: React.FC<NewRunDialogProps> = ({
  open,
  onClose,
  onSuccess,
  initialScanIds = [],
}) => {
  // Profiles
  const [profiles, setProfiles] = useState<CandidateProfile[]>([]);
  const [loadingProfiles, setLoadingProfiles] = useState(false);
  const [selectedProfileId, setSelectedProfileId] = useState<string>("");

  // Input source mode
  const [sourceMode, setSourceMode] = useState<SourceMode>("upload");

  // File upload state
  const [file, setFile] = useState<File | null>(null);

  // Scan outputs selection
  const [selectedScanIds, setSelectedScanIds] = useState<string[]>([]);
  const [isScanPickerOpen, setIsScanPickerOpen] = useState(false);

  // Run settings
  const [runName, setRunName] = useState("");
  const [configPath, setConfigPath] = useState(".env.yaml");

  // Form submission state
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [errorAction, setErrorAction] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      setError(null);
      setErrorCode(null);
      setErrorAction(null);
      setFieldErrors({});
      setSubmitting(false);
      setFile(null);
      setSelectedScanIds([...initialScanIds]);
      setRunName("");
      setConfigPath(".env.yaml");
      setSourceMode(initialScanIds.length > 0 ? "scans" : "upload");

      // Load active profiles
      setLoadingProfiles(true);
      fetchProfiles({ view: "active", page: 1, page_size: 50 })
        .then((res) => {
          const list = res.data || [];
          setProfiles(list);
          if (list.length > 0) {
            setSelectedProfileId(list[0].profile_id);
          } else {
            setSelectedProfileId("");
          }
        })
        .catch((err) => {
          setError(err.message || "Failed to load candidate profiles.");
        })
        .finally(() => {
          setLoadingProfiles(false);
        });
    }
  }, [open, initialScanIds]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] || null;
    if (selected) {
      const ext = selected.name.substring(selected.name.lastIndexOf(".")).toLowerCase();
      if (ext !== ".json" && ext !== ".jsonl") {
        setFieldErrors((prev) => ({
          ...prev,
          jobs_file: "Only .json and .jsonl files are supported.",
        }));
        setFile(null);
        return;
      }
      if (selected.size > 50 * 1024 * 1024) {
        setFieldErrors((prev) => ({
          ...prev,
          jobs_file: "File size must not exceed 50 MB.",
        }));
        setFile(null);
        return;
      }
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next.jobs_file;
        return next;
      });
      setFile(selected);
      if (!runName) {
        const stem = selected.name.replace(/\.[^/.]+$/, "");
        setRunName(stem.slice(0, 120));
      }
    } else {
      setFile(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setErrorCode(null);
    setErrorAction(null);
    const errors: Record<string, string> = {};

    if (!selectedProfileId) {
      errors.profile_id = "An active Candidate Profile is required.";
    }

    if (sourceMode === "upload") {
      if (!file) {
        errors.jobs_file = "A jobs file (.json or .jsonl) is required.";
      }
    } else if (sourceMode === "scans") {
      if (selectedScanIds.length === 0) {
        errors.scan_ids = "Select at least one eligible Scan output.";
      }
    } else if (sourceMode === "combined") {
      if (!file && selectedScanIds.length === 0) {
        errors.jobs_file = "Provide an uploaded file or select at least one Scan.";
      }
    }

    if (runName && runName.length > 120) {
      errors.run_name = "Run name must be 120 characters or fewer.";
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("profile_id", selectedProfileId);
      if (file && (sourceMode === "upload" || sourceMode === "combined")) {
        formData.append("jobs_file", file);
      }
      if (
        selectedScanIds.length > 0 &&
        (sourceMode === "scans" || sourceMode === "combined")
      ) {
        selectedScanIds.forEach((id) => {
          formData.append("scan_ids", id);
        });
      }
      if (runName.trim()) {
        formData.append("run_name", runName.trim());
      }
      if (configPath.trim()) {
        formData.append("config_path", configPath.trim());
      }
      formData.append("triggered_by", "admin");

      const idempotencyKey = generateIdempotencyKey();
      const res = await triggerRun(formData, idempotencyKey);
      onSuccess(res.run_id);
      onClose();
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        if (err.fieldErrors) {
          const mapped: Record<string, string> = {};
          err.fieldErrors.forEach((fe) => {
            mapped[fe.field] = fe.message;
          });
          setFieldErrors(mapped);
        }
        setError(err.message || "Failed to trigger run.");
        setErrorCode(err.code);
        setErrorAction(err.action || null);
        const detailsData = (err.details as any)?.data || (err.details as any);
        if (detailsData?.run_id) {
          onSuccess(detailsData.run_id);
          onClose();
          return;
        }
      } else {
        setError(err.message || "An unexpected error occurred while starting the run.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        title="Trigger New Run"
        description="Configure and launch a pipeline run with an active Candidate Profile and job sources."
        className="new-run-dialog"
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, width: "100%" }}>
            <Button variant="secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSubmit}
              disabled={submitting || loadingProfiles || profiles.length === 0}
            >
              {submitting ? "Triggering..." : "Launch Run"}
            </Button>
          </div>
        }
      >
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {error && (
            <div className="notice error" role="alert">
              <div>{error}</div>
              {(errorAction || errorCode === "local_readiness_required") && (
                <div style={{ marginTop: 6 }}>
                  <RunErrorAction code={errorCode} action={errorAction} />
                </div>
              )}
            </div>
          )}

          {loadingProfiles ? (
            <LoadingState message="Loading candidate profiles..." />
          ) : profiles.length === 0 ? (
            <div className="notice warn" role="alert">
              No active, confirmed Candidate Profiles found. Please create and confirm a Candidate Profile before launching a Run.
            </div>
          ) : (
            <div className="field-group">
              <label htmlFor="run-profile-select" className="field-label">
                Candidate Profile <span className="required-mark">*</span>
              </label>
              <select
                id="run-profile-select"
                className="field-input"
                value={selectedProfileId}
                onChange={(e) => setSelectedProfileId(e.target.value)}
                disabled={submitting}
                style={{ width: "100%", padding: "8px 12px" }}
              >
                {profiles.map((p) => (
                  <option key={p.profile_id} value={p.profile_id}>
                    {p.profile_name || p.profile_id} (Rev {p.revision}) — {p.lifecycle}
                  </option>
                ))}
              </select>
              {fieldErrors.profile_id && (
                <span className="field-error">{fieldErrors.profile_id}</span>
              )}
            </div>
          )}

          <div className="field-group">
            <label className="field-label">Job Input Source</label>
            <div style={{ display: "flex", gap: 16, marginBottom: 8 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                <input
                  type="radio"
                  name="sourceMode"
                  value="upload"
                  checked={sourceMode === "upload"}
                  onChange={() => setSourceMode("upload")}
                  disabled={submitting}
                />
                <span>File Upload</span>
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                <input
                  type="radio"
                  name="sourceMode"
                  value="scans"
                  checked={sourceMode === "scans"}
                  onChange={() => setSourceMode("scans")}
                  disabled={submitting}
                />
                <span>Scan Outputs</span>
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                <input
                  type="radio"
                  name="sourceMode"
                  value="combined"
                  checked={sourceMode === "combined"}
                  onChange={() => setSourceMode("combined")}
                  disabled={submitting}
                />
                <span>Combined (File + Scans)</span>
              </label>
            </div>
          </div>

          {(sourceMode === "upload" || sourceMode === "combined") && (
            <div className="field-group">
              <label htmlFor="run-jobs-file" className="field-label">
                Jobs File (.json or .jsonl) {sourceMode === "upload" && <span className="required-mark">*</span>}
              </label>
              <input
                id="run-jobs-file"
                type="file"
                accept=".json,.jsonl,application/json"
                onChange={handleFileChange}
                disabled={submitting}
                className="field-input"
                style={{ width: "100%" }}
              />
              <span className="field-hint">
                Non-empty UTF-8 JSON array or JSONL file up to 50 MB.
              </span>
              {fieldErrors.jobs_file && (
                <span className="field-error">{fieldErrors.jobs_file}</span>
              )}
            </div>
          )}

          {(sourceMode === "scans" || sourceMode === "combined") && (
            <div className="field-group">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <label className="field-label" style={{ margin: 0 }}>
                  Selected Scans ({selectedScanIds.length}) {sourceMode === "scans" && <span className="required-mark">*</span>}
                </label>
                <Button
                  type="button"
                  size="compact"
                  variant="secondary"
                  onClick={() => setIsScanPickerOpen(true)}
                  disabled={submitting}
                >
                  {selectedScanIds.length > 0 ? "Edit Selected Scans" : "Choose Scans"}
                </Button>
              </div>
              {selectedScanIds.length > 0 ? (
                <div
                  style={{
                    padding: "8px 12px",
                    background: "var(--surface-2)",
                    borderRadius: "var(--radius-sm)",
                    fontSize: 13,
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 6,
                  }}
                >
                  {selectedScanIds.map((id) => (
                    <span
                      key={id}
                      style={{
                        background: "var(--surface)",
                        border: "1px solid var(--border)",
                        borderRadius: "var(--radius-sm)",
                        padding: "2px 8px",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      {id}
                      <button
                        type="button"
                        onClick={() =>
                          setSelectedScanIds((prev) => prev.filter((item) => item !== id))
                        }
                        style={{
                          border: "none",
                          background: "transparent",
                          cursor: "pointer",
                          padding: 0,
                          fontSize: 14,
                          lineHeight: 1,
                          color: "var(--muted)",
                        }}
                        aria-label={`Remove scan ${id}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              ) : (
                <span className="field-hint">
                  No Scans selected. Choose one or more succeeded Scans with usable outputs.
                </span>
              )}
              {fieldErrors.scan_ids && (
                <span className="field-error">{fieldErrors.scan_ids}</span>
              )}
            </div>
          )}

          <Field
            label="Run Name"
            placeholder="Defaults to input source name"
            value={runName}
            onChange={(e) => setRunName(e.target.value)}
            disabled={submitting}
            error={fieldErrors.run_name}
            hint="Optional. 120 characters maximum."
          />

          <Field
            label="Config Path"
            value={configPath}
            onChange={(e) => setConfigPath(e.target.value)}
            disabled={submitting}
            error={fieldErrors.config_path}
            hint="Default .env.yaml."
          />
        </form>
      </Dialog>

      <RunSourceSelectionDialog
        open={isScanPickerOpen}
        onClose={() => setIsScanPickerOpen(false)}
        selectedScanIds={selectedScanIds}
        onApply={(ids) => setSelectedScanIds(ids)}
      />
    </>
  );
};
