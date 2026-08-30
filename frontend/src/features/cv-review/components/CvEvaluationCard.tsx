import React, { useState, useEffect } from "react";
import { CvVersionResource, CvReviewDecisionPayload } from "../types";
import { StatusBadge, StatusVariant, Button } from "../../../components";

export interface CvEvaluationCardProps {
  version: CvVersionResource | null;
  runId?: string;
  runJobId?: string;
  onReviewSubmit?: (decision: CvReviewDecisionPayload, ifMatch?: string | null) => Promise<{ etag?: string | null }>;
}

function getReviewVariant(state: string): StatusVariant {
  switch (state) {
    case "approved":
    case "accepted":
      return "success";
    case "review_required":
    case "stretch":
    case "potential":
      return "warn";
    case "rejected":
    case "blocked":
      return "danger";
    default:
      return "neutral";
  }
}

export const CvEvaluationCard: React.FC<CvEvaluationCardProps> = ({
  version,
  onReviewSubmit,
}) => {
  const [notes, setNotes] = useState<string>("");
  const [currentEtag, setCurrentEtag] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Reset / version-key notes and ETag state whenever selected version changes
  useEffect(() => {
    if (version) {
      setNotes(version.evaluation?.notes || "");
      setCurrentEtag(version.etag || version.content_checksum || null);
    } else {
      setNotes("");
      setCurrentEtag(null);
    }
  }, [version?.version_id, version?.etag, version?.content_checksum]);

  if (!version) {
    return null;
  }

  const evalData = version.evaluation;
  const reviewState = version.review_state || "none";

  const handleDecision = async (newState: string) => {
    if (!onReviewSubmit) return;
    setSubmitting(true);
    try {
      const result = await onReviewSubmit(
        { review_state: newState, notes },
        currentEtag
      );
      // Preserve / update returned ETag for next CAS mutation
      if (result?.etag) {
        setCurrentEtag(result.etag);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section
      className="cv-evaluation-card"
      aria-labelledby="cv-eval-title"
      key={version.version_id}
      style={{
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        background: "var(--surface)",
        padding: "18px 20px",
        display: "grid",
        gap: 14,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div>
          <h3 id="cv-eval-title" style={{ margin: 0, fontSize: 15 }}>
            Evaluation & Review Truth
          </h3>
          <p style={{ margin: "2px 0 0", color: "var(--muted)", fontSize: 12 }}>
            Independent review state for immutable version {version.version_id.slice(0, 8)}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {evalData?.fit_classification && (
            <StatusBadge
              status={getReviewVariant(evalData.fit_classification)}
              label={`Fit: ${evalData.fit_classification}`}
            />
          )}
          <StatusBadge
            status={getReviewVariant(reviewState)}
            label={`Review: ${reviewState}`}
          />
        </div>
      </div>

      {evalData ? (
        <div style={{ display: "grid", gap: 12 }}>
          {evalData.recommendation && (
            <div style={{ padding: "10px 12px", background: "var(--surface-2)", borderRadius: "var(--radius-md)" }}>
              <strong style={{ fontSize: 12, display: "block", color: "var(--muted)", marginBottom: 4 }}>
                Recommendation
              </strong>
              <p style={{ margin: 0, fontSize: 13 }}>{evalData.recommendation}</p>
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
            {Array.isArray(evalData.strengths) && evalData.strengths.length > 0 && (
              <div>
                <strong style={{ fontSize: 12, color: "var(--success)", display: "block", marginBottom: 4 }}>
                  Strengths ({evalData.strengths.length})
                </strong>
                <ul className="cv-evaluation-list" style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text)" }}>
                  {evalData.strengths.map((s, idx) => (
                    <li key={`str-${idx}`}>{s}</li>
                  ))}
                </ul>
              </div>
            )}

            {Array.isArray(evalData.weaknesses) && evalData.weaknesses.length > 0 && (
              <div>
                <strong style={{ fontSize: 12, color: "var(--danger)", display: "block", marginBottom: 4 }}>
                  Weaknesses ({evalData.weaknesses.length})
                </strong>
                <ul className="cv-evaluation-list" style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text)" }}>
                  {evalData.weaknesses.map((w, idx) => (
                    <li key={`weak-${idx}`}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div style={{ fontSize: 12, color: "var(--muted)" }}>
          No structured evaluation record attached to this CV version.
        </div>
      )}

      {/* Interactive Review Decision & Notes */}
      {onReviewSubmit && (
        <div style={{ borderTop: "1px solid var(--border-soft)", paddingTop: 14, display: "grid", gap: 10 }}>
          <label htmlFor={`cv-notes-${version.version_id}`} style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)" }}>
            Review Notes (v{version.ordinal || 1})
          </label>
          <textarea
            id={`cv-notes-${version.version_id}`}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add reviewer notes or feedback for this CV version..."
            rows={2}
            className="field-input"
            style={{ fontSize: 12, resize: "vertical" }}
          />

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Button
              variant="primary"
              size="compact"
              onClick={() => handleDecision("approved")}
              disabled={submitting}
            >
              Approve CV
            </Button>
            <Button
              variant="secondary"
              size="compact"
              onClick={() => handleDecision("stretch")}
              disabled={submitting}
            >
              Mark Stretch
            </Button>
            <Button
              variant="secondary"
              size="compact"
              onClick={() => handleDecision("rejected")}
              disabled={submitting}
            >
              Reject CV
            </Button>
          </div>
        </div>
      )}
    </section>
  );
};
