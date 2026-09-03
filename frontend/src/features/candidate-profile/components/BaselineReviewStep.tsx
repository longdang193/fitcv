import React, { useEffect, useState, useCallback } from "react";
import { Button, LoadingState, ErrorState, LiveStatus } from "../../../components";
import {
  fetchBaselineReview,
  fetchCreationAttempt,
  fetchFieldSchema,
  patchBaselineReview,
  regenerateBaselineReview,
  undoBaselineRegeneration,
  approveBaselineReview,
  waitForAttemptTransition,
} from "../api";
import {
  CandidateProfileReviewOperation,
  CreationAttempt,
  FieldSchema,
  ReviewResource,
} from "../types";
import { SourceDialog } from "./SourceDialog";
import { getCandidateProfileFailurePresentation } from "./ProcessingStep";

export interface BaselineReviewStepProps {
  attemptId: string;
  onApproveSuccess: (attempt: CreationAttempt) => void;
  onSaveAndExit: () => void;
}

function generateRandomId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).substring(2, 9)}`;
}

export const BaselineReviewStep: React.FC<BaselineReviewStepProps> = ({
  attemptId,
  onApproveSuccess,
  onSaveAndExit,
}) => {
  const [schema, setSchema] = useState<FieldSchema | null>(null);
  const [review, setReview] = useState<ReviewResource | null>(null);
  const [document, setDocument] = useState<Record<string, any>>({});
  const [pendingOps, setPendingOps] = useState<Map<string, CandidateProfileReviewOperation>>(new Map());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [staleError, setStaleError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("Review baseline extracted facts.");

  // Source Dialog state
  const [sourceDialogOpen, setSourceDialogOpen] = useState(false);
  const [activeSourceBlockId, setActiveSourceBlockId] = useState<string | undefined>();
  const [activeSourceTitle, setActiveSourceTitle] = useState("");
  const [activeReviewedValue, setActiveReviewedValue] = useState("");

  const reconciliationKey = `fitcv_recon_baseline_${attemptId}`;

  // Load review & schema
  const loadReview = useCallback(async () => {
    setLoading(true);
    setError(null);
    setStaleError(null);
    try {
      const [schemaData, attemptData] = await Promise.all([
        fetchFieldSchema(),
        fetchCreationAttempt(attemptId),
      ]);
      setSchema(schemaData);

      let currentAttempt = attemptData;
      if (
        currentAttempt.creation_status === "base_mapping" ||
        currentAttempt.creation_status === "extracting_base" ||
        currentAttempt.next_action === "wait"
      ) {
        setStatusMessage("Extracting baseline facts...");
        currentAttempt = await waitForAttemptTransition(attemptId, ["review_baseline", "review_derived", "confirm"]);
      }

      if (currentAttempt.creation_status === "derived_review" || currentAttempt.next_action === "review_derived") {
        onApproveSuccess(currentAttempt);
        return;
      }

      const reviewData = await fetchBaselineReview(attemptId);
      setReview(reviewData);
      setDocument(reviewData.document || {});
      setLoading(false);
      setStatusMessage("Baseline facts loaded.");
    } catch (err: any) {
      setError(err.message || "Failed to load baseline review.");
      setLoading(false);
    }
  }, [attemptId, onApproveSuccess]);

  useEffect(() => {
    loadReview();
  }, [loadReview]);

  // Queue an operation
  const queueOperation = (op: CandidateProfileReviewOperation) => {
    setPendingOps((prev) => {
      const next = new Map(prev);
      next.set(op.path, op);
      return next;
    });
  };

  // Helper to update scalar field
  const handleFieldChange = (path: string, value: any) => {
    const segments = path.split("/").filter(Boolean);
    setDocument((prev) => {
      const doc = JSON.parse(JSON.stringify(prev));
      let current: any = doc;
      for (let i = 0; i < segments.length - 1; i++) {
        const seg = segments[i];
        if (Array.isArray(current)) {
          current = current.find((item: any) => item.id === seg) || current[Number(seg)];
        } else {
          if (!current[seg]) current[seg] = {};
          current = current[seg];
        }
      }
      const last = segments[segments.length - 1];
      if (Array.isArray(current)) {
        const item = current.find((it: any) => it.id === last);
        if (item) Object.assign(item, value);
      } else {
        current[last] = value;
      }
      return doc;
    });

    queueOperation({ operation: "replace", path, value });
  };

  // Helper to add item to collection
  const handleAddItem = (sectionId: string, itemMeta: Record<string, any>) => {
    const newId = generateRandomId(sectionId.substring(0, 4));
    const newItem: Record<string, any> = { id: newId };

    Object.keys(itemMeta).forEach((k) => {
      if (k === "id") return;
      if (k === "evidence") newItem.evidence = [];
      else if (k === "source_refs") newItem.source_refs = [];
      else newItem[k] = "";
    });

    setDocument((prev) => {
      const doc = JSON.parse(JSON.stringify(prev));
      if (!Array.isArray(doc[sectionId])) doc[sectionId] = [];
      doc[sectionId].push(newItem);
      return doc;
    });

    queueOperation({ operation: "add", path: `/${sectionId}`, value: newItem });
  };

  // Helper to remove item from collection
  const handleRemoveItem = (sectionId: string, itemId: string) => {
    setDocument((prev) => {
      const doc = JSON.parse(JSON.stringify(prev));
      if (Array.isArray(doc[sectionId])) {
        doc[sectionId] = doc[sectionId].filter((item: any) => item.id !== itemId);
      }
      return doc;
    });

    queueOperation({ operation: "remove", path: `/${sectionId}/${itemId}` });
  };

  // Helper to add evidence statement to a collection entry
  const handleAddEvidence = (sectionId: string, itemId: string) => {
    const evId = generateRandomId(`ev_${itemId}`);
    const newEv = {
      id: evId,
      kind: sectionId === "experiences" ? "work_experience" : sectionId === "education" ? "education" : "project",
      title: "",
      text: "",
      source_refs: [],
    };

    setDocument((prev) => {
      const doc = JSON.parse(JSON.stringify(prev));
      const parent = doc[sectionId]?.find((it: any) => it.id === itemId);
      if (parent) {
        if (!Array.isArray(parent.evidence)) parent.evidence = [];
        parent.evidence.push(newEv);
      }
      return doc;
    });

    queueOperation({
      operation: "add",
      path: `/${sectionId}/${itemId}/evidence`,
      value: newEv,
    });
  };

  // Helper to remove evidence statement
  const handleRemoveEvidence = (sectionId: string, itemId: string, evId: string) => {
    setDocument((prev) => {
      const doc = JSON.parse(JSON.stringify(prev));
      const parent = doc[sectionId]?.find((it: any) => it.id === itemId);
      if (parent && Array.isArray(parent.evidence)) {
        parent.evidence = parent.evidence.filter((ev: any) => ev.id !== evId);
      }
      return doc;
    });

    queueOperation({
      operation: "remove",
      path: `/${sectionId}/${itemId}/evidence/${evId}`,
    });
  };

  // Flush queued operations to server
  const flushOperations = async (): Promise<ReviewResource | null> => {
    if (pendingOps.size === 0 || !review) return review;

    setSaving(true);
    setError(null);
    setStatusMessage("Saving draft changes...");

    const ops = Array.from(pendingOps.values());
    try {
      const updated = await patchBaselineReview(attemptId, review.revision, ops);
      setReview(updated);
      setDocument(updated.document || {});
      setPendingOps(new Map());
      setSaving(false);
      setStatusMessage("Changes saved successfully.");
      try {
        sessionStorage.removeItem(reconciliationKey);
      } catch {}
      return updated;
    } catch (err: any) {
      setSaving(false);
      if (err.code === "candidate_profile_revision_conflict" || err.code === "candidate_profile_fingerprint_conflict") {
        try {
          sessionStorage.setItem(reconciliationKey, JSON.stringify(ops));
        } catch {}
        setStaleError("Review draft updated on server. Reload latest draft to reapply your unsaved changes.");
      } else {
        setError(err.message || "Failed to save draft changes.");
      }
      throw err;
    }
  };

  // Reapply stored unsaved operations after reload
  const reapplyUnsavedEdits = async () => {
    setSaving(true);
    setError(null);
    try {
      const freshReview = await fetchBaselineReview(attemptId);
      setReview(freshReview);
      setDocument(freshReview.document || {});

      let ops = Array.from(pendingOps.values());
      const stored = sessionStorage.getItem(reconciliationKey);
      if (stored && ops.length === 0) {
        ops = JSON.parse(stored);
      }

      if (ops.length === 0) {
        setStaleError(null);
        setSaving(false);
        return;
      }

      const updated = await patchBaselineReview(attemptId, freshReview.revision, ops);
      setReview(updated);
      setDocument(updated.document || {});
      setPendingOps(new Map());
      setStaleError(null);
      try {
        sessionStorage.removeItem(reconciliationKey);
      } catch {}
      setStatusMessage("Unsaved edits successfully reapplied and saved.");
    } catch (e: any) {
      if (e.status === 409 || e.code === "candidate_profile_revision_conflict" || e.code === "candidate_profile_fingerprint_conflict") {
        setStaleError("Conflict persists on server. Reload latest draft to inspect recent changes.");
      } else {
        setError("Failed to reapply unsaved changes: " + e.message);
      }
    } finally {
      setSaving(false);
    }
  };

  // Regenerate target or all
  const handleRegenerate = async (target: string = "*") => {
    if (!review) return;
    setSaving(true);
    setError(null);
    setStatusMessage(`Regenerating AI-assisted fields (${target})...`);

    try {
      await regenerateBaselineReview(attemptId, review.revision, [target]);
      const attempt = await waitForAttemptTransition(attemptId, "review_baseline");
      if (attempt.creation_status === "failed") {
        throw new Error(getCandidateProfileFailurePresentation(attempt.failure).message);
      }
      await loadReview();
      setStatusMessage("Regeneration complete.");
    } catch (err: any) {
      setError([err.message, err.action].filter(Boolean).join(" ") || "Regeneration failed.");
    } finally {
      setSaving(false);
    }
  };

  // Undo regeneration
  const handleUndo = async () => {
    if (!review) return;
    setSaving(true);
    setError(null);
    setStatusMessage("Undoing regeneration...");

    try {
      const restored = await undoBaselineRegeneration(attemptId, review.revision);
      setReview(restored);
      setDocument(restored.document || {});
      setPendingOps(new Map());
      setSaving(false);
      setStatusMessage("Regeneration undone.");
    } catch (err: any) {
      setError(err.message || "Failed to undo regeneration.");
      setSaving(false);
    }
  };

  // Approve baseline
  const handleApprove = async () => {
    if (!review) return;
    setApproving(true);
    setError(null);
    setStatusMessage("Flushing changes and approving baseline evidence...");

    try {
      let currentReview = review;
      if (pendingOps.size > 0) {
        const updated = await flushOperations();
        if (updated) currentReview = updated;
      }

      const attempt = await approveBaselineReview(attemptId, currentReview.revision, currentReview.fingerprint);
      setStatusMessage("Baseline approved! Moving to controlled derivation...");
      onApproveSuccess(attempt);
    } catch (err: any) {
      setApproving(false);
      setError(err.message || "Failed to approve baseline review.");
    }
  };

  const handleSaveAndExit = async () => {
    try {
      if (pendingOps.size > 0) {
        await flushOperations();
      }
      onSaveAndExit();
    } catch {}
  };

  const openSourceDialog = (blockId: string, title: string, value: string) => {
    setActiveSourceBlockId(blockId);
    setActiveSourceTitle(title);
    setActiveReviewedValue(value);
    setSourceDialogOpen(true);
  };

  if (loading) {
    return <LoadingState message="Loading baseline evidence review..." />;
  }

  if (!review || !schema) {
    return <ErrorState message={error || "Failed to load review data."} onRetry={loadReview} />;
  }

  const baselineSections = schema.sections.filter(
    (s) => s.stage === "baseline" && s.id !== "interests" && s.id !== "search_preferences"
  );

  return (
    <div className="baseline-review-container">
      {/* Header toolbar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <button
            type="button"
            className="btn-subtle"
            style={{ fontSize: 13, padding: "4px 8px", cursor: "pointer", border: 0, background: "transparent", color: "var(--muted)" }}
            onClick={handleSaveAndExit}
          >
            ← Save and exit to Candidate Profiles
          </button>
          <div style={{ marginTop: 4 }}>
            <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--accent)" }}>
              Step 2 · Evidence review
            </span>
            <h2 style={{ margin: "4px 0", fontSize: 22, fontFamily: "var(--display-font)" }}>
              Review baseline facts
            </h2>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
              Review extracted statements and citations. AI controls appear only where context supports inference.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {review.capabilities.regenerate_all && (
            <Button size="compact" onClick={() => handleRegenerate("*")} loading={saving} disabled={saving || approving}>
              ✨ Regenerate AI fields
            </Button>
          )}
          {review.capabilities.undo_regeneration && (
            <Button size="compact" onClick={handleUndo} disabled={saving || approving}>
              Undo regeneration
            </Button>
          )}
          {pendingOps.size > 0 && (
            <Button size="compact" variant="secondary" onClick={() => flushOperations()} loading={saving}>
              Save draft ({pendingOps.size})
            </Button>
          )}
          <Button
            variant="primary"
            onClick={handleApprove}
            loading={approving}
            disabled={saving || approving || Boolean(staleError)}
          >
            Approve baseline and continue
          </Button>
        </div>
      </div>

      {staleError && (
        <div
          role="alert"
          style={{
            padding: "12px 16px",
            marginBottom: 20,
            background: "var(--warn-soft)",
            border: "1px solid var(--warn)",
            borderRadius: "var(--radius-md)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <strong style={{ color: "var(--warn)", display: "block" }}>Draft Changed on Server</strong>
            <span style={{ fontSize: 13 }}>{staleError}</span>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <Button size="compact" variant="secondary" onClick={loadReview}>
              Reload latest
            </Button>
            <Button size="compact" variant="primary" onClick={reapplyUnsavedEdits}>
              Reapply unsaved edits
            </Button>
          </div>
        </div>
      )}

      {error && (
        <div
          role="alert"
          style={{
            padding: "12px 16px",
            marginBottom: 20,
            background: "var(--danger-soft)",
            color: "var(--danger)",
            borderRadius: "var(--radius-md)",
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          {error}
        </div>
      )}

      <LiveStatus message={statusMessage} />

      {/* Review Sections */}
      <div style={{ display: "flex", flexDirection: "column", gap: 24, marginTop: 16 }}>
        {baselineSections.map((section) => (
          <section
            key={section.id}
            className="table-card"
            style={{ padding: 24 }}
            aria-labelledby={`section-${section.id}-heading`}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 16,
                borderBottom: "1px solid var(--border-soft)",
                paddingBottom: 12,
              }}
            >
              <div>
                <h3 id={`section-${section.id}-heading`} style={{ margin: 0, fontSize: 16 }}>
                  {section.label}
                </h3>
                {section.description && (
                  <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--muted)" }}>
                    {section.description}
                  </p>
                )}
              </div>

              {section.shape === "collection" && (
                <Button
                  size="compact"
                  onClick={() => handleAddItem(section.id, section.item || {})}
                >
                  + Add {section.item_label || section.label}
                </Button>
              )}
            </div>

            {/* Object Section (Identity / Contact) */}
            {section.shape === "object" && section.fields && (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                  gap: 16,
                }}
              >
                {Object.entries(section.fields).map(([fieldName, fieldMeta]) => {
                  const path = `/${fieldName === "name" || fieldName === "headline" || fieldName === "summary" ? fieldName : `${section.id}/${fieldName}`}`;
                  const annotation = review.annotations[path] || {};
                  const value = fieldName === "name" || fieldName === "headline" || fieldName === "summary"
                    ? document[fieldName] || ""
                    : document[section.id]?.[fieldName] || "";

                  return (
                    <div key={fieldName} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <label style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
                          {fieldMeta.label}
                          {fieldMeta.required && <span style={{ color: "var(--accent)" }}> *</span>}
                        </label>
                        <div style={{ display: "flex", gap: 6 }}>
                          {annotation.source_block_ids && annotation.source_block_ids.length > 0 && (
                            <button
                              type="button"
                              className="btn-subtle"
                              style={{ fontSize: 11, padding: "2px 6px", cursor: "pointer", color: "var(--accent)" }}
                              onClick={() =>
                                openSourceDialog(
                                  annotation.source_block_ids![0],
                                  fieldMeta.label,
                                  String(value)
                                )
                              }
                            >
                              Source
                            </button>
                          )}
                          {annotation.regenerable && (
                            <button
                              type="button"
                              className="btn-subtle"
                              style={{ fontSize: 11, padding: "2px 6px", cursor: "pointer" }}
                              onClick={() => handleRegenerate(path)}
                              title={`Regenerate ${fieldMeta.label}`}
                            >
                              ✨
                            </button>
                          )}
                        </div>
                      </div>

                      {fieldMeta.shape === "textarea" ? (
                        <textarea
                          className="field-textarea"
                          value={value}
                          rows={3}
                          onChange={(e) => handleFieldChange(path, e.target.value)}
                        />
                      ) : (
                        <input
                          className="field-input"
                          type="text"
                          value={value}
                          onChange={(e) => handleFieldChange(path, e.target.value)}
                        />
                      )}
                      {fieldMeta.description && (
                        <span style={{ fontSize: 11, color: "var(--muted)" }}>{fieldMeta.description}</span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Collection Section (Experiences, Education, Projects, etc.) */}
            {section.shape === "collection" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                {(!document[section.id] || document[section.id].length === 0) && (
                  <p style={{ margin: 0, color: "var(--muted)", fontSize: 13, fontStyle: "italic" }}>
                    No {section.label.toLowerCase()} entries extracted. Click &quot;Add {section.item_label || section.label}&quot; to add one.
                  </p>
                )}

                {(document[section.id] || []).map((item: any, idx: number) => {
                  const itemId = item.id || `item_${idx}`;
                  const itemPath = `/${section.id}/${itemId}`;

                  return (
                    <article
                      key={itemId}
                      style={{
                        padding: 16,
                        border: "1px solid var(--border)",
                        borderRadius: "var(--radius-md)",
                        background: "var(--surface)",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          marginBottom: 12,
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <strong>
                            {section.item_label || section.label} #{idx + 1}
                          </strong>
                          <code style={{ fontSize: 11, color: "var(--muted)" }}>{itemId}</code>
                        </div>
                        <Button
                          size="compact"
                          variant="danger"
                          onClick={() => handleRemoveItem(section.id, itemId)}
                        >
                          Remove
                        </Button>
                      </div>

                      {/* Parent Item Fields */}
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                          gap: 12,
                          marginBottom: 16,
                        }}
                      >
                        {Object.entries(section.item || {}).map(([fName, fMeta]) => {
                          if (fName === "id" || fName === "evidence" || fName === "source_refs") return null;
                          const fieldPath = `${itemPath}/${fName}`;
                          const fVal = item[fName] || "";
                          const fAnnotation = review.annotations[fieldPath] || {};

                          return (
                            <div key={fName} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <label style={{ fontSize: 12, fontWeight: 600 }}>
                                  {fMeta.label}
                                  {fMeta.required && <span style={{ color: "var(--accent)" }}> *</span>}
                                </label>
                                {fAnnotation.source_block_ids && fAnnotation.source_block_ids.length > 0 && (
                                  <button
                                    type="button"
                                    className="btn-subtle"
                                    style={{ fontSize: 11, padding: "2px 4px", cursor: "pointer", color: "var(--accent)" }}
                                    onClick={() =>
                                      openSourceDialog(
                                        fAnnotation.source_block_ids![0],
                                        fMeta.label,
                                        String(fVal)
                                      )
                                    }
                                  >
                                    Source
                                  </button>
                                )}
                              </div>
                              <input
                                className="field-input"
                                type="text"
                                value={fVal}
                                onChange={(e) => handleFieldChange(fieldPath, e.target.value)}
                              />
                            </div>
                          );
                        })}
                      </div>

                      {/* Evidence Collection inside item */}
                      {section.item?.evidence && (
                        <div
                          style={{
                            borderTop: "1px solid var(--border-soft)",
                            paddingTop: 12,
                            marginTop: 12,
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              marginBottom: 8,
                            }}
                          >
                            <span style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
                              Evidence Statements ({item.evidence?.length || 0})
                            </span>
                            <Button
                              size="compact"
                              onClick={() => handleAddEvidence(section.id, itemId)}
                            >
                              + Add Evidence Statement
                            </Button>
                          </div>

                          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                            {(!item.evidence || item.evidence.length === 0) && (
                              <span style={{ fontSize: 12, color: "var(--muted)", fontStyle: "italic" }}>
                                No evidence statements for this entry.
                              </span>
                            )}
                            {(item.evidence || []).map((ev: any, evIdx: number) => {
                              const evPath = `${itemPath}/evidence/${ev.id}`;
                              const evAnnotation = review.annotations[`${evPath}/text`] || {};

                              return (
                                <div
                                  key={ev.id}
                                  style={{
                                    padding: 10,
                                    background: "var(--surface-2)",
                                    borderRadius: "var(--radius-sm)",
                                    border: "1px solid var(--border-soft)",
                                  }}
                                >
                                  <div
                                    style={{
                                      display: "flex",
                                      justifyContent: "space-between",
                                      alignItems: "center",
                                      marginBottom: 6,
                                    }}
                                  >
                                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                                      <span style={{ fontSize: 12, fontWeight: 600 }}>
                                        Evidence #{evIdx + 1}
                                      </span>
                                      <code style={{ fontSize: 11, color: "var(--accent)" }}>{ev.id}</code>
                                    </div>
                                    <div style={{ display: "flex", gap: 6 }}>
                                      {evAnnotation.source_block_ids && evAnnotation.source_block_ids.length > 0 && (
                                        <button
                                          type="button"
                                          className="btn-subtle"
                                          style={{ fontSize: 11, padding: "2px 6px", cursor: "pointer", color: "var(--accent)" }}
                                          onClick={() =>
                                            openSourceDialog(
                                              evAnnotation.source_block_ids![0],
                                              `Evidence ${ev.id}`,
                                              ev.text || ""
                                            )
                                          }
                                        >
                                          Source
                                        </button>
                                      )}
                                      <button
                                        type="button"
                                        className="btn-subtle"
                                        style={{ fontSize: 11, padding: "2px 6px", cursor: "pointer", color: "var(--danger)" }}
                                        onClick={() => handleRemoveEvidence(section.id, itemId, ev.id)}
                                      >
                                        Remove
                                      </button>
                                    </div>
                                  </div>

                                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                    <input
                                      className="field-input"
                                      type="text"
                                      placeholder="Optional Title / Label"
                                      value={ev.title || ""}
                                      onChange={(e) => handleFieldChange(`${evPath}/title`, e.target.value)}
                                      style={{ minHeight: 30, fontSize: 12 }}
                                    />
                                    <textarea
                                      className="field-textarea"
                                      placeholder="Traceable evidence statement verbatim or normalized from source"
                                      title={ev.text || ""}
                                      value={ev.text || ""}
                                      rows={2}
                                      onChange={(e) => handleFieldChange(`${evPath}/text`, e.target.value)}
                                      style={{ minHeight: 50, fontSize: 12 }}
                                    />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        ))}
      </div>

      {/* Bottom Actions */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 28,
          paddingTop: 16,
          borderTop: "1px solid var(--border-soft)",
        }}
      >
        <Button variant="secondary" onClick={handleSaveAndExit}>
          Save and exit
        </Button>
        <Button
          variant="primary"
          onClick={handleApprove}
          loading={approving}
          disabled={saving || approving || Boolean(staleError)}
        >
          Approve baseline and continue →
        </Button>
      </div>

      {/* Source Dialog */}
      <SourceDialog
        open={sourceDialogOpen}
        onClose={() => setSourceDialogOpen(false)}
        attemptId={attemptId}
        title={`Source citation: ${activeSourceTitle}`}
        sourceBlockId={activeSourceBlockId}
        reviewedValue={activeReviewedValue}
      />
    </div>
  );
};
