import React, { useState, useEffect, useCallback } from "react";
import { apiClient } from "../lib/api-client";
import { Button, LoadingState, ErrorState } from "../components";
import { notificationStore } from "../lib/notifications";
import { PipelineSettingsDialog } from "../features/pipeline-settings/pipeline-settings-dialog";

interface SettingFieldDef {
  key: string;
  label: string;
  description: string;
  type: "number" | "boolean";
  min?: number;
  max?: number;
  step?: number;
  defaultValue: number | boolean;
}

interface SettingSectionDef {
  title: string;
  open: boolean;
  rows: SettingFieldDef[];
}

export function isExplicitOfflineOrMock(explicitFlag?: boolean): boolean {
  if (explicitFlag) return true;
  if (typeof window !== "undefined") {
    if ((window as any).__FITCV_MOCK__ || (window as any).__FITCV_OFFLINE__) return true;
    const search = window.location?.search || "";
    if (search.includes("mock=true") || search.includes("offline=true")) return true;
  }
  return false;
}

const OVERVIEW_SECTIONS: SettingSectionDef[] = [
  {
    title: "Candidate Scope",
    open: true,
    rows: [
      {
        key: "pipeline.vector_search_top_n",
        label: "Initial Candidate Pool Size",
        description: "Listings collected before shortlisting begins.",
        type: "number",
        min: 1,
        max: 1000,
        step: 1,
        defaultValue: 100,
      },
      {
        key: "pipeline.ai_score_top_n",
        label: "AI Reranking Pool Size",
        description: "Top screened listings sent for deeper AI ranking.",
        type: "number",
        min: 1,
        max: 500,
        step: 1,
        defaultValue: 40,
      },
      {
        key: "pipeline.final_top_n",
        label: "Final Output Count",
        description: "Best-fit listings returned when the pipeline finishes.",
        type: "number",
        min: 1,
        max: 100,
        step: 1,
        defaultValue: 10,
      },
      {
        key: "pipeline.evidence_top_k",
        label: "Final Evidence Items Per Job",
        description: "Strongest CV evidence items retained for each final job.",
        type: "number",
        min: 1,
        max: 20,
        step: 1,
        defaultValue: 5,
      },
    ],
  },
  {
    title: "Pre-enrichment Filter",
    open: true,
    rows: [
      {
        key: "global_job_filters.applications_count_max",
        label: "Maximum Applications",
        description: "Skip listings whose visible application count is above this limit.",
        type: "number",
        min: 1,
        max: 10000,
        step: 1,
        defaultValue: 200,
      },
      {
        key: "global_job_filters.max_age_days",
        label: "Maximum Posting Age",
        description: "Only include listings posted within this many days.",
        type: "number",
        min: 1,
        max: 365,
        step: 1,
        defaultValue: 30,
      },
    ],
  },
];

