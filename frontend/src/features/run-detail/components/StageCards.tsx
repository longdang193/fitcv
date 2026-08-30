import React from "react";
import { StatusBadge, StatusVariant } from "../../../components";
import { RunStageResource } from "../../runs/types";

export interface StageCardsProps {
  stages: RunStageResource[];
  selectedStage: string;
  onSelectStage: (stageId: string) => void;
}

const stageStatusMap: Record<string, { variant: StatusVariant; label: string }> = {
  pending: { variant: "neutral", label: "Pending" },
  running: { variant: "info", label: "Running" },
  succeeded: { variant: "success", label: "Succeeded" },
  warning: { variant: "warn", label: "Warning" },
  partial: { variant: "warn", label: "Partial" },
  failed: { variant: "danger", label: "Failed" },
  cancelled: { variant: "neutral", label: "Cancelled" },
  skipped: { variant: "neutral", label: "Skipped" },
};

export const StageCards: React.FC<StageCardsProps> = ({
  stages,
  selectedStage,
  onSelectStage,
}) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>Pipeline Stages</h2>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: 12,
        }}
      >
        {stages.map((st) => {
          const cfg = stageStatusMap[st.status] || {
            variant: "neutral" as StatusVariant,
            label: st.status,
          };
          const isSelected = selectedStage === st.stage_id;
          return (
            <button
              key={st.stage_id}
              type="button"
              onClick={() => {
                const next = isSelected ? "all" : st.stage_id;
                onSelectStage(next);
              }}
              style={{
                background: isSelected ? "var(--accent-soft)" : "var(--surface)",
                border: isSelected ? "2px solid var(--accent)" : "1px solid var(--border)",
                borderRadius: "var(--radius-md)",
                padding: "12px 10px",
                textAlign: "left",
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                transition: "border-color var(--motion-fast)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)" }}>
                  STAGE {st.ordinal}
                </span>
                <StatusBadge status={cfg.variant} label={cfg.label} />
              </div>
              <div style={{ fontWeight: 600, fontSize: 13, color: "var(--text)" }}>
                {st.label}
              </div>
              {st.recomputed_counts && (
                <div style={{ fontSize: 11, color: "var(--muted)" }}>
                  <span style={{ color: "var(--success)" }}>{st.recomputed_counts.passed} pass</span>
                  {" · "}
                  <span style={{ color: "var(--danger)" }}>{st.recomputed_counts.rejected} rej</span>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
