import React from "react";

export type CreationStage = "upload" | "baseline" | "derived" | "confirm";

export interface CreationStepperProps {
  currentStage: CreationStage;
  onStepClick?: (stage: CreationStage) => void;
}

const STEPS: Array<{ id: CreationStage; stepNumber: number; label: string; description: string }> = [
  { id: "upload", stepNumber: 1, label: "Upload", description: "Source document" },
  { id: "baseline", stepNumber: 2, label: "Baseline Evidence", description: "Direct facts & citations" },
  { id: "derived", stepNumber: 3, label: "Controlled Derivation", description: "Traceable claims" },
  { id: "confirm", stepNumber: 4, label: "Confirmation", description: "Review & publish" },
];

export const CreationStepper: React.FC<CreationStepperProps> = ({ currentStage }) => {
  const currentIdx = STEPS.findIndex((s) => s.id === currentStage);

  return (
    <nav className="creation-stepper" aria-label="Creation progress" style={{ margin: "16px 0 24px" }}>
      <ol
        style={{
          display: "flex",
          listStyle: "none",
          margin: 0,
          padding: 0,
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        {STEPS.map((step, idx) => {
          const isCurrent = step.id === currentStage;
          const isCompleted = idx < currentIdx;

          return (
            <li
              key={step.id}
              style={{
                flex: "1 1 180px",
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                border: isCurrent
                  ? "1px solid var(--accent)"
                  : isCompleted
                  ? "1px solid var(--border)"
                  : "1px solid var(--border-soft)",
                background: isCurrent
                  ? "var(--accent-soft)"
                  : isCompleted
                  ? "var(--surface-2)"
                  : "var(--surface)",
                transition: "all var(--motion-fast)",
              }}
              aria-current={isCurrent ? "step" : undefined}
            >
              <div
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: "var(--radius-pill)",
                  display: "grid",
                  placeItems: "center",
                  fontSize: 12,
                  fontWeight: 700,
                  background: isCurrent
                    ? "var(--accent)"
                    : isCompleted
                    ? "var(--success)"
                    : "var(--border)",
                  color: isCurrent || isCompleted ? "#ffffff" : "var(--muted)",
                }}
              >
                {isCompleted ? "✓" : step.stepNumber}
              </div>
              <div style={{ minWidth: 0 }}>
                <strong
                  style={{
                    display: "block",
                    fontSize: 13,
                    color: isCurrent ? "var(--accent)" : "var(--text)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {step.label}
                </strong>
                <span
                  style={{
                    display: "block",
                    fontSize: 11,
                    color: "var(--muted)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {step.description}
                </span>
              </div>
            </li>
          );
        })}
      </ol>
    </nav>
  );
};