export interface OverviewPageProps {
  allowOfflineFallback?: boolean;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ allowOfflineFallback }) => {
  const [settingsValues, setSettingsValues] = useState<Record<string, any>>({});
  const [revision, setRevision] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [, setSavingKey] = useState<string | null>(null);
  const [isPipelineDialogOpen, setIsPipelineDialogOpen] = useState(false);

  // Load pipeline settings
  const loadSettings = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const res = await apiClient.get<any>("/settings/pipeline");
      const data = res.data?.data || res.data || {};
      const vals = data.values || {};
      setSettingsValues(vals);
      setRevision(data.revision || "");
    } catch (err: any) {
      if (isExplicitOfflineOrMock(allowOfflineFallback)) {
        // If backend not running or explicit mock mode, populate with defaults
        const defaults: Record<string, any> = {};
        OVERVIEW_SECTIONS.forEach((sec) => {
          sec.rows.forEach((r) => {
            defaults[r.key] = r.defaultValue;
          });
        });
        setSettingsValues(defaults);
      } else {
        setLoadError(err?.message || "Failed to load pipeline settings.");
      }
    } finally {
      setLoading(false);
    }
  }, [allowOfflineFallback]);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // Direct field update
  const handleSaveSetting = async (key: string, value: any) => {
    setSavingKey(key);
    setSettingsValues((prev) => ({ ...prev, [key]: value }));
    try {
      const res = await apiClient.patch<any>("/settings/pipeline", {
        changes: { [key]: value },
        expected_revision: revision || undefined,
      });
      const data = res.data?.data || res.data || {};
      if (data.revision) setRevision(data.revision);
      notificationStore.notify({
        dedupe: `overview:saved:${key}`,
        type: "success",
        title: "Setting Saved",
        message: "Setting updated for future pipeline runs.",
      });
    } catch (err: any) {
      notificationStore.notify({
        dedupe: `overview:err:${key}`,
        type: "error",
        title: "Failed to Save",
        message: err.message || "Could not save setting.",
      });
    } finally {
      setSavingKey(null);
    }
  };

  // Restore defaults
  const handleRestoreDefaults = async () => {
    if (typeof window !== "undefined" && typeof window.confirm === "function") {
      if (!window.confirm("Restore defaults for Overview settings?")) return;
    }
    const defaultKeys = OVERVIEW_SECTIONS.flatMap((s) => s.rows.map((r) => r.key));
    const defaultVals: Record<string, any> = {};
    OVERVIEW_SECTIONS.forEach((sec) => {
      sec.rows.forEach((r) => {
        defaultVals[r.key] = r.defaultValue;
      });
    });

    setSettingsValues((prev) => ({ ...prev, ...defaultVals }));
    try {
      const res = await apiClient.post<any>("/settings/pipeline/actions/reset", {
        keys: defaultKeys,
        expected_revision: revision || undefined,
      });
      const data = res.data?.data || res.data || {};
      if (data.revision) setRevision(data.revision);
      notificationStore.notify({
        dedupe: "overview:reset:success",
        type: "success",
        title: "Defaults Restored",
        message: "Pipeline Overview defaults restored.",
      });
    } catch (err: any) {
      notificationStore.notify({
        dedupe: "overview:reset:info",
        type: "info",
        title: "Defaults Restored Locally",
        message: "Defaults restored.",
      });
    }
  };

  return (
    <div className="content-container" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Page Header */}
      <div className="page-head">
        <div>
          <p className="eyebrow">Pipeline</p>
          <h2>Overview</h2>
          <p>Set the most important pipeline volumes and output limits. Changes apply to future runs.</p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Button variant="primary" onClick={() => setIsPipelineDialogOpen(true)}>
            Pipeline Settings
          </Button>
          <Button variant="secondary" onClick={handleRestoreDefaults}>
            Restore Defaults
          </Button>
        </div>
      </div>

      {/* Before your first run - Onboarding Card */}
      <section className="section-card start-here" aria-labelledby="start-here-title">
        <div className="start-here-head">
          <div>
            <p className="eyebrow">Normal use</p>
            <h3 id="start-here-title">Before your first run</h3>
            <p>Confirm a candidate profile, bring in jobs, and connect a model. Technical tuning below is optional.</p>
          </div>
        </div>
        <ol className="start-here-list">
          <li className="start-here-step">
            <a href="#/candidate-profile">Confirm Candidate Profile</a>
            <span>Review source-backed facts before matching.</span>
          </li>
          <li className="start-here-step">
            <a href="#/scans">Bring in jobs</a>
            <span>Scan supported companies or add job input from Runs.</span>
          </li>
          <li className="start-here-step">
            <a href="#/settings/api-providers">Connect a model</a>
            <span>Validate one provider before AI-assisted stages run.</span>
          </li>
        </ol>
      </section>

      {/* Settings Sections */}
      {loading ? (
        <LoadingState message="Loading pipeline settings..." />
      ) : loadError ? (
        <div style={{ padding: "24px 0" }}>
          <ErrorState
            title="Failed to Load Pipeline Settings"
            message={loadError}
            actionLabel="Retry"
            onRetry={loadSettings}
          />
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {OVERVIEW_SECTIONS.map((section) => (
            <details
              key={section.title}
              className="section-card collapsible-section setting-section"
              open={section.open}
            >
              <summary>
                <span className="section-heading">
                  <strong>{section.title}</strong>
                </span>
              </summary>
              <div className="section-content">
                {section.rows.map((row) => {
                  const rawValue = settingsValues[row.key];
                  const currentValue = rawValue !== undefined ? rawValue : row.defaultValue;
                  const numValue = Number(currentValue);
                  const isInvalid =
                    currentValue === "" ||
                    isNaN(numValue) ||
                    (row.min !== undefined && numValue < row.min) ||
                    (row.max !== undefined && numValue > row.max);

                  const controlId = `overview-setting-${row.key.replace(/\./g, "-")}`;
                  const descId = `${controlId}-desc`;
                  const errorId = `${controlId}-error`;

                  let validationMessage = "";
                  if (isInvalid) {
                    if (currentValue === "" || isNaN(numValue)) {
                      validationMessage = "Please enter a valid number.";
                    } else if (row.min !== undefined && row.max !== undefined) {
                      validationMessage = `Must be between ${row.min} and ${row.max}.`;
                    } else if (row.min !== undefined) {
                      validationMessage = `Must be at least ${row.min}.`;
                    } else if (row.max !== undefined) {
                      validationMessage = `Must be at most ${row.max}.`;
                    }
                  }

                  return (
                    <div key={row.key} className="setting-row">
                      <div>
                        <label htmlFor={controlId}>
                          <strong>{row.label}</strong>
                        </label>
                        <p id={descId}>{row.description}</p>
                      </div>
                      <div style={{ display: "grid", gap: 4, justifyItems: "end" }}>
                        {row.type === "number" && (
                          <input
                            id={controlId}
                            type="number"
                            className={`field${isInvalid ? " is-invalid" : ""}`}
                            min={row.min}
                            max={row.max}
                            step={row.step}
                            value={currentValue}
                            onChange={(e) => {
                              const valStr = e.target.value;
                              setSettingsValues((prev) => ({
                                ...prev,
                                [row.key]: valStr === "" ? "" : Number(valStr),
                              }));
                            }}
                            onBlur={(e) => {
                              const valStr = e.target.value;
                              const v = Number(valStr);
                              if (valStr !== "" && !isNaN(v) && (!row.min || v >= row.min) && (!row.max || v <= row.max)) {
                                handleSaveSetting(row.key, v);
                              }
                            }}
                            aria-label={row.label}
                            aria-invalid={isInvalid ? "true" : "false"}
                            aria-describedby={isInvalid ? `${errorId} ${descId}` : descId}
                            aria-errormessage={isInvalid ? errorId : undefined}
                          />
                        )}
                        {isInvalid && (
                          <span
                            id={errorId}
                            className="field-error"
                            role="alert"
                            style={{ fontSize: 11, color: "var(--danger)" }}
                          >
                            {validationMessage}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </details>
          ))}
        </div>
      )}
      <PipelineSettingsDialog
        open={isPipelineDialogOpen}
        onClose={() => setIsPipelineDialogOpen(false)}
        onSaved={loadSettings}
      />
    </div>
  );
};

export const route = {
  id: "overview",
  path: "#/overview",
  title: "Overview",
  group: "workspace" as const,
  order: 10,
  component: OverviewPage,
};

export default route;
