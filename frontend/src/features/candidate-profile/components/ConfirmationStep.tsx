import React, { useEffect, useState, useMemo } from "react";
import { Button, LoadingState, ErrorState, LiveStatus, StatusBadge } from "../../../components";
import {
  fetchConfirmation,
  fetchCreationAttempt,
  confirmProfile,
  downloadAttemptSource,
} from "../api";
import { ConfirmationResource, CreationAttempt } from "../types";

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
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("Review final profile facts and confirmation.");

  // Collapsible section toggles
  const [baselineOpen, setBaselineOpen] = useState(true);
  const [derivedOpen, setDerivedOpen] = useState(true);
  const [technicalLogOpen, setTechnicalLogOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    Promise.all([
      fetchConfirmation(attemptId),
      fetchCreationAttempt(attemptId),
    ])
      .then(([confData, attData]) => {
        if (isMounted) {
          setConfirmation(confData);
          setAttempt(attData);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || "Failed to load confirmation details.");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [attemptId]);

  const canonical = confirmation?.profile?.canonical || {};

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
    setStatusMessage("Publishing candidate profile revision...");

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

      setStatusMessage("Profile confirmed and saved!");
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
      setError(err.message || "Failed to confirm profile.");
    }
  };

  const handleDownloadSource = () => {
    downloadAttemptSource(attemptId, attempt?.source_document?.original_filename || "candidate_source");
  };

  if (loading) {
    return <LoadingState message="Loading final confirmation review..." />;
  }

  if (!confirmation || !attempt) {
    return <ErrorState message={error || "Failed to load confirmation."} onRetry={onCancel} />;
  }

  const canConfirm = confirmation.readiness?.ready !== false;

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
            disabled={confirming || !canConfirm}
          >
            Confirm and save profile
          </Button>
        </div>
      </div>

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
                              <code style={{ fontSize: 11, color: "var(--accent)" }}>{ev.id}: </code>
                              <span title={ev.text} style={{ wordBreak: "break-word" }}>{ev.text}</span>
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
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 8 }}>
                    {items.map((item: any) => (
                      <div
                        key={item.id}
                        style={{
                          padding: "8px 12px",
                          background: "var(--surface)",
                          border: "1px solid var(--border)",
                          borderRadius: "var(--radius-sm)",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <div style={{ minWidth: 0, flex: 1, marginRight: 8 }}>
                          <strong title={item.name} style={{ fontSize: 13, display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {item.name}
                          </strong>
                          <span title={(item.evidence_refs || []).join(", ")} style={{ fontSize: 11, color: "var(--muted)", display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {item.evidence_refs?.length || 0} evidence refs
                          </span>
                        </div>
                        <StatusBadge
                          status={item.support_status === "supported" ? "success" : "neutral"}
                          label={`${Math.round((Number(item.confidence) || 1) * 100)}%`}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Technical Event Log Console & Traceability */}
      <div className="table-card" style={{ marginBottom: 24, overflow: "hidden" }}>
        <button
          type="button"
          onClick={() => setTechnicalLogOpen(!technicalLogOpen)}
          style={{
            width: "100%",
            padding: "16px 20px",
            background: "var(--surface-2)",
            border: 0,
            borderBottom: technicalLogOpen ? "1px solid var(--border-soft)" : "none",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          <div>
            <strong style={{ fontSize: 15, color: "var(--text)" }}>Traceability & Technical Event Log</strong>
            <span style={{ display: "block", fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
              Document locators, claim-level evidence citations, attempt ID, and confirmation fingerprints
            </span>
          </div>
          <span style={{ fontSize: 14, color: "var(--muted)" }}>{technicalLogOpen ? "▲" : "▼"}</span>
        </button>

        {technicalLogOpen && (
          <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12, fontSize: 12, fontFamily: "var(--font-mono)" }}>
            <div style={{ padding: 12, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)" }}>
              <div style={{ color: "var(--muted)", marginBottom: 4 }}>Attempt ID: <strong style={{ color: "var(--text)" }}>{attemptId}</strong></div>
              <div style={{ color: "var(--muted)", marginBottom: 4 }}>Confirmation Fingerprint: <code style={{ color: "var(--accent)" }}>{confirmation.fingerprint || "—"}</code></div>
              <div style={{ color: "var(--muted)", marginBottom: 4 }}>Baseline Fingerprint: <code style={{ color: "var(--text)" }}>{confirmation.approval_fingerprints?.baseline || "—"}</code></div>
              <div style={{ color: "var(--muted)" }}>Derived Fingerprint: <code style={{ color: "var(--text)" }}>{confirmation.approval_fingerprints?.derived || "—"}</code></div>
            </div>
            <div style={{ maxHeight: 200, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
              {["skills", "role_families", "domain_tags", "responsibility_themes"].flatMap((sec) => (canonical[sec] || []).map((c: any) => (
                <div key={`${sec}_${c.id}`} style={{ padding: "6px 8px", background: "var(--surface)", border: "1px solid var(--border-soft)", borderRadius: "var(--radius-sm)", display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text)" }} title={c.name}>{c.name}</span>
                  <span style={{ color: "var(--muted)" }}>Refs: {(c.evidence_refs || []).join(", ") || "unsupported"}</span>
                </div>
              )))}
            </div>
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
            disabled={confirming || !canConfirm}
          >
            Confirm and save profile ✓
          </Button>
        </div>
      </div>
    </div>
  );
};
