import React from "react";
import { CvVersionResource } from "../types";
import { StatusBadge, StatusVariant } from "../../../components";
import { formatIdentifier, formatTimestamp } from "../../../lib/format";

export interface CvVersionHistoryProps {
  versions: CvVersionResource[];
  selectedVersionId: string | null;
  onSelectVersion: (versionId: string) => void;
  loading?: boolean;
}

function getStatusVariant(status: string): StatusVariant {
  switch (status) {
    case "generated":
      return "success";
    case "review_required":
      return "warn";
    case "pending":
    case "running":
      return "info";
    case "generation_failed":
    case "validation_failed":
    case "persistence_failed":
      return "danger";
    default:
      return "neutral";
  }
}

export const CvVersionHistory: React.FC<CvVersionHistoryProps> = ({
  versions,
  selectedVersionId,
  onSelectVersion,
  loading = false,
}) => {
  if (loading) {
    return (
      <div className="cv-version-history loading" style={{ padding: 16, color: "var(--muted)", fontSize: 13 }}>
        Loading version history...
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div className="cv-version-history empty" style={{ padding: 16, color: "var(--muted)", fontSize: 13 }}>
        No CV versions available.
      </div>
    );
  }

  return (
    <nav className="cv-version-history" aria-label="CV Version History">
      <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
        {versions.map((ver) => {
          const isSelected = ver.version_id === selectedVersionId;
          const createdDate = formatTimestamp(ver.created_at, "Unknown date");
          return (
            <li key={ver.version_id}>
              <button
                type="button"
                className={`cv-version-item ${isSelected ? "is-selected" : ""}`}
                onClick={() => onSelectVersion(ver.version_id)}
                aria-current={isSelected ? "true" : undefined}
                style={{
                  width: "100%",
                  textAlign: "left",
                  padding: "12px 14px",
                  border: isSelected ? "2px solid var(--accent)" : "1px solid var(--border)",
                  borderRadius: "var(--radius-md)",
                  background: isSelected ? "var(--accent-soft)" : "var(--surface)",
                  cursor: "pointer",
                  display: "grid",
                  gap: 6,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                  <strong style={{ fontSize: 13 }}>
                    v{ver.ordinal || 1} · <span title={ver.version_id}>{formatIdentifier(ver.version_id)}</span>
                  </strong>
                  <StatusBadge
                    status={getStatusVariant(ver.generation_status)}
                    label={ver.generation_status}
                  />
                </div>

                <div style={{ fontSize: 11, color: "var(--muted)", display: "flex", justifyContent: "space-between" }}>
                  <span>{createdDate}</span>
                  {ver.parent_cv_version_id && (
                    <span title={`Parent: ${ver.parent_cv_version_id}`}>
                      ↳ from {ver.parent_cv_version_id.slice(0, 6)}
                    </span>
                  )}
                </div>

                {ver.review_state && ver.review_state !== "none" && (
                  <div style={{ fontSize: 11, color: "var(--text)" }}>
                    Review: <span className="cv-review-badge">{ver.review_state}</span>
                  </div>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
};
