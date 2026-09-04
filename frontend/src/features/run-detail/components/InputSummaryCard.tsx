import React from "react";
import { PipelineRunResource } from "../../runs/types";
import { formatIdentifier, formatTimestamp } from "../../../lib/format";

export interface InputSummaryCardProps {
  run: PipelineRunResource;
}

export const InputSummaryCard: React.FC<InputSummaryCardProps> = ({ run }) => {
  const input = run.input;
  let parsedProfile: Record<string, any> | null = null;
  let parsedSources: any[] = [];

  if (input?.candidate_profile_json) {
    try {
      parsedProfile = JSON.parse(input.candidate_profile_json);
    } catch {}
  }

  if (input?.jobs_input_manifest_json) {
    try {
      const manifest = JSON.parse(input.jobs_input_manifest_json);
      if (manifest.sources && Array.isArray(manifest.sources)) {
        parsedSources = manifest.sources;
      }
    } catch {}
  }

  const profileName = parsedProfile?.name || parsedProfile?.profile_name || input?.candidate_profile_source || "Default";
  const profileRevision = parsedProfile?.revision;
  const sourceKind = input?.jobs_input_source || "Upload";

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
        gap: 16,
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        padding: 16,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <strong style={{ fontSize: 14, color: "var(--text)" }}>Input Configuration</strong>
        <div style={{ fontSize: 13, color: "var(--muted)" }}>
          <strong>Profile:</strong> {profileName} {profileRevision ? `(Rev ${profileRevision})` : ""}
        </div>
        <div style={{ fontSize: 13, color: "var(--muted)" }}>
          <strong>Source Mode:</strong> {sourceKind}
        </div>
        {parsedSources && parsedSources.length > 0 && (
          <div style={{ fontSize: 12, color: "var(--muted)" }}>
            {parsedSources.map((s: any, idx: number) => (
              <div key={idx}>
                • {s.type === "scan" ? `Scan: ${s.scan_name || s.scan_id}` : `Upload: ${s.filename}`} ({s.record_count ?? 0} jobs)
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <strong style={{ fontSize: 14, color: "var(--text)" }}>Execution Timing</strong>
        <div style={{ fontSize: 13, color: "var(--muted)" }}>
          <strong>Created:</strong> {formatTimestamp(run.created_at)}
        </div>
        {run.started_at && (
          <div style={{ fontSize: 13, color: "var(--muted)" }}>
            <strong>Started:</strong> {formatTimestamp(run.started_at)}
          </div>
        )}
        {run.finished_at && (
          <div style={{ fontSize: 13, color: "var(--muted)" }}>
            <strong>Finished:</strong> {formatTimestamp(run.finished_at)}
          </div>
        )}
        <div style={{ fontSize: 12, color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
          ID: <span title={run.run_id}>{formatIdentifier(run.run_id)}</span>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <strong style={{ fontSize: 14, color: "var(--text)" }}>Result Counts</strong>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 13 }}>
          <div><strong>{run.counts.total}</strong> Total</div>
          <div style={{ color: "var(--success)" }}><strong>{run.counts.passed}</strong> Passed</div>
          <div style={{ color: "var(--danger)" }}><strong>{run.counts.rejected}</strong> Rejected</div>
          <div style={{ color: "var(--muted)" }}><strong>{run.counts.skipped}</strong> Skipped</div>
          {run.counts.cvs_generated > 0 && (
            <div style={{ color: "var(--info)" }}><strong>{run.counts.cvs_generated}</strong> CVs</div>
          )}
        </div>
      </div>
    </div>
  );
};
