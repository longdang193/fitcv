import React, { useEffect, useState, useMemo } from "react";
import { SourceDialog } from "./SourceDialog";
import { Button, LoadingState, ErrorState, StatusBadge, Dialog, LiveStatus } from "../../../components";
import {
  fetchProfileDetail,
  archiveProfile,
  restoreProfile,
  deleteProfile,
  downloadAttemptSource,
  createEditAttempt,
} from "../api";
import { CandidateProfileDetail } from "../types";

export interface DetailViewProps {
  profileId: string;
  onBack: () => void;
  onEdit: (attemptId: string) => void;
}

export const DetailView: React.FC<DetailViewProps> = ({ profileId, onBack, onEdit }) => {
  const [profile, setProfile] = useState<CandidateProfileDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("");

  // Delete confirm dialog state
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  // Source dialog state for derived claim evidence inspection
  const [sourceDialogOpen, setSourceDialogOpen] = useState(false);
  const [activeClaimName, setActiveClaimName] = useState("");
  const [activeReferencedEvidence, setActiveReferencedEvidence] = useState<any[]>([]);

  const handleEdit = async () => {
    if (!profile) return;
    setActionLoading(true);
    setError(null);
    setStatusMessage("Opening profile editor...");
    try {
      const attempt = await createEditAttempt(profile.profile_id);
      setActionLoading(false);
      onEdit(attempt.attempt_id);
    } catch (err: any) {
      setError(err.message || "Failed to edit candidate profile.");
      setActionLoading(false);
    }
  };


  const loadDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const profData = await fetchProfileDetail(profileId);
      setProfile(profData);
      setLoading(false);
    } catch (err: any) {
      setError(err.message || "Failed to load candidate profile details.");
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDetail();
  }, [profileId]);

  const canonical = profile?.canonical || profile?.profile?.canonical || profile?.overview || {};
  // Index all baseline evidence items
  const allBaselineEvidence = useMemo(() => {
    const list: any[] = [];
    const sections = ["experiences", "education", "projects", "certifications", "achievements", "volunteering"];
    sections.forEach((sec) => {
      const parents = canonical[sec] || [];
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
  }, [canonical]);

  const openEvidenceDialogForClaim = (claim: any) => {
    const refs: string[] = claim.evidence_refs || [];
    const matched = allBaselineEvidence.filter((ev) => refs.includes(ev.id));
    setActiveClaimName(claim.name || claim.id);
    setActiveReferencedEvidence(matched);
    setSourceDialogOpen(true);
  };


  // Lifecycle actions
  const handleArchive = async () => {
    if (!profile) return;
    setActionLoading(true);
    setError(null);
    setStatusMessage("Archiving profile...");
    try {
      const updated = await archiveProfile(profile.profile_id, profile.revision);
      setStatusMessage("Profile archived.");
      setProfile((prev) => (prev ? { ...prev, ...updated, lifecycle: "archived" } : null));
      setActionLoading(false);
    } catch (err: any) {
      setError(err.message || "Failed to archive profile.");
      setActionLoading(false);
    }
  };

  const handleRestore = async () => {
    if (!profile) return;
    setActionLoading(true);
    setError(null);
    setStatusMessage("Restoring profile...");
    try {
      const updated = await restoreProfile(profile.profile_id, profile.revision);
      setStatusMessage("Profile restored.");
      setProfile((prev) => (prev ? { ...prev, ...updated, lifecycle: "active" } : null));
      setActionLoading(false);
    } catch (err: any) {
      setError(err.message || "Failed to restore profile.");
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!profile) return;
    setActionLoading(true);
    setError(null);
    setStatusMessage("Deleting profile...");
    try {
      await deleteProfile(profile.profile_id, profile.revision);
      setDeleteConfirmOpen(false);
      onBack();
    } catch (err: any) {
      setError(err.message || "Failed to delete profile.");
      setActionLoading(false);
    }
  };

  const handleDownloadSource = () => {
    if (profile?.creation?.attempt_id) {
      downloadAttemptSource(profile.creation.attempt_id, profile.original_filename || "candidate_source");
    }
  };

  if (loading) {
    return <LoadingState message="Loading candidate profile..." />;
  }

  if (!profile) {
    return <ErrorState message={error || "Candidate profile not found."} onRetry={loadDetail} />;
  }

  const isArchived = profile.lifecycle === "archived";

  return (
    <div className="candidate-profile-detail-container">
      {/* Back button & page header */}
      <div style={{ marginBottom: 20 }}>
        <button
          type="button"
          className="btn-subtle"
          style={{ fontSize: 13, padding: "4px 8px", cursor: "pointer", border: 0, background: "transparent", color: "var(--muted)" }}
          onClick={onBack}
        >
          ← Back to Candidate Profiles
        </button>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginTop: 8,
            flexWrap: "wrap",
            gap: 16,
          }}
        >
          <div>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 4 }}>
              <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--accent)" }}>
                Candidate Profile
              </span>
              <StatusBadge
                status={isArchived ? "neutral" : "success"}
                label={isArchived ? "Archived" : "Active"}
              />
              <code style={{ fontSize: 12, color: "var(--muted)" }}>{profile.profile_id}</code>
            </div>
            <h2 style={{ margin: "4px 0", fontSize: 24, fontFamily: "var(--display-font)" }}>
              {profile.display_name || profile.profile_name}
            </h2>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
              {isArchived
                ? "Archived profile — retained for historical Run reproducibility."
                : "Active profile — available for new pipeline matching runs."}
            </p>
          </div>

          {/* Action buttons */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {!isArchived && profile.capabilities?.archive && (
              <Button onClick={handleArchive} disabled={actionLoading}>
                Archive Profile
              </Button>
            )}
            {isArchived && profile.capabilities?.restore && (
              <Button variant="primary" onClick={handleRestore} disabled={actionLoading}>
                Restore Profile
              </Button>
            )}
            {isArchived && profile.capabilities?.delete && (
              <Button variant="danger" onClick={() => setDeleteConfirmOpen(true)} disabled={actionLoading}>
                Delete Profile
              </Button>
            )}
            {!isArchived && (
              <Button onClick={handleEdit} disabled={actionLoading}>
                Edit Profile
              </Button>
            )}
          </div>
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

      {statusMessage && <LiveStatus message={statusMessage} />}

      {/* Main Details Stack */}
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Profile Overview Card */}
        <section className="table-card" style={{ padding: 20 }}>
          <h3 style={{ margin: "0 0 12px", fontSize: 15 }}>Profile Overview</h3>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: 16,
              fontSize: 13,
            }}
          >
            <div>
              <span style={{ color: "var(--muted)", display: "block", fontSize: 11, textTransform: "uppercase", fontWeight: 700 }}>
                Profile ID
              </span>
              <code>{profile.profile_id}</code>
            </div>
            <div>
              <span style={{ color: "var(--muted)", display: "block", fontSize: 11, textTransform: "uppercase", fontWeight: 700 }}>
                Revision
              </span>
              <span>r{profile.revision}</span>
            </div>
            <div>
              <span style={{ color: "var(--muted)", display: "block", fontSize: 11, textTransform: "uppercase", fontWeight: 700 }}>
                Created Time
              </span>
              <span>{profile.created_at_display || profile.created_at}</span>
            </div>
            <div>
              <span style={{ color: "var(--muted)", display: "block", fontSize: 11, textTransform: "uppercase", fontWeight: 700 }}>
                Run Availability
              </span>
              <span>{isArchived ? "Historical Runs only" : "Eligible for new Runs ✓"}</span>
            </div>
          </div>
        </section>

        {/* Source Input */}
        <section className="table-card" style={{ padding: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0, fontSize: 15 }}>Source Input</h3>
            {profile.creation?.attempt_id && (
              <Button size="compact" onClick={handleDownloadSource}>
                Download original source 📥
              </Button>
            )}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: 16,
              fontSize: 13,
            }}
          >
            <div>
              <span style={{ color: "var(--muted)", display: "block", fontSize: 11, textTransform: "uppercase", fontWeight: 700 }}>
                Original File
              </span>
              <span>{profile.original_filename || "candidate.md"}</span>
            </div>
            <div>
              <span style={{ color: "var(--muted)", display: "block", fontSize: 11, textTransform: "uppercase", fontWeight: 700 }}>
                Source Format
              </span>
              <span>{profile.creation?.source_format || "Markdown"}</span>
            </div>
            <div>
              <span style={{ color: "var(--muted)", display: "block", fontSize: 11, textTransform: "uppercase", fontWeight: 700 }}>
                Creation Attempt ID
              </span>
              <code>{profile.creation?.attempt_id || "—"}</code>
            </div>
          </div>
        </section>

        {/* Baseline Facts */}
        <section className="table-card" style={{ padding: 20 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 15 }}>Approved Baseline Facts</h3>

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Identity & Headline */}
            <div style={{ padding: 14, background: "var(--surface-2)", borderRadius: "var(--radius-md)" }}>
              <strong style={{ display: "block", fontSize: 15 }}>{canonical.name || profile.profile_name}</strong>
              {canonical.headline && <p style={{ margin: "4px 0 6px", fontSize: 13, color: "var(--muted)" }}>{canonical.headline}</p>}
              {canonical.summary && <p style={{ margin: "4px 0 0", fontSize: 13 }}>{canonical.summary}</p>}

              {canonical.contact && (
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 12, marginTop: 8, color: "var(--muted)" }}>
                  {canonical.contact.email && <span>Email: <strong>{canonical.contact.email}</strong></span>}
                  {canonical.contact.phone && <span>Phone: <strong>{canonical.contact.phone}</strong></span>}
                  {canonical.contact.location && <span>Location: <strong>{canonical.contact.location}</strong></span>}
                  {canonical.contact.linkedin && <span>LinkedIn: <a href={canonical.contact.linkedin} target="_blank" rel="noreferrer">{canonical.contact.linkedin}</a></span>}
                  {canonical.contact.github && <span>GitHub: <a href={canonical.contact.github} target="_blank" rel="noreferrer">{canonical.contact.github}</a></span>}
                </div>
              )}
            </div>

            {/* Experiences */}
            {canonical.experiences && canonical.experiences.length > 0 && (
              <div>
                <strong style={{ display: "block", fontSize: 12, textTransform: "uppercase", color: "var(--muted)", marginBottom: 8 }}>
                  Work Experiences ({canonical.experiences.length})
                </strong>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {canonical.experiences.map((exp: any) => (
                    <div key={exp.id} style={{ padding: 12, border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <strong style={{ fontSize: 13 }}>{exp.role} at {exp.company}</strong>
                        <span style={{ fontSize: 12, color: "var(--muted)" }}>{exp.start || "—"} – {exp.end || "Present"}</span>
                      </div>
                      {exp.location && <span style={{ fontSize: 12, color: "var(--muted)", display: "block" }}>{exp.location}</span>}
                      {exp.evidence && exp.evidence.length > 0 && (
                        <div style={{ marginTop: 8, paddingLeft: 12, borderLeft: "2px solid var(--accent-soft)", display: "flex", flexDirection: "column", gap: 4 }}>
                          {exp.evidence.map((ev: any) => (
                            <div key={ev.id} style={{ fontSize: 12 }}>
                              <code style={{ fontSize: 11, color: "var(--accent)" }}>{ev.id}: </code>
                              <span>{ev.text}</span>
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
                <strong style={{ display: "block", fontSize: 12, textTransform: "uppercase", color: "var(--muted)", marginBottom: 8 }}>
                  Education ({canonical.education.length})
                </strong>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {canonical.education.map((edu: any) => (
                    <div key={edu.id} style={{ padding: 12, border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <strong style={{ fontSize: 13 }}>{edu.degree || edu.field} — {edu.institution}</strong>
                        <span style={{ fontSize: 12, color: "var(--muted)" }}>{edu.start || "—"} – {edu.end || "Present"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Projects */}
            {canonical.projects && canonical.projects.length > 0 && (
              <div>
                <strong style={{ display: "block", fontSize: 12, textTransform: "uppercase", color: "var(--muted)", marginBottom: 8 }}>
                  Projects ({canonical.projects.length})
                </strong>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {canonical.projects.map((proj: any) => (
                    <div key={proj.id} style={{ padding: 12, border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <strong style={{ fontSize: 13 }}>{proj.name}</strong>
                        <span style={{ fontSize: 12, color: "var(--muted)" }}>{proj.start || "—"} – {proj.end || "Present"}</span>
                      </div>
                      {proj.context && <span style={{ fontSize: 12, color: "var(--muted)", display: "block" }}>{proj.context}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Derived Claims */}
        <section className="table-card" style={{ padding: 20 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 15 }}>Approved Derived Claims</h3>

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
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
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <strong style={{ fontSize: 13 }}>{item.name}</strong>
                          <StatusBadge
                            status={item.support_status === "supported" ? "success" : "neutral"}
                            label={`${Math.round((Number(item.confidence) || 1) * 100)}%`}
                          />
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 11, color: "var(--muted)" }}>
                          <span>Origin: {item.origin === "llm_inferred" ? "Inferred" : item.origin || "Inferred"}</span>
                          <button
    type="button"
    className="btn-subtle"
    style={{
      padding: "2px 6px",
      fontSize: 11,
      cursor: (item.evidence_refs?.length || 0) > 0 ? "pointer" : "default",
      color: "var(--accent)",
      border: "1px solid var(--border-soft)",
      borderRadius: "var(--radius-sm)",
      background: "var(--surface-2)",
      fontWeight: 600,
    }}
    onClick={() => openEvidenceDialogForClaim(item)}
    aria-label={`View ${item.evidence_refs?.length || 0} evidence references for ${item.name}`}
    disabled={!item.evidence_refs || item.evidence_refs.length === 0}
  >
    {item.evidence_refs?.length || 0} evidence refs
  </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </div>


      {/* Evidence Source Dialog for Derived Claims */}
      <SourceDialog
        open={sourceDialogOpen}
        onClose={() => setSourceDialogOpen(false)}
        attemptId={profile.creation?.attempt_id || profile.profile_id}
        title={activeClaimName ? `Evidence for "${activeClaimName}"` : "Referenced Evidence"}
        description="Approved baseline evidence supporting this derived claim."
        evidenceItems={activeReferencedEvidence}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(false)}
        title="Delete Archived Profile?"
        description="This will permanently delete the archived candidate profile. Profiles referenced by historical runs cannot be deleted."
        footer={
          <div style={{ display: "flex", gap: 10 }}>
            <Button variant="secondary" onClick={() => setDeleteConfirmOpen(false)} disabled={actionLoading}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleDelete} loading={actionLoading}>
              Delete permanently
            </Button>
          </div>
        }
      >
        <p style={{ margin: 0, fontSize: 13, color: "var(--text)" }}>
          Are you sure you want to delete profile <code>{profile.profile_id}</code> (
          <strong>{profile.display_name}</strong>)? This action cannot be undone.
        </p>
      </Dialog>
    </div>
  );
};
