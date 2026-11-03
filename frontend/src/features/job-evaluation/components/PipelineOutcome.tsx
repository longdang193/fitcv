import React from "react";
import { StatusBadge, StatusVariant } from "../../../components/status";
import { formatOutcomeCode, formatOutcomeReason } from "../../../lib/format";

export interface PipelineOutcomeProps {
  item: {
    result_bucket?: string | null;
    status?: string | null;
    outcome_code?: string | null;
    reason_code?: string | null;
    stage_outcome_reason?: string | null;
    evidence?: any;
    outcome?: any;
    fit_classification?: string | null;
    ranking_fit_label?: string | null;
    experience_evidence_summary?: any;
    latest_cv_review_state?: string | null;
    cv_review_state?: string | null;
  };
  showReviewTag?: boolean;
}

export const PipelineOutcome: React.FC<PipelineOutcomeProps> = ({ item, showReviewTag = false }) => {
  const isPassed = item.result_bucket === "passed" || item.status === "passed";
  const isRejected = item.result_bucket === "rejected" || item.status === "rejected";
  const isSkipped = item.result_bucket === "skipped" || item.status === "skipped";

  const badgeStatus: StatusVariant = isPassed
    ? "success"
    : isRejected
    ? "danger"
    : isSkipped
    ? "neutral"
    : item.status === "running"
    ? "info"
    : "neutral";

  const label =
    formatOutcomeCode(item.outcome_code) ||
    (isPassed
      ? "Passed"
      : isRejected
      ? "Rejected"
      : isSkipped
      ? "Skipped"
      : item.status
      ? item.status.charAt(0).toUpperCase() + item.status.slice(1)
      : "Pending");

  const reason = formatOutcomeReason(item);
  const evidence = item.evidence && typeof item.evidence === "object" ? item.evidence : {};
  const recommendation =
    item.fit_classification ||
    evidence.recommendation ||
    evidence.fit_classification ||
    item.outcome?.fit_classification;
  const evidenceSummary =
    item.experience_evidence_summary || evidence.experience_evidence_summary;
  const evidenceGaps = Array.isArray(evidenceSummary?.gaps) ? evidenceSummary.gaps : [];
  const evidenceVerdict = evidenceGaps.length
    ? `${evidenceGaps.length} experience evidence gap${evidenceGaps.length === 1 ? "" : "s"}`
    : evidenceSummary?.professional_experience?.verified_requirement_ids?.length
    ? "Professional experience verified"
    : null;
  const isStretch = Boolean(
    showReviewTag &&
      (item.latest_cv_review_state === "stretch" || (item as any).cv_review_state === "stretch")
  );

  return (
    <div className="pipeline-outcome">
      <StatusBadge status={badgeStatus} label={label} />
      {recommendation && <span className="recommendation-label">Recommendation: {recommendation}</span>}
      {evidenceVerdict && <span className="evidence-verdict">Evidence: {evidenceVerdict}</span>}
      {reason && <span className="outcome-reason">{reason}</span>}
      {isStretch && <span className="cv-review-tag">Stretch review</span>}
    </div>
  );
};
