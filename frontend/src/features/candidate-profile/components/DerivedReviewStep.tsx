import React, { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { Button, LoadingState, ErrorState, StatusBadge } from "../../../components";
import {
  fetchBaselineReview,
  fetchDerivedReview,
  fetchFieldSchema,
  patchDerivedReview,
  regenerateDerivedReview,
  undoDerivedRegeneration,
  approveDerivedReview,
  fetchCreationAttempt,
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
import { EvidenceReferenceButton } from "./EvidenceReferenceButton";
import { ReviewLogConsole } from "./ReviewLogConsole";

function controlId(...parts: string[]): string {
  return parts.map((part) => encodeURIComponent(part)).join("-");
}

export interface DerivedReviewStepProps {
  attemptId: string;
  onBackToBaseline?: () => void;
  onBackToConfirmation?: () => void;
  onApproveSuccess: () => void;
  onSaveAndExit: () => void;
}

function generateRandomId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).substring(2, 9)}`;
}

interface EvidenceLookupItem {
  id: string;
  section: string;
  parentTitle: string;
  title?: string;
  text?: string;
  source_refs?: Array<{ document_id?: string; locator?: Record<string, any> }>;
}

export const DerivedReviewStep: React.FC<DerivedReviewStepProps> = ({
  attemptId,
  onBackToBaseline,
  onBackToConfirmation,
  onApproveSuccess,
  onSaveAndExit,
}) => {
  const [schema, setSchema] = useState<FieldSchema | null>(null);
  const [review, setReview] = useState<ReviewResource | null>(null);
  const [attempt, setAttempt] = useState<CreationAttempt | null>(null);
  const [document, setDocument] = useState<Record<string, any>>({});
  const [baselineDoc, setBaselineDoc] = useState<Record<string, any>>({});
  const [pendingOps, setPendingOps] = useState<Map<string, CandidateProfileReviewOperation>>(new Map());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [staleError, setStaleError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("Review derived claims and evidence links.");
  const reviewRef = useRef<ReviewResource | null>(null);
  const documentRef = useRef(document);
  const pendingOpsRef = useRef(pendingOps);

  // Source Dialog state
  const [sourceDialogOpen, setSourceDialogOpen] = useState(false);
  const [activeClaimName, setActiveClaimName] = useState("");
  const [activeReferencedEvidence, setActiveReferencedEvidence] = useState<EvidenceLookupItem[]>([]);

  const reconciliationKey = `fitcv_recon_derived_${attemptId}`;

  // Load reviews & attempt
  const loadReview = useCallback(async () => {
    setLoading(true);
    setError(null);
    setStaleError(null);
    try {
      const schemaData = await fetchFieldSchema();
      setSchema(schemaData);

      let attemptData = await fetchCreationAttempt(attemptId);
      if (
        attemptData.creation_status === "deriving" ||
        attemptData.creation_status === "base_mapping" ||
        attemptData.creation_status === "extracting_base" ||
        attemptData.next_action === "wait"
      ) {
        setStatusMessage("Processing candidate document...");
        attemptData = await waitForAttemptTransition(attemptId, ["review_derived", "confirm", "review_baseline"]);
      }

      if (attemptData.creation_status === "base_review" || attemptData.next_action === "review_baseline") {
        if (onBackToBaseline) {
          onBackToBaseline();
          return;
        }
      }

      const [baselineData, derivedData] = await Promise.all([
        fetchBaselineReview(attemptId),
        fetchDerivedReview(attemptId),
      ]);
      reviewRef.current = derivedData;
      documentRef.current = derivedData.document || {};
      setReview(derivedData);
      setDocument(documentRef.current);
      setBaselineDoc(baselineData.document || {});
      setAttempt(attemptData);
      setLoading(false);
      setStatusMessage("Derived claims loaded.");
    } catch (err: any) {
      setError(err.message || "Failed to load derived review.");
      setLoading(false);
    }
  }, [attemptId, onBackToBaseline]);

  useEffect(() => {
    loadReview();
  }, [loadReview]);

  // Index all baseline evidence items
  const allBaselineEvidence = useMemo<EvidenceLookupItem[]>(() => {
    const list: EvidenceLookupItem[] = [];
    if (!baselineDoc) return list;

    const sections = ["experiences", "education", "projects", "certifications", "achievements", "volunteering"];
    sections.forEach((sec) => {
      const parents = baselineDoc[sec] || [];
      parents.forEach((parent: any) => {
        const parentTitle = parent.role || parent.name || parent.institution || parent.title || parent.id;
        const evs = parent.evidence || [];
        evs.forEach((ev: any) => {
          list.push({
            id: ev.id,
            section: sec,
            parentTitle,
            title: ev.title,
            text: ev.text,
            source_refs: ev.source_refs,
          });
        });
      });
    });

    return list;
  }, [baselineDoc]);

  // Queue operation
  const queueOperation = (op: CandidateProfileReviewOperation) => {
    const next = new Map(pendingOpsRef.current);
    next.set(op.path, op);
    pendingOpsRef.current = next;
    setPendingOps(next);
  };

  // Field change on a derived claim
  const handleClaimFieldChange = (sectionId: string, claimId: string, fieldName: string, value: any) => {
    const path = `/${sectionId}/${claimId}/${fieldName}`;
    const doc = JSON.parse(JSON.stringify(documentRef.current));
    const section = doc[sectionId] || [];
    const claim = section.find((c: any) => c.id === claimId);
    if (claim) {
      claim[fieldName] = value;
      if (fieldName === "evidence_refs") {
        claim.support_status = Array.isArray(value) && value.length > 0 ? "supported" : "unsupported";
      }
    }
    documentRef.current = doc;
    setDocument(doc);

    queueOperation({ operation: "replace", path, value });
  };

  // Toggle evidence ref
  const handleToggleEvidenceRef = (sectionId: string, claimId: string, evId: string) => {
    const currentClaim = (documentRef.current[sectionId] || []).find((c: any) => c.id === claimId);
    const currentRefs: string[] = Array.isArray(currentClaim?.evidence_refs) ? currentClaim.evidence_refs : [];

    const nextRefs = currentRefs.includes(evId)
      ? currentRefs.filter((id) => id !== evId)
      : [...currentRefs, evId];

    handleClaimFieldChange(sectionId, claimId, "evidence_refs", nextRefs);
  };

  // Add a new derived claim
  const handleAddClaim = (sectionId: string) => {
    const newId = generateRandomId(sectionId.substring(0, 5));
    const newClaim = {
      id: newId,
      name: "",
      confidence: 1.0,
      origin: "manual",
      support_status: "unsupported",
      evidence_refs: [],
    };

    const doc = JSON.parse(JSON.stringify(documentRef.current));
    if (!Array.isArray(doc[sectionId])) doc[sectionId] = [];
    doc[sectionId].push(newClaim);
    documentRef.current = doc;
    setDocument(doc);

    queueOperation({ operation: "add", path: `/${sectionId}`, value: newClaim });
  };

  // Remove a claim
  const handleRemoveClaim = (sectionId: string, claimId: string) => {
    const doc = JSON.parse(JSON.stringify(documentRef.current));
    if (Array.isArray(doc[sectionId])) {
      doc[sectionId] = doc[sectionId].filter((c: any) => c.id !== claimId);
    }
    documentRef.current = doc;
    setDocument(doc);

    queueOperation({ operation: "remove", path: `/${sectionId}/${claimId}` });
  };

  // Flush operations
  const flushOperations = async (): Promise<ReviewResource | null> => {
    const currentReview = reviewRef.current;
    const ops = Array.from(pendingOpsRef.current.values());
    if (ops.length === 0 || !currentReview) return currentReview;

    setSaving(true);
    setError(null);
    setStatusMessage("Saving draft changes...");

    try {
      const updated = await patchDerivedReview(attemptId, currentReview.revision, ops);
      reviewRef.current = updated;
      documentRef.current = updated.document || {};
      pendingOpsRef.current = new Map();
      setReview(updated);
      setDocument(documentRef.current);
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

  // Reapply unsaved operations
  const reapplyUnsavedEdits = async () => {
    setSaving(true);
    setError(null);
    try {
      const freshReview = await fetchDerivedReview(attemptId);
      reviewRef.current = freshReview;
      documentRef.current = freshReview.document || {};
      setReview(freshReview);
      setDocument(documentRef.current);

      let ops = Array.from(pendingOpsRef.current.values());
      const stored = sessionStorage.getItem(reconciliationKey);
      if (stored && ops.length === 0) {
        ops = JSON.parse(stored);
      }

      if (ops.length === 0) {
        setStaleError(null);
        setSaving(false);
        return;
      }

      const updated = await patchDerivedReview(attemptId, freshReview.revision, ops);
      reviewRef.current = updated;
      documentRef.current = updated.document || {};
      pendingOpsRef.current = new Map();
      setReview(updated);
      setDocument(documentRef.current);
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

  // Regenerate all or targets
  const handleRegenerate = async (target: string = "*") => {
    if (!review) return;
    setSaving(true);
    setError(null);
    setStatusMessage("Regenerating all derived claims...");

    try {
      await regenerateDerivedReview(attemptId, review.revision, [target]);
      const attempt = await waitForAttemptTransition(attemptId, "review_derived");
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
      const restored = await undoDerivedRegeneration(attemptId, review.revision);
      reviewRef.current = restored;
      documentRef.current = restored.document || {};
      pendingOpsRef.current = new Map();
      setReview(restored);
      setDocument(documentRef.current);
      setPendingOps(new Map());
      setSaving(false);
      setStatusMessage("Regeneration undone.");
    } catch (err: any) {
      setError(err.message || "Failed to undo regeneration.");
      setSaving(false);
    }
  };

  // Approve derived claims
  const handleApprove = async () => {
    if (!review || !attempt || review.capabilities.approve !== true) return;
    setApproving(true);
    setError(null);
    setStatusMessage("Flushing changes and approving derived claims...");

    try {
      const currentReview = (await flushOperations()) || reviewRef.current;
      if (!currentReview) return;

      const baselineFingerprint = attempt.fingerprints?.approved_baseline || "";

      await approveDerivedReview(
        attemptId,
        currentReview.revision,
        currentReview.fingerprint,
        baselineFingerprint
      );

      setStatusMessage("Derived claims approved! Moving to final confirmation...");
      onApproveSuccess();
    } catch (err: any) {
      setApproving(false);
      setError(err.message || "Failed to approve derived review.");
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

  const openSourceDialogForClaim = (claim: any) => {
    const refs: string[] = claim.evidence_refs || [];
    const matched = allBaselineEvidence.filter((ev) => refs.includes(ev.id));
    setActiveClaimName(claim.name || claim.id);
    setActiveReferencedEvidence(matched);
    setSourceDialogOpen(true);
  };

  if (loading) {
    return <LoadingState message="Loading derived claims review..." />;
  }

  if (!review || !schema) {
    return <ErrorState message={error || "Failed to load review data."} onRetry={loadReview} />;
  }

  const derivedSections = schema.sections.filter((s) => s.stage === "derived");

  return (
    <div className="derived-review-container">
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
              Step 3 · Controlled derivation
            </span>
            <h2 style={{ margin: "4px 0", fontSize: 22, fontFamily: "var(--display-font)" }}>
              Review derived claims
            </h2>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
              Each claim owns editable evidence refs, confidence, and origin. Unsupported claims require linked evidence statements.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {review.capabilities.regenerate_all && (
            <Button size="compact" onClick={() => handleRegenerate("*")} loading={saving} disabled={saving || approving}>
              ✨ Regenerate all derived claims
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
            disabled={saving || approving || Boolean(staleError) || review.capabilities.approve !== true}
          >
            Approve derived claims →
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

      {/* Derived Sections */}
      <div style={{ display: "flex", flexDirection: "column", gap: 24, marginTop: 16 }}>
        {derivedSections.map((section) => {
          const claims = document[section.id] || [];

          return (
            <section
              key={section.id}
              className="table-card"
              style={{ padding: 24 }}
              aria-labelledby={`derived-section-${section.id}-heading`}
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
                  <h3 id={`derived-section-${section.id}-heading`} style={{ margin: 0, fontSize: 16 }}>
                    {section.label} ({claims.length})
                  </h3>
                  <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--muted)" }}>
                    {section.description || "Each claim is independently editable and traceable."}
                  </p>
                </div>

                <Button
                  size="compact"
                  onClick={() => handleAddClaim(section.id)}
                >
                  + Add {section.item_label || section.label}
                </Button>
              </div>

              {claims.length === 0 ? (
                <p style={{ margin: 0, color: "var(--muted)", fontSize: 13, fontStyle: "italic" }}>
                  No {section.label.toLowerCase()} generated. Add a claim manually or click Regenerate.
                </p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  {claims.map((claim: any, idx: number) => {
                    const claimId = claim.id || `claim_${idx}`;
                    const originLabel = claim.origin === "llm_inferred" ? "Inferred" : claim.origin || "Inferred";
                    const confidencePct = Math.round((Number(claim.confidence) || 0) * 100);
                    const isSupported = claim.support_status === "supported" || (claim.evidence_refs?.length > 0);
                    const claimNameId = controlId("derived", section.id, claimId, "name");
                    const confidenceId = controlId("derived", section.id, claimId, "confidence");

                    return (
                      <article
                        key={claimId}
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
                            flexWrap: "wrap",
                            gap: 8,
                          }}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <code style={{ fontSize: 11, color: "var(--accent)" }}>{claimId}</code>
                            <StatusBadge
                              status={claim.origin === "manual" ? "info" : "neutral"}
                              label={originLabel}
                            />
                            <StatusBadge
                              status={isSupported ? "success" : "warn"}
                              label={isSupported ? "Supported" : "Unsupported"}
                            />
                            <span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 600 }}>
                              {confidencePct}% Confidence
                            </span>
                          </div>

                          <div style={{ display: "flex", gap: 6 }}>
                            <EvidenceReferenceButton
                              referenceIds={claim.evidence_refs || []}
                              onOpen={() => openSourceDialogForClaim(claim)}
                            />
                            <Button
                              size="compact"
                              variant="danger"
                              onClick={() => handleRemoveClaim(section.id, claimId)}
                            >
                              Remove
                            </Button>
                          </div>
                        </div>

                        {/* Name and Confidence */}
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                            gap: 12,
                            marginBottom: 14,
                          }}
                        >
                          <div>
                            <label htmlFor={claimNameId} style={{ display: "block", fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                              Claim Name *
                            </label>
                            <input
                              id={claimNameId}
                              className="field-input"
                              type="text"
                              title={claim.name || ""}
                              value={claim.name || ""}
                              onChange={(e) =>
                                handleClaimFieldChange(section.id, claimId, "name", e.target.value)
                              }
                            />
                          </div>

                          <div>
                            <label htmlFor={confidenceId} style={{ display: "block", fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                              Confidence (0.0 – 1.0)
                            </label>
                            <input
                              id={confidenceId}
                              className="field-input"
                              type="number"
                              min="0"
                              max="1"
                              step="0.05"
                              value={claim.confidence ?? 1.0}
                              onChange={(e) =>
                                handleClaimFieldChange(
                                  section.id,
                                  claimId,
                                  "confidence",
                                  parseFloat(e.target.value) || 0
                                )
                              }
                            />
                          </div>
                        </div>

                        {/* Evidence References Selector */}
                        <fieldset
                          style={{
                            border: "1px solid var(--border-soft)",
                            borderRadius: "var(--radius-sm)",
                            padding: "10px 12px",
                            margin: 0,
                          }}
                        >
                          <legend style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--muted)", padding: "0 6px" }}>
                            Evidence References ({claim.evidence_refs?.length || 0} selected)
                          </legend>

                          {allBaselineEvidence.length === 0 ? (
                            <span style={{ fontSize: 12, color: "var(--muted)", fontStyle: "italic" }}>
                              No approved baseline evidence items available.
                            </span>
                          ) : (
                            <div
                              style={{
                                display: "grid",
                                gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
                                gap: 6,
                                maxHeight: 180,
                                overflowY: "auto",
                                padding: "4px 0",
                              }}
                            >
                              {allBaselineEvidence.map((ev) => {
                                const isChecked = (claim.evidence_refs || []).includes(ev.id);
                                const evidenceCheckboxId = controlId("derived", section.id, claimId, "evidence", ev.id);

                                return (
                                  <label
                                    key={ev.id}
                                    htmlFor={evidenceCheckboxId}
                                    title={ev.text ? `${ev.parentTitle}: ${ev.title ? ev.title + " — " : ""}${ev.text}` : `${ev.parentTitle}: ${ev.title || ""}`}
                                    style={{
                                      display: "flex",
                                      alignItems: "flex-start",
                                      gap: 8,
                                      fontSize: 12,
                                      padding: "4px 6px",
                                      borderRadius: "var(--radius-sm)",
                                      background: isChecked ? "var(--accent-soft)" : "transparent",
                                      cursor: "pointer",
                                      minWidth: 0,
                                    }}
                                  >
                                    <input
                                      id={evidenceCheckboxId}
                                      type="checkbox"
                                      checked={isChecked}
                                      onChange={() => handleToggleEvidenceRef(section.id, claimId, ev.id)}
                                      style={{ marginTop: 2, flexShrink: 0 }}
                                    />
                                    <div style={{ minWidth: 0, flex: 1, lineHeight: 1.3 }}>
                                      <code style={{ fontSize: 11, color: isChecked ? "var(--accent)" : "var(--text)" }}>
                                        {ev.id}
                                      </code>
                                      <span
                                        title={ev.text ? `${ev.parentTitle}: ${ev.title ? ev.title + " — " : ""}${ev.text}` : `${ev.parentTitle}: ${ev.title || ""}`}
                                        style={{
                                          display: "block",
                                          color: "var(--muted)",
                                          fontSize: 11,
                                          whiteSpace: "normal",
                                          overflowWrap: "anywhere",
                                        }}
                                      >
                                        {ev.parentTitle}: {ev.title ? `${ev.title}${ev.text ? " — " : ""}` : ""}{ev.text || ""}
                                      </span>
                                    </div>
                                  </label>
                                );
                              })}
                            </div>
                          )}
                          <small style={{ display: "block", marginTop: 6, fontSize: 11, color: "var(--muted)" }}>
                            Claims must link to nested evidence IDs.
                          </small>
                        </fieldset>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          );
        })}
      </div>

      <ReviewLogConsole
        stage="derived"
        attemptId={attemptId}
        statusMessage={statusMessage}
        revision={review.revision}
        fingerprint={review.fingerprint}
        baselineFingerprint={attempt?.fingerprints?.approved_baseline}
      />

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
        <div style={{ display: "flex", gap: 8 }}>
          {onBackToConfirmation && review.capabilities.approve !== true && (
            <Button variant="secondary" id="backToConfirmation" onClick={onBackToConfirmation}>
              ← Back to confirmation
            </Button>
          )}
          {onBackToBaseline && (
            <Button variant="secondary" id="backToBaseline" onClick={onBackToBaseline}>
              ← Back to baseline
            </Button>
          )}
          <Button variant="secondary" onClick={handleSaveAndExit}>
            Save and exit
          </Button>
        </div>
        <Button
          variant="primary"
          onClick={handleApprove}
          loading={approving}
          disabled={saving || approving || Boolean(staleError) || review.capabilities.approve !== true}
        >
          Approve derived claims →
        </Button>
      </div>

      {/* Source Dialog */}
      <SourceDialog
        open={sourceDialogOpen}
        onClose={() => setSourceDialogOpen(false)}
        attemptId={attemptId}
        title={`Evidence citation: ${activeClaimName}`}
        evidenceItems={activeReferencedEvidence}
      />
    </div>
  );
};
