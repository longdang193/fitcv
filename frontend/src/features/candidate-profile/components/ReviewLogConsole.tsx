import React, { useState } from "react";

export interface ReviewLogConsoleProps {
  stage: "baseline" | "derived" | "confirmation";
  attemptId: string;
  statusMessage: string;
  revision?: number;
  fingerprint?: string;
  baselineFingerprint?: string;
  derivedFingerprint?: string;
}

const stageLabels = {
  baseline: "Baseline review",
  derived: "Derived review",
  confirmation: "Confirmation",
} as const;

export const ReviewLogConsole: React.FC<ReviewLogConsoleProps> = ({
  stage,
  attemptId,
  statusMessage,
  revision,
  fingerprint,
  baselineFingerprint,
  derivedFingerprint,
}) => {
  const [open, setOpen] = useState(false);
  const label = stageLabels[stage];

  return (
    <section className="table-card" style={{ marginTop: 24, overflow: "hidden" }} data-testid={`${stage}-review-log`}>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        style={{
          width: "100%",
          padding: "10px 14px",
          background: "var(--surface-2)",
          border: 0,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
          cursor: "pointer",
          textAlign: "left",
          color: "var(--text)",
        }}
      >
        <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          <strong style={{ fontSize: 12 }}>Review log</strong>
          <span style={{ marginLeft: 8, fontSize: 11, color: "var(--muted)" }}>
            {label} · {statusMessage} · {attemptId}{fingerprint ? ` · ${fingerprint}` : ""}
          </span>
        </span>
        <span style={{ flexShrink: 0, fontSize: 11, color: "var(--muted)" }}>{open ? "Hide" : "Show"}</span>
      </button>

      {open && (
        <div
          role="log"
          aria-label={`${label} traceability log`}
          style={{
            padding: "10px 14px",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "6px 16px",
            fontSize: 11,
            fontFamily: "var(--font-mono)",
            borderTop: "1px solid var(--border-soft)",
          }}
        >
          <div><span style={{ color: "var(--muted)" }}>STATUS </span>{statusMessage}</div>
          <div><span style={{ color: "var(--muted)" }}>ATTEMPT </span><code>{attemptId}</code></div>
          {revision !== undefined && <div><span style={{ color: "var(--muted)" }}>REVISION </span><code>{revision}</code></div>}
          {fingerprint && <div><span style={{ color: "var(--muted)" }}>FINGERPRINT </span><code>{fingerprint}</code></div>}
          {baselineFingerprint && <div><span style={{ color: "var(--muted)" }}>BASELINE </span><code>{baselineFingerprint}</code></div>}
          {derivedFingerprint && <div><span style={{ color: "var(--muted)" }}>DERIVED </span><code>{derivedFingerprint}</code></div>}
        </div>
      )}
    </section>
  );
};
