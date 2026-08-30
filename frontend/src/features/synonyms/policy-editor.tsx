import React, { useState, useEffect, useCallback } from "react";
import { Button, StatusBadge, LoadingState, ErrorState } from "../../components";
import { ApiClientError } from "../../lib/api-client";
import { fetchSynonymPolicy, updateSynonymPolicy } from "./api";
import type { SynonymType, SynonymPolicyResource, SynonymPolicyIssue } from "./types";

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
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [conflictError, setConflictError] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showNormalized, setShowNormalized] = useState<boolean>(false);

  const loadPolicy = useCallback(async (type: SynonymType) => {
    setLoading(true);
    setError(null);
    setConflictError(false);
    setFeedback(null);
    try {
      const data = await fetchSynonymPolicy(type);
      setPolicy(data);
      setEditorText(data.editor_text || "");
    } catch (err: unknown) {
      const msg = err instanceof ApiClientError ? err.message : "Failed to load synonym policy.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPolicy(selectedType);
  }, [selectedType, loadPolicy]);

  const handleSave = async () => {
    if (!policy) return;
    setSaving(true);
    setError(null);
    setConflictError(false);
    setFeedback(null);

    try {
      const updated = await updateSynonymPolicy(selectedType, {
        editor_text: editorText,
        expected_draft_revision: policy.draft_revision,
        expected_active_bundle_revision_id: policy.active_bundle_revision_id,
      });
      setPolicy(updated);
      setEditorText(updated.editor_text || "");
      setFeedback(`Policy activated successfully (Draft rev ${updated.draft_revision}).`);
      if (onPolicyUpdated) {
        onPolicyUpdated();
      }
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        if (err.status === 409 || err.code === "revision_conflict") {
          setConflictError(true);
          setError("Revision conflict: Synonym policy was modified by another session. Please reload to review current state.");
        } else if (err.status === 422) {
          setError(err.message || "Policy validation failed.");
          if (err.details && typeof err.details === "object" && "issues" in err.details) {
            setPolicy((prev) =>
              prev
                ? {
                    ...prev,
                    issues: (err.details as { issues: SynonymPolicyIssue[] }).issues,
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

  const isDirty = policy ? editorText !== (policy.editor_text || "") : false;
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

      {loading ? (
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
                label={`Mirror: ${policy.mirror_status}`}
              />
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <Button
                variant="secondary"
                size="compact"
                onClick={() => loadPolicy(selectedType)}
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
                  <Button size="compact" variant="secondary" onClick={() => loadPolicy(selectedType)}>
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
                    <strong>Line {issue.lines?.join(", ") || "N/A"}:</strong> [{issue.code}] {issue.message}
                    {issue.aliases && issue.aliases.length > 0 && (
                      <span style={{ color: "var(--muted)", marginLeft: 6 }}>
                        (aliases: {issue.aliases.join(", ")})
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
              onChange={(e) => setEditorText(e.target.value)}
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
