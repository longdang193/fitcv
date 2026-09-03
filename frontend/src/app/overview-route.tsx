import React, { useState, useEffect, useCallback } from "react";
import { apiClient } from "../lib/api-client";
import { Button, LoadingState } from "../components";
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

export const OverviewPage: React.FC = () => {
  const [settingsValues, setSettingsValues] = useState<Record<string, any>>({});
  const [revision, setRevision] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [, setSavingKey] = useState<string | null>(null);
  const [isPipelineDialogOpen, setIsPipelineDialogOpen] = useState(false);

  // Load pipeline settings
  const loadSettings = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<any>("/settings/pipeline");
      const data = res.data?.data || res.data || {};
      const vals = data.values || {};
      setSettingsValues(vals);
      setRevision(data.revision || "");
    } catch (err: any) {
      // If backend not running or mock mode, populate with defaults
      const defaults: Record<string, any> = {};
      OVERVIEW_SECTIONS.forEach((sec) => {
        sec.rows.forEach((r) => {
          defaults[r.key] = r.defaultValue;
        });
      });
      setSettingsValues(defaults);
    } finally {
      setLoading(false);
    }
  }, []);

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
                  const currentValue =
                    settingsValues[row.key] !== undefined
                      ? settingsValues[row.key]
                      : row.defaultValue;
                  return (
                    <div key={row.key} className="setting-row">
                      <div>
                        <strong>{row.label}</strong>
                        <p>{row.description}</p>
                      </div>
                      <div>
                        {row.type === "number" && (
                          <input
                            type="number"
                            className="field"
                            min={row.min}
                            max={row.max}
                            step={row.step}
                            value={currentValue}
                            onChange={(e) => {
                              const v = Number(e.target.value);
                              if (!isNaN(v)) {
                                setSettingsValues((prev) => ({ ...prev, [row.key]: v }));
                              }
                            }}
                            onBlur={(e) => {
                              const v = Number(e.target.value);
                              if (!isNaN(v) && (!row.min || v >= row.min) && (!row.max || v <= row.max)) {
                                handleSaveSetting(row.key, v);
                              }
                            }}
                            aria-label={row.label}
                          />
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
