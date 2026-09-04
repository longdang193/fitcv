import React from "react";

export interface EvidenceReferenceButtonProps {
  referenceIds: string[];
  onOpen: () => void;
}

export const EvidenceReferenceButton: React.FC<EvidenceReferenceButtonProps> = ({
  referenceIds,
  onOpen,
}) => {
  const count = referenceIds.length;
  const references = referenceIds.join(", ");

  return (
    <button
      type="button"
      className="btn-subtle"
      onClick={onOpen}
      disabled={count === 0}
      aria-label={`View ${count} evidence references`}
      title={references || "No evidence references"}
      style={{
        fontSize: 11,
        padding: "2px 6px",
        cursor: count > 0 ? "pointer" : "default",
        color: count > 0 ? "var(--accent)" : "var(--muted)",
        border: "1px solid var(--border-soft)",
        borderRadius: "var(--radius-sm)",
        background: "var(--surface-2)",
        fontWeight: 600,
      }}
    >
      {count} evidence refs
    </button>
  );
};
