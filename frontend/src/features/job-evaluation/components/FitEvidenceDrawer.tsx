import React from "react";
import { Dialog, Button, StatusBadge } from "../../../components";
import { RunJobItem } from "../../runs/types";
import { formatFactorLabel, formatFactorValue, formatOutcomeReason } from "../../../lib/format";

export interface FitEvidenceDrawerProps {
  job: RunJobItem | null;
  open: boolean;
  onClose: () => void;
}

export const FitEvidenceDrawer: React.FC<FitEvidenceDrawerProps> = ({
  job,
  open,
  onClose,
}) => {
  if (!job) return null;

  const isPassed = job.result_bucket === "passed" || job.status === "passed";
  const rawAttributes = (job.attributes || {}) as Record<string, any>;
  const reasons: string[] = Array.isArray(rawAttributes.reasons)
    ? rawAttributes.reasons
    : rawAttributes.reason
    ? [String(rawAttributes.reason)]
    : [];

  const fitFactors = (rawAttributes.fit_factor_results || {}) as Record<
    string,
    any
  >;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={job.title || "Job Fit Evidence"}
      description={`${job.company || "Unknown Company"}${job.location ? ` · ${job.location}` : ""}`}
      footer={
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      }
    >
      <div style={{ display: "grid", gap: 16, fontSize: 14 }}>
        {/* Top summary row */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "12px 14px",
            background: "var(--surface-2)",
            borderRadius: 8,
            border: "1px solid var(--border-soft)",
          }}
        >
          <div>
            <span style={{ fontSize: 12, color: "var(--muted)", display: "block" }}>
              Pipeline Decision
            </span>
            <strong>Stage: {formatFactorLabel(job.current_stage_id) || "Screening"}</strong>
          </div>
          <StatusBadge
            status={isPassed ? "success" : "danger"}
            label={isPassed ? "Passed / Suitable" : "Rejected / Screened Out"}
          />
        </div>

        {/* Reasons block */}
        <div>
          <h4 style={{ margin: "0 0 6px", fontSize: 13, textTransform: "uppercase", color: "var(--muted)" }}>
            Qualification Evidence & Reasons
          </h4>
          {reasons.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 4 }}>
              {reasons.map((r, i) => (
                <li key={i}>{formatOutcomeReason(r) || r}</li>
              ))}
            </ul>
          ) : (
            <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
              {isPassed
                ? "Candidate qualifications satisfy all required evaluation factors for this stage."
                : "No explicit disqualification reason recorded."}
            </p>
          )}
        </div>

        {/* Fit factor breakdown if available */}
        {Object.keys(fitFactors).length > 0 && (
          <div>
            <h4 style={{ margin: "0 0 6px", fontSize: 13, textTransform: "uppercase", color: "var(--muted)" }}>
              Factor Breakdown
            </h4>
            <div style={{ display: "grid", gap: 8 }}>
              {Object.entries(fitFactors).map(([factorKey, factorVal]) => {
                const formatted = formatFactorValue(factorVal);
                const badgeColor =
                  formatted.variant === "success"
                    ? "var(--success)"
                    : formatted.variant === "danger"
                    ? "var(--danger)"
                    : "var(--muted)";
                return (
                  <div
                    key={factorKey}
                    style={{
                      padding: "8px 12px",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      background: "var(--surface)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 600 }}>
                      <span>{formatFactorLabel(factorKey)}</span>
                      <span style={{ fontSize: 12, color: badgeColor }}>
                        {formatted.label}
                      </span>
                    </div>
                    {formatted.reason && (
                      <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
                        {formatted.reason}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Job metadata attributes */}
        <div style={{ borderTop: "1px solid var(--border-soft)", paddingTop: 12 }}>
          <dl
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, 1fr)",
              gap: 8,
              margin: 0,
              fontSize: 12,
            }}
          >
            <div>
              <dt style={{ color: "var(--muted)", fontWeight: 600 }}>Job ID</dt>
              <dd style={{ margin: 0, fontFamily: "var(--font-mono)" }}>
                {job.job_id || job.run_job_id}
              </dd>
            </div>
            {job.location && (
              <div>
                <dt style={{ color: "var(--muted)", fontWeight: 600 }}>Location</dt>
                <dd style={{ margin: 0 }}>{job.location}</dd>
              </div>
            )}
            {rawAttributes.work_mode && (
              <div>
                <dt style={{ color: "var(--muted)", fontWeight: 600 }}>Work Mode</dt>
                <dd style={{ margin: 0 }}>{formatOutcomeReason(String(rawAttributes.work_mode)) || String(rawAttributes.work_mode)}</dd>
              </div>
            )}
            {rawAttributes.seniority && (
              <div>
                <dt style={{ color: "var(--muted)", fontWeight: 600 }}>Seniority</dt>
                <dd style={{ margin: 0 }}>{formatOutcomeReason(String(rawAttributes.seniority)) || String(rawAttributes.seniority)}</dd>
              </div>
            )}
          </dl>
        </div>
      </div>
    </Dialog>
  );
};
