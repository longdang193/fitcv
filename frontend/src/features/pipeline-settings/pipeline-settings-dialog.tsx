export { PIPELINE_SECTIONS } from "./sections-def";
import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { Button, LoadingState, ErrorState } from "../../components";
import { apiClient } from "../../lib/api-client";
import { notificationStore } from "../../lib/notifications";
import { PipelineSectionId } from "./types";
import { PIPELINE_SECTIONS, buildFallbackDefaults } from "./sections-def";

export interface PipelineSettingsDialogProps {
  open: boolean;
  onClose: () => void;
  onSaved?: (values: Record<string, any>) => void;
  initialSection?: PipelineSectionId;
  allowOfflineFallback?: boolean;
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

export const PipelineSettingsDialog: React.FC<PipelineSettingsDialogProps> = ({
  open,
  onClose,
  onSaved,
  initialSection = "overview",
  allowOfflineFallback,
}) => {
  const [activeSectionId, setActiveSectionId] = useState<PipelineSectionId>(initialSection);
  const [savedValues, setSavedValues] = useState<Record<string, any>>({});
  const [draftValues, setDraftValues] = useState<Record<string, any>>({});
  const [canonicalDefaults, setCanonicalDefaults] = useState<Record<string, any>>(() => buildFallbackDefaults());
  const [revision, setRevision] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflictNotice, setConflictNotice] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);
  const wasOpenRef = useRef(false);
  const isBackdropMouseDownRef = useRef(false);
  const navRef = useRef<HTMLElement>(null);

  const handleNavKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    const isNext = e.key === "ArrowDown" || e.key === "ArrowRight";
    const isPrev = e.key === "ArrowUp" || e.key === "ArrowLeft";
    let nextIndex = -1;

    if (isNext) {
      e.preventDefault();
      nextIndex = (index + 1) % PIPELINE_SECTIONS.length;
    } else if (isPrev) {
      e.preventDefault();
      nextIndex = (index - 1 + PIPELINE_SECTIONS.length) % PIPELINE_SECTIONS.length;
    } else if (e.key === "Home") {
      e.preventDefault();
      nextIndex = 0;
    } else if (e.key === "End") {
      e.preventDefault();
      nextIndex = PIPELINE_SECTIONS.length - 1;
    }

    if (nextIndex !== -1 && navRef.current) {
      const tabs = navRef.current.querySelectorAll<HTMLButtonElement>('[role="tab"]');
      tabs[nextIndex]?.focus();
      setActiveSectionId(PIPELINE_SECTIONS[nextIndex].id);
    }
  };

  useEffect(() => {
    const dialog = dialogRef.current;
    if (open) {
      if (!wasOpenRef.current) {
        triggerRef.current = (document.activeElement as HTMLElement) || null;
        wasOpenRef.current = true;
      }
      if (dialog && !dialog.open) {
        if (typeof dialog.showModal === "function") {
          dialog.showModal();
        } else {
          dialog.setAttribute("open", "");
        }
      }
    } else if (wasOpenRef.current) {
      wasOpenRef.current = false;
      if (dialog && dialog.open) {
        if (typeof dialog.close === "function") {
          dialog.close();
        } else {
          dialog.removeAttribute("open");
        }
      }
      if (triggerRef.current && typeof triggerRef.current.focus === "function") {
        triggerRef.current.focus();
      }
      triggerRef.current = null;
    }
  }, [open]);

  useEffect(() => {
    return () => {
      if (wasOpenRef.current) {
        wasOpenRef.current = false;
        if (triggerRef.current && typeof triggerRef.current.focus === "function") {
          triggerRef.current.focus();
        }
        triggerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleCancel = (e: Event) => {
      e.preventDefault();
      onClose();
    };

    const handleMouseDown = (e: MouseEvent) => {
      if (e.target === dialog) {
        const rect = dialog.getBoundingClientRect();
        const isInDialog =
          rect.top <= e.clientY &&
          e.clientY <= rect.top + rect.height &&
          rect.left <= e.clientX &&
          e.clientX <= rect.left + rect.width;
        isBackdropMouseDownRef.current = !isInDialog;
      } else {
        isBackdropMouseDownRef.current = false;
      }
    };

    const handleClick = (e: MouseEvent) => {
      const wasBackdropMouseDown = isBackdropMouseDownRef.current;
      isBackdropMouseDownRef.current = false;

      if (!wasBackdropMouseDown || e.target !== dialog) {
        return;
      }

      const rect = dialog.getBoundingClientRect();
      const isInDialog =
        rect.top <= e.clientY &&
        e.clientY <= rect.top + rect.height &&
        rect.left <= e.clientX &&
        e.clientX <= rect.left + rect.width;
      if (!isInDialog) {
        onClose();
      }
    };

    dialog.addEventListener("cancel", handleCancel);
    dialog.addEventListener("mousedown", handleMouseDown);
    dialog.addEventListener("click", handleClick);
    return () => {
      dialog.removeEventListener("cancel", handleCancel);
      dialog.removeEventListener("mousedown", handleMouseDown);
      dialog.removeEventListener("click", handleClick);
    };
  }, [open, onClose]);

  const activeSection = useMemo(() => {
    return PIPELINE_SECTIONS.find((s) => s.id === activeSectionId) || PIPELINE_SECTIONS[0];
  }, [activeSectionId]);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    setError(null);
    setConflictNotice(null);
    try {
      const res = await apiClient.get<any>("/settings/pipeline");
      const data = res.data?.data || res.data || {};
      const vals = data.values || {};
      const defs = data.defaults || {};
      const rev = data.revision || "";

      const mergedDefaults = { ...buildFallbackDefaults(), ...defs };
      const initialValues: Record<string, any> = { ...mergedDefaults, ...vals };

      setSavedValues(initialValues);
      setDraftValues(initialValues);
      setCanonicalDefaults(mergedDefaults);
      setRevision(rev);
    } catch (err: any) {
      if (isExplicitOfflineOrMock(allowOfflineFallback)) {
        const fallback = buildFallbackDefaults();
        setSavedValues(fallback);
        setDraftValues(fallback);
        setCanonicalDefaults(fallback);
      } else {
        setLoadError(err?.message || "Failed to load pipeline settings.");
      }
    } finally {
      setLoading(false);
    }
  }, [allowOfflineFallback]);

  useEffect(() => {
    if (open) {
      loadSettings();
      if (initialSection) {
        setActiveSectionId(initialSection);
      }
    }
  }, [open, loadSettings, initialSection]);

  const dirtyChanges = useMemo(() => {
    const changes: Record<string, any> = {};
    for (const section of PIPELINE_SECTIONS) {
      for (const key of section.ownedKeys) {
        if (key === "rule_filter.selected_filters") {
          const savedList: string[] = (savedValues[key] || []).slice().sort();
          const draftList: string[] = (draftValues[key] || []).slice().sort();
          if (JSON.stringify(savedList) !== JSON.stringify(draftList)) {
            changes[key] = draftValues[key];
          }
        } else if (draftValues[key] !== undefined && draftValues[key] !== savedValues[key]) {
          changes[key] = draftValues[key];
        }
      }
    }
    return changes;
  }, [draftValues, savedValues]);

  const dirtyCount = Object.keys(dirtyChanges).length;

  const handleFieldChange = (key: string, value: any) => {
    setDraftValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleMembershipToggle = (key: string, member: string, checked: boolean) => {
    setDraftValues((prev) => {
      const currentList: string[] = Array.isArray(prev[key]) ? [...prev[key]] : [];
      let updated: string[];
      if (checked) {
        updated = currentList.includes(member) ? currentList : [...currentList, member];
      } else {
        updated = currentList.filter((m) => m !== member);
      }
      return { ...prev, [key]: updated };
    });
  };

  const handleRestoreSectionDefaults = () => {
    if (typeof window !== "undefined" && typeof window.confirm === "function") {
      if (!window.confirm(`Restore defaults for ${activeSection.title}?`)) return;
    }
    setDraftValues((prev) => {
      const next = { ...prev };
      for (const key of activeSection.ownedKeys) {
        if (key === "rule_filter.selected_filters") {
          next[key] = canonicalDefaults[key] || [
            "seniority_mismatch",
            "missing_fit_context",
            "location_type_excluded",
            "contract_type_excluded",
            "experience_level_excluded",
          ];
        } else if (canonicalDefaults[key] !== undefined) {
          next[key] = canonicalDefaults[key];
        }
      }
      return next;
    });
  };

  const handleRestoreAllDefaults = () => {
    if (typeof window !== "undefined" && typeof window.confirm === "function") {
      if (!window.confirm("Restore defaults for all Pipeline settings?")) return;
    }
    setDraftValues((prev) => {
      const next = { ...prev };
      for (const section of PIPELINE_SECTIONS) {
        for (const key of section.ownedKeys) {
          if (key === "rule_filter.selected_filters") {
            next[key] = canonicalDefaults[key] || [
              "seniority_mismatch",
              "missing_fit_context",
              "location_type_excluded",
              "contract_type_excluded",
              "experience_level_excluded",
            ];
          } else if (canonicalDefaults[key] !== undefined) {
            next[key] = canonicalDefaults[key];
          }
        }
      }
      return next;
    });
  };

  const handleSave = async () => {
    if (dirtyCount === 0) {
      onClose();
      return;
    }

    setSaving(true);
    setError(null);
    setConflictNotice(null);

    try {
      const res = await apiClient.patch<any>("/settings/pipeline", {
        changes: dirtyChanges,
        expected_revision: revision || undefined,
      });
      const data = res.data?.data || res.data || {};
      const newValues = data.values || { ...draftValues };
      const newRevision = data.revision || revision;

      setSavedValues(newValues);
      setDraftValues(newValues);
      if (newRevision) setRevision(newRevision);

      notificationStore.notify({
        dedupe: "pipeline:settings:saved",
        type: "success",
        title: "Pipeline Settings Saved",
        message: "Pipeline settings updated for future runs.",
      });

      if (onSaved) {
        onSaved(newValues);
      }
      onClose();
    } catch (err: any) {
      if (err.status === 409 || err.code === "settings_revision_conflict") {
        setConflictNotice(
          err.message || "Pipeline settings changed since last read. Reload to view updated settings."
        );
      } else {
        setError(err.message || "Failed to save pipeline settings.");
      }
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  const isSemanticDisabled =
    activeSection.id === "cv-analysis" &&
    draftValues["cv_analysis.semantic_alignment.enabled"] === false;

  return (
    <dialog
      ref={dialogRef}
      className="native-dialog pipeline-settings-dialog"
      aria-labelledby="pipeline-dialog-title"
      aria-describedby="pipeline-dialog-desc"
    >
      <div className="dialog-header pipeline-dialog-header">
        <div>
          <h2 id="pipeline-dialog-title" className="dialog-title">Pipeline Settings</h2>
          <p id="pipeline-dialog-desc" className="dialog-description">
            Configure matching run parameters, stages, and output defaults.
          </p>
        </div>
        <button
          type="button"
          className="dialog-close"
          onClick={onClose}
          aria-label="Close Pipeline Settings dialog"
        >
          ✕
        </button>
      </div>

      <div className="pipeline-settings-body">
        {/* Left sections navigation */}
        <nav
          ref={navRef}
          className="pipeline-settings-nav"
          aria-label="Pipeline settings sections"
          role="tablist"
          aria-orientation="vertical"
        >
          {PIPELINE_SECTIONS.map((sec, idx) => {
            const isSelected = sec.id === activeSectionId;
            return (
              <button
                key={sec.id}
                id={`pipeline-tab-${sec.id}`}
                type="button"
                role="tab"
                className={"pipeline-nav-item" + (isSelected ? " active" : "")}
                aria-selected={isSelected}
                aria-controls={`pipeline-panel-${sec.id}`}
                tabIndex={isSelected ? 0 : -1}
                onClick={() => setActiveSectionId(sec.id)}
                onKeyDown={(e) => handleNavKeyDown(e, idx)}
              >
                {sec.title}
              </button>
            );
          })}
        </nav>

        {/* Right content panel */}
        <div
          id={`pipeline-panel-${activeSectionId}`}
          className="pipeline-settings-content"
          role="tabpanel"
          aria-labelledby={`pipeline-tab-${activeSectionId}`}
          aria-label={activeSection.title}
        >
          {loading ? (
            <div style={{ padding: 40 }}>
              <LoadingState message="Loading settings..." />
            </div>
          ) : loadError ? (
            <div style={{ padding: 40 }}>
              <ErrorState
                title="Failed to Load Settings"
                message={loadError}
                actionLabel="Retry"
                onRetry={loadSettings}
              />
            </div>
          ) : (
            <>
              <div className="section-panel-header">
                <div>
                  <p className="eyebrow">Pipeline Stage</p>
                  <h3>{activeSection.title}</h3>
                  <p>{activeSection.description}</p>
                </div>
                {activeSection.ownedKeys.length > 0 && (
                  <div>
                    <Button
                      variant="secondary"
                      size="compact"
                      onClick={handleRestoreSectionDefaults}
                      aria-label={"Restore Section Defaults for " + activeSection.title}
                    >
                      Restore Section Defaults
                    </Button>
                  </div>
                )}
              </div>

              {conflictNotice && (
                <div className="notice is-warning" role="alert" style={{ margin: "12px 0" }}>
                  <strong>Settings Conflict (409)</strong>
                  <p>{conflictNotice}</p>
                  <Button size="compact" variant="secondary" onClick={loadSettings}>
                    Reload Latest Settings
                  </Button>
                </div>
              )}

              {error && (
                <div className="notice is-error" role="alert" style={{ margin: "12px 0" }}>
                  {error}
                </div>
              )}

              <div className="pipeline-groups-stack">
                {activeSection.groups.map((grp) => {
                  const groupIsDisabled =
                    activeSection.id === "cv-analysis" &&
                    grp.title === "Match Methods" &&
                    isSemanticDisabled;

                  return (
                    <details
                      key={grp.title}
                      className="section-card collapsible-section setting-section"
                      open
                    >
                      <summary>
                        <span className="section-heading">
                          <strong>{grp.title}</strong>
                          {grp.description && <span>{grp.description}</span>}
                        </span>
                      </summary>
                      <div className="section-content">
                        {groupIsDisabled && (
                          <div style={{ padding: "10px 22px", background: "var(--surface-2)", color: "var(--muted)", fontSize: 13 }}>
                            Turn on Semantic Alignment to configure Match Methods.
                          </div>
                        )}
                        {grp.fields.map((field) => {
                          const controlId = "pipeline-setting-" + field.key.replace(/\./g, "-") + (field.member ? "-" + field.member : "");
                          const isMembership = field.type === "membership";
                          const isReadonly = field.type === "readonly";
                          const isBoolean = field.type === "boolean";
                          const isNumber = field.type === "number";

                          const isChecked = isMembership
                            ? (draftValues[field.key] || []).includes(field.member!)
                            : Boolean(draftValues[field.key]);

                          const numVal =
                            draftValues[field.key] !== undefined
                              ? draftValues[field.key]
                              : field.defaultValue ?? "";

                          const isFieldDisabled = groupIsDisabled;

                          return (
                            <div key={controlId} className={"setting-row" + (isFieldDisabled ? " is-disabled" : "")}>
                              <div>
                                <label htmlFor={controlId}>
                                  <strong>{field.label}</strong>
                                </label>
                                <p>{field.description}</p>
                              </div>
                              <div className="control">
                                {isMembership && (
                                  <label className="switch">
                                    <input
                                      id={controlId}
                                      type="checkbox"
                                      checked={isChecked}
                                      disabled={isFieldDisabled}
                                      onChange={(e) =>
                                        handleMembershipToggle(field.key, field.member!, e.target.checked)
                                      }
                                      aria-label={field.label}
                                    />
                                    <span className="track" aria-hidden="true" />
                                  </label>
                                )}

                                {isBoolean && (
                                  <label className="switch">
                                    <input
                                      id={controlId}
                                      type="checkbox"
                                      checked={isChecked}
                                      disabled={isFieldDisabled}
                                      onChange={(e) => handleFieldChange(field.key, e.target.checked)}
                                      aria-label={field.label}
                                    />
                                    <span className="track" aria-hidden="true" />
                                  </label>
                                )}

                                {isNumber && (
                                  <input
                                    id={controlId}
                                    type="number"
                                    className="field"
                                    min={field.min}
                                    max={field.max}
                                    step={field.step}
                                    value={numVal}
                                    disabled={isFieldDisabled}
                                    onChange={(e) => {
                                      const v = parseFloat(e.target.value);
                                      handleFieldChange(field.key, isNaN(v) ? e.target.value : v);
                                    }}
                                    aria-label={field.label}
                                  />
                                )}

                                {isReadonly && (
                                  <span className="mirror-value" id={controlId}>
                                    {field.readonlyValue || draftValues[field.key] || field.defaultValue}
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </details>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="dialog-footer pipeline-dialog-footer">
        <div>
          <Button
            variant="secondary"
            onClick={handleRestoreAllDefaults}
            disabled={loading || saving || Boolean(loadError)}
            aria-label="Restore Defaults for all pipeline settings"
          >
            Restore Defaults
          </Button>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {dirtyCount > 0 && !loadError && (
            <span style={{ fontSize: 13, color: "var(--muted)" }} aria-live="polite">
              {dirtyCount} {dirtyCount === 1 ? "setting" : "settings"} changed
            </span>
          )}
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSave}
            disabled={loading || saving || Boolean(loadError)}
          >
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
      </div>
    </dialog>
  );
};
