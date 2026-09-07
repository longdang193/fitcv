import React, { useEffect, useState, useMemo, useCallback } from "react";
import { Button, LoadingState, ErrorState, StatusBadge, Notice } from "../../../components";
import {
  fetchConfirmation,
  fetchCreationAttempt,
  confirmProfile,
  downloadAttemptSource,
  retryAttempt,
} from "../api";

export interface ConfirmationErrorState {
  code?: string;
  message: string;
  action?: string;
  retryable?: boolean;
  fieldErrors?: Array<{ field: string; code?: string; message: string }>;
}
import { ConfirmationResource, CreationAttempt } from "../types";
import { SourceDialog } from "./SourceDialog";
import { EvidenceReferenceButton } from "./EvidenceReferenceButton";
import { formatIdentifier } from "../../../lib/format";

export interface ConfirmationStepProps {
  attemptId: string;
  onBackToDerived?: () => void;
  onConfirmed: (profileId: string) => void;
  onCancel: () => void;
}

export const ConfirmationStep: React.FC<ConfirmationStepProps> = ({
  attemptId,
  onBackToDerived,
  onConfirmed,
  onCancel,
}) => {
  const [confirmation, setConfirmation] = useState<ConfirmationResource | null>(null);
  const [attempt, setAttempt] = useState<CreationAttempt | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState<ConfirmationErrorState | null>(null);
  // Collapsible section toggles
  const [baselineOpen, setBaselineOpen] = useState(true);
  const [derivedOpen, setDerivedOpen] = useState(true);
  const [sourceDialogOpen, setSourceDialogOpen] = useState(false);
  const [activeEvidenceTitle, setActiveEvidenceTitle] = useState("");
  const [activeReviewedValue, setActiveReviewedValue] = useState("");
  const [activeSourceRefs, setActiveSourceRefs] = useState<Array<{ document_id?: string; locator?: Record<string, any> }>>([]);
  const [activeReferencedEvidence, setActiveReferencedEvidence] = useState<any[]>([]);

  const loadConfirmationData = useCallback(async () => {
    setLoading(true);
    try {
      const [attResult, confResult] = await Promise.allSettled([
        fetchCreationAttempt(attemptId),
        fetchConfirmation(attemptId),
      ]);

      if (attResult.status === "fulfilled") {
        const attData = attResult.value;
        setAttempt(attData);

        if (confResult.status === "fulfilled") {
          setConfirmation(confResult.value);
          setError(null);
        } else {
          if (attData.creation_status === "failed") {
            const failure = attData.failure || {};
            setError({
              code: failure.code || "candidate_profile_persistence_failed",
              message: failure.message || "Candidate Profile confirmation could not be persisted.",
              action: failure.retryable ? "Retry confirmation." : (failure.action || "Retry confirmation."),
              retryable: failure.retryable ?? true,
            });
          } else {
            const confErr: any = confResult.reason;
            const fieldErrors = Array.isArray(confErr?.fieldErrors)
              ? confErr.fieldErrors
              : Array.isArray(confErr?.field_errors)
              ? confErr.field_errors
              : undefined;
            setError({
              code: confErr?.code,
              message: confErr?.message || "Failed to load confirmation details.",
              action: confErr?.action,
              retryable: typeof confErr?.retryable === "boolean" ? confErr.retryable : undefined,
              fieldErrors,
            });
          }
        }
      } else {
        const err: any = attResult.reason;
        setError({
          code: err?.code,
          message: err?.message || "Failed to load confirmation details.",
          action: err?.action,
          retryable: typeof err?.retryable === "boolean" ? err.retryable : undefined,
        });
      }
    } finally {
      setLoading(false);
    }
  }, [attemptId]);

  useEffect(() => {
    loadConfirmationData();
  }, [loadConfirmationData]);

  const canonical = confirmation?.profile?.canonical || {};

  const baselineEvidence = useMemo(() => {
    const evidence = new Map<string, any>();
    ["experiences", "education", "projects", "certifications", "achievements", "volunteering"].forEach((section) => {
      (canonical[section] || []).forEach((item: any) => {
        (item.evidence || []).forEach((entry: any) => evidence.set(entry.id, entry));
      });
    });
    return evidence;
  }, [canonical]);

  const openEvidenceDetails = (title: string, value: string, sourceRefs: Array<{ document_id?: string; locator?: Record<string, any> }> = [], evidenceItems: any[] = []) => {
    setActiveEvidenceTitle(title);
    setActiveReviewedValue(value);
    setActiveSourceRefs(sourceRefs);
    setActiveReferencedEvidence(evidenceItems);
    setSourceDialogOpen(true);
  };

  const openClaimEvidence = (claim: any) => {
    const evidenceItems = (claim.evidence_refs || [])
      .map((id: string) => baselineEvidence.get(id))
      .filter(Boolean);
    openEvidenceDetails(`Evidence citation: ${claim.name || claim.id}`, "", [], evidenceItems);
  };

  // Compute counts
  const counts = useMemo(() => {
    let evidenceCount = 0;
    let claimsCount = 0;
    let supportedCount = 0;

    const sections = ["experiences", "education", "projects", "certifications", "achievements", "volunteering"];
    sections.forEach((sec) => {
      const items = canonical[sec] || [];
      items.forEach((item: any) => {
        if (Array.isArray(item.evidence)) {
          evidenceCount += item.evidence.length;
        }
      });
    });

    const derivedSecs = ["skills", "role_families", "domain_tags", "responsibility_themes"];
    derivedSecs.forEach((sec) => {
      const claims = canonical[sec] || [];
      claimsCount += claims.length;
      claims.forEach((c: any) => {
        if (c.support_status === "supported" || (c.evidence_refs && c.evidence_refs.length > 0)) {
          supportedCount++;
        }
      });
    });

    return { evidenceCount, claimsCount, supportedCount };
  }, [canonical]);

  const handleConfirm = async () => {
    if (!confirmation || !attempt) return;
    setConfirming(true);
    setError(null);
    try {
      const baselineFp = confirmation.approval_fingerprints?.baseline || attempt.fingerprints?.approved_baseline || "";
      const derivedFp = confirmation.approval_fingerprints?.derived || attempt.fingerprints?.approved_derived || "";
      const confFp = confirmation.fingerprint || "";

      const res = await confirmProfile(
        attemptId,
        confirmation.revision,
        baselineFp,
        derivedFp,
        confFp
      );

      onConfirmed(res.profile_id);
    } catch (err: any) {
      if (err.code === "candidate_profile_already_confirmed") {
        try {
          const fresh = await fetchCreationAttempt(attemptId);
          if (fresh.profile_id) {
            onConfirmed(fresh.profile_id);
            return;
          }
        } catch {}
      }
      setConfirming(false);
      let freshAttempt: CreationAttempt | null = null;
      try {
        freshAttempt = await fetchCreationAttempt(attemptId);
        setAttempt(freshAttempt);
      } catch {}

      const failure = freshAttempt?.failure;
      const fieldErrors = Array.isArray(err?.fieldErrors)
        ? err.fieldErrors
        : Array.isArray(err?.field_errors)
        ? err.field_errors
        : undefined;
      const isRetryable =
        typeof err?.retryable === "boolean"
          ? err.retryable
          : typeof failure?.retryable === "boolean"
          ? failure.retryable
          : Boolean(err?.details && typeof err.details === "object" && (err.details as any).retryable);

      setError({
        code: failure?.code || err?.code,
        message: failure?.message || err?.message || "Failed to confirm profile.",
        action: failure?.action || err?.action || (isRetryable ? "Retry confirmation." : undefined),
        retryable: isRetryable,
        fieldErrors,
      });
    }
  };

  const handleRetryConfirmation = async () => {
    if (!attempt && !attemptId) return;
    setRetrying(true);
    // Keep error state in place while retrying; do not clear error before retry succeeds
    try {
      let expectedRevision = attempt?.revision;
      try {
        const latestAttempt = await fetchCreationAttempt(attemptId);
        expectedRevision = latestAttempt.revision;
        setAttempt(latestAttempt);
      } catch {}

      if (typeof expectedRevision !== "number") {
        throw new Error("Missing attempt revision for retry.");
      }

      const retried = await retryAttempt(attemptId, expectedRevision);
      setAttempt(retried);
      const freshConfirmation = await fetchConfirmation(attemptId);
      setConfirmation(freshConfirmation);
      setError(null);
    } catch (err: any) {
      const fieldErrors = Array.isArray(err?.fieldErrors)
        ? err.fieldErrors
        : Array.isArray(err?.field_errors)
        ? err.field_errors
        : undefined;
      const isRetryable =
        typeof err?.retryable === "boolean"
          ? err.retryable
          : Boolean(err?.details && typeof err.details === "object" && (err.details as any).retryable);

      setError({
        code: err?.code,
        message: err?.message || "Failed to retry confirmation.",
        action: err?.action || (isRetryable ? "Retry confirmation." : undefined),
        retryable: isRetryable,
        fieldErrors,
      });
    } finally {
      setRetrying(false);
    }
  };

  const handleDownloadSource = () => {
    downloadAttemptSource(attemptId, attempt?.source_document?.original_filename || "candidate_source");
  };

  if (loading) {
    return <LoadingState message="Loading final confirmation review..." />;
  }

  if (!confirmation || !attempt) {
    const isRetryable = Boolean(
      error?.retryable ||
      attempt?.failure?.retryable ||
      attempt?.capabilities?.retry
    );

    return (
      <div className="confirmation-step-container">
        <ErrorState
          title="Confirmation Failed"
          message={error?.message || "Failed to load confirmation details."}
          actionLabel={retrying ? "Retrying..." : "Retry confirmation"}
          retrying={retrying}
          onRetry={
            isRetryable
              ? handleRetryConfirmation
              : !attempt
              ? loadConfirmationData
              : undefined
          }
          actions={
            <>
              {onBackToDerived && (
                <Button variant="secondary" onClick={onBackToDerived} disabled={retrying}>
                  ← Back to derived review
                </Button>
              )}
              <Button variant="secondary" onClick={onCancel} disabled={retrying}>
                Exit to Candidate Profiles
              </Button>
            </>
          }
        >
          {error?.code && (
            <div className="error-code-wrapper">
              <span className="error-code">Code: {error.code}</span>
            </div>
          )}
          {error?.action && (
            <p className="error-action-guidance">
              {error.action}
            </p>
          )}
          {error?.fieldErrors && error.fieldErrors.length > 0 && (
            <ul className="field-errors-list">
              {error.fieldErrors.map((fe, idx) => (
                <li key={fe.field || idx}>
                  <strong>{fe.field}:</strong> {fe.message}
                  {fe.code && ` (${fe.code})`}
                </li>
              ))}
            </ul>
          )}
        </ErrorState>
      </div>
    );
  }

  const canConfirm = confirmation.readiness?.ready !== false && attempt.creation_status !== "failed" && !error;

  return (
    <div className="confirmation-step-container">
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <button
            type="button"
            className="btn-subtle"
            style={{ fontSize: 13, padding: "4px 8px", cursor: "pointer", border: 0, background: "transparent", color: "var(--muted)" }}
            onClick={onCancel}
          >
            ← Back to Candidate Profiles
          </button>
          <div style={{ marginTop: 4 }}>
            <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--accent)" }}>
              Step 4 · Confirmation
            </span>
            <h2 style={{ margin: "4px 0", fontSize: 22, fontFamily: "var(--display-font)" }}>
              Confirm Candidate Profile
            </h2>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
              Verify approved baseline facts, derived claims, and source citations before saving the canonical profile.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {onBackToDerived && (
            <Button variant="secondary" id="backToDerived" onClick={onBackToDerived}>
              ← Back to derived review
            </Button>
          )}
          <Button variant="secondary" onClick={onCancel}>
            Exit
          </Button>
          <Button
            variant="primary"
            onClick={handleConfirm}
            loading={confirming}
            disabled={confirming || retrying || !canConfirm}
          >
            Confirm and save profile
          </Button>
        </div>
      </div>

      {error && (
        <Notice
          variant="error"
          role="alert"
          className="confirmation-error-banner"
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, width: "100%" }}>
            <div style={{ flex: 1 }}>
              <strong style={{ display: "block", fontSize: 14 }}>{error.message}</strong>
              {error.code && (
                <div className="error-code-wrapper">
                  <span className="error-code">Code: {error.code}</span>
                </div>
              )}
              {error.action && (
                <p className="error-action-guidance" style={{ margin: "6px 0 0", textAlign: "left" }}>
                  {error.action}
                </p>
              )}
              {error.fieldErrors && error.fieldErrors.length > 0 && (
                <ul className="field-errors-list" style={{ margin: "6px 0 0", textAlign: "left" }}>
                  {error.fieldErrors.map((fe, idx) => (
                    <li key={fe.field || idx}>
                      <strong>{fe.field}:</strong> {fe.message}
                      {fe.code && ` (${fe.code})`}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {(error.retryable || attempt?.failure?.retryable || attempt?.capabilities?.retry) && (
              <Button
                variant="secondary"
                size="compact"
                onClick={handleRetryConfirmation}
                loading={retrying}
                disabled={retrying || confirming}
              >
                Retry confirmation
              </Button>
            )}
          </div>
        </Notice>
      )}


      {/* Grid of Summary Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 16,
          marginBottom: 24,
        }}
      >
        <div className="table-card" style={{ padding: 16 }}>
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--muted)" }}>
            Profile Name
          </span>
          <strong style={{ display: "block", fontSize: 16, marginTop: 4, color: "var(--text)" }}>
            {confirmation.profile_name}
          </strong>
          <span style={{ fontSize: 12, color: "var(--muted)", marginTop: 2, display: "block" }}>
            Schema: {confirmation.profile.schema_version}
          </span>
        </div>

        <div className="table-card" style={{ padding: 16 }}>
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--muted)" }}>
            Baseline Evidence
          </span>
          <strong style={{ display: "block", fontSize: 16, marginTop: 4, color: "var(--accent)" }}>
            {counts.evidenceCount} statements
          </strong>
          <span style={{ fontSize: 12, color: "var(--muted)", marginTop: 2, display: "block" }}>
            Approved: {attempt.approval_timestamps?.baseline ? "✓ Yes" : "Pending"}
          </span>
        </div>

        <div className="table-card" style={{ padding: 16 }}>
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--muted)" }}>
            Derived Claims
          </span>
          <strong style={{ display: "block", fontSize: 16, marginTop: 4, color: "var(--success)" }}>
            {counts.supportedCount} of {counts.claimsCount} supported
          </strong>
          <span style={{ fontSize: 12, color: "var(--muted)", marginTop: 2, display: "block" }}>
            Approved: {attempt.approval_timestamps?.derived ? "✓ Yes" : "Pending"}
          </span>
        </div>

        <div className="table-card" style={{ padding: 16 }}>
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--muted)" }}>
            Source Document
          </span>
          <strong style={{ display: "block", fontSize: 14, marginTop: 4, color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {attempt.source_document?.original_filename || "candidate.md"}
          </strong>
          <button
            type="button"
            className="btn-subtle"
            style={{ fontSize: 12, padding: "2px 0", cursor: "pointer", color: "var(--accent)", border: 0, background: "transparent", marginTop: 4 }}
            onClick={handleDownloadSource}
          >
            Download source 📥
          </button>
        </div>
      </div>

      {/* Baseline Facts Accordion */}
      <div className="table-card" style={{ marginBottom: 16, overflow: "hidden" }}>
        <button
          type="button"
          onClick={() => setBaselineOpen(!baselineOpen)}
          style={{
            width: "100%",
            padding: "16px 20px",
            background: "var(--surface-2)",
            border: 0,
            borderBottom: baselineOpen ? "1px solid var(--border-soft)" : "none",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          <div>
            <strong style={{ fontSize: 15, color: "var(--text)" }}>Approved Baseline Facts</strong>
            <span style={{ display: "block", fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
              Direct facts, contact info, experience, education, and repeatable evidence entries
            </span>
          </div>
          <span style={{ fontSize: 14, color: "var(--muted)" }}>{baselineOpen ? "▲" : "▼"}</span>
        </button>

        {baselineOpen && (
          <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Identity & Contact */}
            <div style={{ padding: 14, background: "var(--surface)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
              <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>{canonical.name || confirmation.profile_name}</h4>
              {canonical.headline && <p style={{ margin: "0 0 6px", fontSize: 13, color: "var(--muted)" }}>{canonical.headline}</p>}
              {canonical.summary && <p style={{ margin: "0 0 8px", fontSize: 13 }}>{canonical.summary}</p>}

              {canonical.contact && (
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 12, color: "var(--muted)" }}>
                  {canonical.contact.email && <span>Email: <strong>{canonical.contact.email}</strong></span>}
                  {canonical.contact.phone && <span>Phone: <strong>{canonical.contact.phone}</strong></span>}
                  {canonical.contact.location && <span>Location: <strong>{canonical.contact.location}</strong></span>}
                </div>
              )}
            </div>

            {/* Experiences */}
            {canonical.experiences && canonical.experiences.length > 0 && (
              <div>
                <strong style={{ display: "block", fontSize: 13, textTransform: "uppercase", color: "var(--muted)", marginBottom: 8 }}>
                  Work Experience ({canonical.experiences.length})
                </strong>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {canonical.experiences.map((exp: any) => (
                    <div key={exp.id} style={{ padding: 12, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <strong style={{ fontSize: 13 }}>{exp.role} at {exp.company}</strong>
                        <span style={{ fontSize: 12, color: "var(--muted)" }}>{exp.start || "—"} - {exp.end || "Present"}</span>
                      </div>
                      {exp.evidence && exp.evidence.length > 0 && (
                        <div style={{ marginTop: 8, paddingLeft: 12, borderLeft: "2px solid var(--accent-soft)" }}>
                          {exp.evidence.map((ev: any) => (
                            <div key={ev.id} style={{ fontSize: 12, margin: "4px 0", minWidth: 0 }}>
                              <button
                                type="button"
                                className="btn-subtle"
                                onClick={() => openEvidenceDetails(`Evidence details: ${ev.id}`, ev.text || "", ev.source_refs || [])}
                                style={{ fontSize: 12, padding: 0, textAlign: "left", color: "var(--accent)", wordBreak: "break-word" }}
                              >
                                <code title={ev.id} style={{ fontSize: 11 }}>{formatIdentifier(ev.id)}: </code>{ev.text}
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Education */}
            {canonical.education && canonical.education.length > 0 && (
              <div>
                <strong style={{ display: "block", fontSize: 13, textTransform: "uppercase", color: "var(--muted)", marginBottom: 8 }}>
                  Education ({canonical.education.length})
                </strong>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {canonical.education.map((edu: any) => (
                    <div key={edu.id} style={{ padding: 12, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <strong style={{ fontSize: 13 }}>{edu.degree || edu.field} — {edu.institution}</strong>
                        <span style={{ fontSize: 12, color: "var(--muted)" }}>{edu.start || "—"} - {edu.end || "Present"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Derived Claims Accordion */}
      <div className="table-card" style={{ marginBottom: 24, overflow: "hidden" }}>
        <button
          type="button"
          onClick={() => setDerivedOpen(!derivedOpen)}
          style={{
            width: "100%",
            padding: "16px 20px",
            background: "var(--surface-2)",
            border: 0,
            borderBottom: derivedOpen ? "1px solid var(--border-soft)" : "none",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          <div>
            <strong style={{ fontSize: 15, color: "var(--text)" }}>Approved Derived Claims</strong>
            <span style={{ display: "block", fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
              Skills, Role Families, Domain Tags, and Responsibility Themes with traceability
            </span>
          </div>
          <span style={{ fontSize: 14, color: "var(--muted)" }}>{derivedOpen ? "▲" : "▼"}</span>
        </button>

        {derivedOpen && (
          <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
            {["skills", "role_families", "domain_tags", "responsibility_themes"].map((secId) => {
              const items = canonical[secId] || [];
              if (items.length === 0) return null;
              const label = secId.replace("_", " ").toUpperCase();

              return (
                <div key={secId}>
                  <strong style={{ display: "block", fontSize: 12, textTransform: "uppercase", color: "var(--muted)", marginBottom: 8 }}>
                    {label} ({items.length})
                  </strong>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 8 }}>
                    {items.map((item: any) => (
                      <div
                        key={item.id}
                        style={{
                          padding: "10px 12px",
                          background: "var(--surface)",
                          border: "1px solid var(--border)",
                          borderRadius: "var(--radius-sm)",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, minWidth: 0 }}>
                          <strong title={item.name} style={{ flex: 1, minWidth: 0, fontSize: 13, overflowWrap: "anywhere" }}>{item.name}</strong>
                          <StatusBadge
                            status={item.support_status === "supported" ? "success" : "neutral"}
                            label={`${Math.round((Number(item.confidence) || 1) * 100)}%`}
                          />
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 11, color: "var(--muted)" }}>
                          <span>Origin: {item.origin === "llm_inferred" ? "Inferred" : item.origin || "Inferred"}</span>
                          <EvidenceReferenceButton
                            referenceIds={item.evidence_refs || []}
                            onOpen={() => openClaimEvidence(item)}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Bottom Confirm Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "16px 20px",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <div>
          <strong style={{ display: "block", fontSize: 14 }}>Ready to publish profile</strong>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>
            Saved profile will become available for pipeline Runs.
          </span>
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          {onBackToDerived && (
            <Button variant="secondary" id="backToDerivedFooter" onClick={onBackToDerived}>
              ← Back to derived review
            </Button>
          )}
          <Button variant="secondary" onClick={onCancel}>
            Exit
          </Button>
          <Button
            variant="primary"
            onClick={handleConfirm}
            loading={confirming}
            disabled={confirming || retrying || !canConfirm}
          >
            Confirm and save profile ✓
          </Button>
        </div>
      </div>

      <SourceDialog
        open={sourceDialogOpen}
        onClose={() => setSourceDialogOpen(false)}
        attemptId={attemptId}
        title={activeEvidenceTitle}
        sourceRefs={activeSourceRefs}
        reviewedValue={activeReviewedValue}
        evidenceItems={activeReferencedEvidence}
      />
    </div>
  );
};
