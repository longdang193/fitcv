import React, { useState, useEffect, useCallback } from "react";
import { Button, StatusBadge, LoadingState, ErrorState } from "../../components";
import { ApiClientError } from "../../lib/api-client";
import { fetchSynonymPolicy, updateSynonymPolicy } from "./api";
import type { SynonymType, SynonymPolicyResource, SynonymPolicyIssue } from "./types";
import { formatDisplayValue, formatSynonymIssueLocation } from "../../lib/format";

type PolicyDraft = {
  baseText: string;
  draftText: string;
  baseRevision: number;
  baseActiveBundleRevisionId: string | null;
};

export interface PolicyEditorProps {
  initialType?: SynonymType;
  onPolicyUpdated?: () => void;
}

const POLICY_TYPES: { id: SynonymType; label: string; description: string }[] = [
  { id: "skills", label: "Skill Synonyms", description: "Normalized mappings for technical & soft skills" },
  { id: "domain", label: "Domain Synonyms", description: "Industry and business domain canonical mappings" },
  { id: "role_family", label: "Role Family Synonyms", description: "Job family and seniority title equivalences" },
];

export const PolicyEditor: React.FC<PolicyEditorProps> = ({
  initialType = "skills",
  onPolicyUpdated,
}) => {
  const [selectedType, setSelectedType] = useState<SynonymType>(initialType);
  const [policy, setPolicy] = useState<SynonymPolicyResource | null>(null);
  const [editorText, setEditorText] = useState<string>("");
  const [draftsByType, setDraftsByType] = useState<Partial<Record<SynonymType, PolicyDraft>>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [conflictError, setConflictError] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showNormalized, setShowNormalized] = useState<boolean>(false);
  const draftsRef = React.useRef(draftsByType);
  const requestRef = React.useRef(0);
  draftsRef.current = draftsByType;

  const loadPolicy = useCallback(async (type: SynonymType, resolveDraft = false) => {
    const requestId = ++requestRef.current;
    setLoading(true);
    setError(null);
    setConflictError(false);
    setFeedback(null);
    try {
      const data = await fetchSynonymPolicy(type);
      if (requestRef.current !== requestId) return;
      const serverText = data.editor_text || "";
      const existingDraft = draftsRef.current[type];
      const isDirty = Boolean(existingDraft && existingDraft.draftText !== existingDraft.baseText);
      const remoteChanged = Boolean(
        existingDraft &&
          (existingDraft.baseRevision !== data.draft_revision || existingDraft.baseText !== serverText)
      );
      const nextDraft =
        resolveDraft || !existingDraft || !isDirty
          ? {
              baseText: serverText,
              draftText: serverText,
              baseRevision: data.draft_revision,
              baseActiveBundleRevisionId: data.active_bundle_revision_id,
            }
          : existingDraft;
      setDraftsByType((previous) => ({ ...previous, [type]: nextDraft }));
      setPolicy(data);
      setEditorText(nextDraft.draftText);
      if (isDirty && remoteChanged && !resolveDraft) {
        setError("Policy changed on the server while this draft was being edited. Reload to discard local edits and use the latest revision.");
      }
    } catch (err: unknown) {
      if (requestRef.current !== requestId) return;
      const msg = err instanceof ApiClientError ? err.message : "Failed to load synonym policy.";
      setError(msg);
    } finally {
      if (requestRef.current === requestId) setLoading(false);
    }
  }, []);

  useEffect(() => {
    setPolicy(null);
    setEditorText(draftsRef.current[selectedType]?.draftText || "");
    void loadPolicy(selectedType);
    return () => {
      requestRef.current += 1;
    };
  }, [selectedType, loadPolicy]);

  const handleEditorChange = (value: string) => {
    setEditorText(value);
    setDraftsByType((previous) => {
      const current = previous[selectedType];
      if (!current) return previous;
      return { ...previous, [selectedType]: { ...current, draftText: value } };
    });
  };

  const handleSave = async () => {
    if (!policy) return;
    const type = selectedType;
    const draft = draftsRef.current[type];
    if (!draft) return;
    const saveRequestId = ++requestRef.current;
    setSaving(true);
    setError(null);
    setConflictError(false);
    setFeedback(null);

    try {
      const updated = await updateSynonymPolicy(type, {
        editor_text: editorText,
        expected_draft_revision: draft.baseRevision,
        expected_active_bundle_revision_id: draft.baseActiveBundleRevisionId,
      });
      if (requestRef.current !== saveRequestId) return;
      const updatedText = updated.editor_text || "";
      setDraftsByType((previous) => ({
        ...previous,
        [type]: {
          baseText: updatedText,
          draftText: updatedText,
          baseRevision: updated.draft_revision,
          baseActiveBundleRevisionId: updated.active_bundle_revision_id,
        },
      }));
      setPolicy(updated);
      setEditorText(updatedText);
      setFeedback(`Policy activated successfully (Draft rev ${updated.draft_revision}).`);
      if (onPolicyUpdated) {
        onPolicyUpdated();
      }
    } catch (err: unknown) {
      if (requestRef.current !== saveRequestId) return;
      if (err instanceof ApiClientError) {
        if (err.status === 409 || err.code === "revision_conflict") {
          setConflictError(true);
          setError("Revision conflict: Synonym policy was modified by another session. Please reload to review current state.");
        } else if (err.status === 422) {
          setError(err.message || "Policy validation failed.");
          const details = err.details as { issues?: SynonymPolicyIssue[]; data?: { issues?: SynonymPolicyIssue[] } } | undefined;
          const issues = details?.issues ?? details?.data?.issues;
          if (Array.isArray(issues)) {
            setPolicy((prev) =>
              prev
                ? {
                    ...prev,
                    issues,
                    validation_status: "invalid",
                  }
                : prev
            );
          }
        } else {
          setError(err.message);
        }
      } else {
        setError("Failed to save synonym policy.");
      }
    } finally {
      setSaving(false);
    }
  };

  const currentDraft = draftsByType[selectedType];
  const isDirty = Boolean(currentDraft && currentDraft.draftText !== currentDraft.baseText);
  const mappingCount = policy?.normalized_policy ? Object.keys(policy.normalized_policy).length : 0;

  return (
    <div className="synonym-policy-editor" style={{ display: "grid", gap: 20 }}>
      {/* Type selection tabs */}
      <div className="policy-type-selector" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {POLICY_TYPES.map((t) => {
          const isSelected = t.id === selectedType;
          return (
            <button
              key={t.id}
              type="button"
              className={`btn ${isSelected ? "btn-primary" : "btn-secondary"}`}
              onClick={() => setSelectedType(t.id)}
              aria-pressed={isSelected}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {loading && !policy ? (
        <LoadingState message={`Loading ${selectedType} synonym policy...`} />
      ) : error && !policy ? (
        <ErrorState
          title="Policy Load Error"
          message={error}
          actionLabel="Retry"
          onRetry={() => loadPolicy(selectedType)}
        />
      ) : policy ? (
        <div style={{ display: "grid", gap: 16 }}>
          {loading && <div role="status" style={{ color: "var(--muted)", fontSize: 13 }}>Refreshing {selectedType} synonym policy...</div>}
          {/* Status Bar */}
          <div
            className="table-card"
            style={{
              padding: "16px 20px",
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <StatusBadge
                status={policy.validation_status === "valid" ? "success" : "danger"}
                label={policy.validation_status === "valid" ? "Valid" : "Invalid"}
              />
              <span style={{ fontSize: 13, color: "var(--muted)" }}>
                Draft Rev: <strong>{policy.draft_revision}</strong>
              </span>
              <span style={{ fontSize: 13, color: "var(--muted)" }}>
                Active Bundle: <strong>{policy.active_bundle_revision_id ? `v${policy.active_bundle_revision}` : "None"}</strong>
              </span>
              <span style={{ fontSize: 13, color: "var(--muted)" }}>
                Mappings: <strong>{mappingCount}</strong>
              </span>
              <StatusBadge
                status={
                  policy.mirror_status === "in_sync"
                    ? "neutral"
                    : policy.mirror_status === "repair_required"
                    ? "warn"
                    : "danger"
                }
                label={`Mirror: ${formatDisplayValue(policy.mirror_status, "Unknown")}`}
              />
              {policy.mirror_status === "repair_failed" && policy.mirror_error_code && (
                <span style={{ fontSize: 12, color: "var(--danger, #dc2626)", fontFamily: "monospace" }}>
                  [{policy.mirror_error_code}]
                </span>
              )}
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <Button
                variant="secondary"
                size="compact"
                onClick={() => loadPolicy(selectedType, true)}
                disabled={saving}
              >
                Reload
              </Button>
              <Button
                variant="primary"
                size="compact"
                onClick={handleSave}
                loading={saving}
                disabled={saving || !isDirty}
              >
                {isDirty ? "Save & Activate" : "Saved"}
              </Button>
            </div>
          </div>

          {/* Feedback or Alerts */}
          {feedback && (
            <div
              role="status"
              style={{
                padding: "10px 16px",
                borderRadius: "var(--radius)",
                backgroundColor: "rgba(34, 197, 94, 0.1)",
                color: "var(--success, #16a34a)",
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              {feedback}
            </div>
          )}

          {error && (
            <div
              role="alert"
              style={{
                padding: "10px 16px",
                borderRadius: "var(--radius)",
                backgroundColor: "rgba(239, 68, 68, 0.1)",
                color: "var(--danger, #dc2626)",
                fontSize: 13,
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 4 }}>Error</div>
              <div>{error}</div>
              {conflictError && (
                <div style={{ marginTop: 8 }}>
                  <Button size="compact" variant="secondary" onClick={() => loadPolicy(selectedType, true)}>
                    Reload Latest Policy
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Validation Issues Alert */}
          {policy.issues && policy.issues.length > 0 && (
            <div
              className="table-card"
              role="alert"
              style={{
                padding: 16,
                borderColor: "var(--danger-soft, #fca5a5)",
                backgroundColor: "var(--surface)",
              }}
            >
              <h4 style={{ margin: "0 0 8px", color: "var(--danger, #dc2626)", fontSize: 14 }}>
                Validation Issues ({policy.issues.length})
              </h4>
              <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, display: "grid", gap: 6 }}>
                {policy.issues.map((issue: SynonymPolicyIssue, idx: number) => (
                  <li key={idx}>
                    <strong>{formatSynonymIssueLocation(issue.lines)}:</strong> [{issue.code}] {issue.message}
                    {issue.aliases && issue.aliases.length > 0 && (
                      <span style={{ color: "var(--muted)", marginLeft: 6 }}>
                        (aliases: {issue.aliases.join(", ")})
                      </span>
                    )}
                    {issue.canonicals && issue.canonicals.length > 0 && (
                      <span style={{ color: "var(--muted)", marginLeft: 6 }}>
                        (canonicals: {issue.canonicals.join(", ")})
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Textarea Editor */}
          <div className="table-card" style={{ padding: 16, display: "grid", gap: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <label htmlFor="synonym-policy-textarea" style={{ fontSize: 13, fontWeight: 600 }}>
                Policy Definitions (Format: <code>alias: canonical</code>)
              </label>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>
                {editorText.split("\n").length} lines
              </span>
            </div>
            <textarea
              id="synonym-policy-textarea"
              value={editorText}
              onChange={(e) => handleEditorChange(e.target.value)}
              rows={16}
              spellCheck={false}
              style={{
                width: "100%",
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                fontSize: 13,
                lineHeight: 1.5,
                padding: "12px 14px",
                borderRadius: "var(--radius)",
                border: "1px solid var(--border)",
                backgroundColor: "var(--surface)",
                color: "var(--text)",
                resize: "vertical",
                boxSizing: "border-box",
              }}
              placeholder={`# ${selectedType} synonym mappings\nalias: canonical`}
            />
          </div>

          {/* Normalized Policy Toggle / Preview */}
          <div className="table-card" style={{ padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h4 style={{ margin: 0, fontSize: 14 }}>Compiled Mappings Dictionary</h4>
                <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>
                  Normalized key-value pairs stored in active bundle
                </p>
              </div>
              <Button
                variant="subtle"
                size="compact"
                onClick={() => setShowNormalized(!showNormalized)}
              >
                {showNormalized ? "Hide Dictionary" : `View Dictionary (${mappingCount})`}
              </Button>
            </div>

            {showNormalized && (
              <div style={{ marginTop: 12, maxHeight: 300, overflowY: "auto" }}>
                {mappingCount === 0 ? (
                  <p style={{ fontSize: 13, color: "var(--muted)", margin: 0 }}>No compiled mappings.</p>
                ) : (
                  <table className="data-table" style={{ width: "100%", fontSize: 13 }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: "left", padding: "6px 10px" }}>Alias (Normalized)</th>
                        <th style={{ textAlign: "left", padding: "6px 10px" }}>Canonical Term</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(policy.normalized_policy || {}).map(([alias, canonical]) => (
                        <tr key={alias}>
                          <td style={{ padding: "6px 10px", fontFamily: "monospace" }}>{alias}</td>
                          <td style={{ padding: "6px 10px", fontFamily: "monospace", fontWeight: 600 }}>
                            {canonical}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default PolicyEditor;
