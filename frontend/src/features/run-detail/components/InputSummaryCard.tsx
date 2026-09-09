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

  const candidateProfileObj = (input as any)?.candidate_profile;
  const profileName =
    candidateProfileObj?.name ||
    parsedProfile?.name ||
    parsedProfile?.profile_name ||
    input?.candidate_profile_name ||
    input?.candidate_profile_source ||
    "Default";
  const profileRevision = parsedProfile?.revision ?? input?.candidate_profile_revision;
  const profileIdValue =
    candidateProfileObj?.profile_id ||
    (input?.candidate_profile_id as string | undefined) ||
    (input?.profile_id as string | undefined) ||
    parsedProfile?.candidate_profile_id ||
    parsedProfile?.profile_id ||
    parsedProfile?.id ||
    (typeof input?.candidate_profile_source === "string" &&
    input.candidate_profile_source !== "default_config" &&
    input.candidate_profile_source !== "Upload"
      ? input.candidate_profile_source
      : undefined);
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
      <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
        <strong style={{ fontSize: 14, color: "var(--text)" }}>Input Configuration</strong>
        <div style={{ fontSize: 13, color: "var(--muted)", overflowWrap: "anywhere", wordBreak: "break-word" }}>
          <span style={{ fontWeight: 600 }}>Profile:</span>{" "}
          {profileIdValue ? (
            <a
              href={`#/candidate-profile/${encodeURIComponent(String(profileIdValue))}`}
              className="run-id-link"
              aria-label={`Open candidate profile ${profileName}`}
            >
              {profileName}
            </a>
          ) : (
            <span>{profileName}</span>
          )}{" "}
          {profileRevision ? `(Rev ${profileRevision})` : ""}
        </div>
        {profileIdValue && (
          <div style={{ fontSize: 13, color: "var(--muted)", overflowWrap: "anywhere", wordBreak: "break-word" }}>
            <span style={{ fontWeight: 600 }}>Profile ID:</span>{" "}
            <a
              href={`#/candidate-profile/${encodeURIComponent(String(profileIdValue))}`}
              className="run-id-link"
              aria-label={`Open candidate profile with ID ${profileIdValue}`}
            >
              {profileIdValue}
            </a>
          </div>
        )}
        <div style={{ fontSize: 13, color: "var(--muted)", overflowWrap: "anywhere", wordBreak: "break-word" }}>
          <span style={{ fontWeight: 600 }}>Source Mode:</span> <span>{sourceKind}</span>
        </div>
        {parsedSources && parsedSources.length > 0 && (
          <div style={{ fontSize: 12, color: "var(--muted)", overflowWrap: "anywhere", wordBreak: "break-word" }}>
            {parsedSources.map((s: any, idx: number) => (
              <div key={idx} style={{ overflowWrap: "anywhere", wordBreak: "break-word" }}>
                • {s.type === "scan" ? `Scan: ${s.scan_name || s.scan_id}` : `Upload: ${s.filename}`} ({s.record_count ?? 0} jobs)
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
        <strong style={{ fontSize: 14, color: "var(--text)" }}>Execution Timing</strong>
        <div style={{ fontSize: 13, color: "var(--muted)", overflowWrap: "anywhere", wordBreak: "break-word" }}>
          <span style={{ fontWeight: 600 }}>Created:</span> <span>{formatTimestamp(run.created_at)}</span>
        </div>
        {run.started_at && (
          <div style={{ fontSize: 13, color: "var(--muted)", overflowWrap: "anywhere", wordBreak: "break-word" }}>
            <span style={{ fontWeight: 600 }}>Started:</span> <span>{formatTimestamp(run.started_at)}</span>
          </div>
        )}
        {run.finished_at && (
          <div style={{ fontSize: 13, color: "var(--muted)", overflowWrap: "anywhere", wordBreak: "break-word" }}>
            <span style={{ fontWeight: 600 }}>Finished:</span> <span>{formatTimestamp(run.finished_at)}</span>
          </div>
        )}
        <div style={{ fontSize: 12, color: "var(--muted)", fontFamily: "var(--font-mono)", overflowWrap: "anywhere", wordBreak: "break-word" }}>
          <span style={{ fontWeight: 600 }}>ID:</span> <span title={run.run_id}>{formatIdentifier(run.run_id)}</span>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
        <strong style={{ fontSize: 14, color: "var(--text)" }}>Result Counts</strong>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 13 }}>
          <div><span>{run.counts.total}</span> Total</div>
          <div style={{ color: "var(--success)" }}><span>{run.counts.passed}</span> Passed</div>
          <div style={{ color: "var(--danger)" }}><span>{run.counts.rejected}</span> Rejected</div>
          <div style={{ color: "var(--muted)" }}><span>{run.counts.skipped}</span> Skipped</div>
          {run.counts.cvs_generated > 0 && (
            <div style={{ color: "var(--info)" }}><span>{run.counts.cvs_generated}</span> CVs</div>
          )}
        </div>
      </div>
    </div>
  );
};
