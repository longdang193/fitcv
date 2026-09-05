import React from "react";
import { OptimizationRunItem, RankingMode } from "../types";
import { formatTimestamp } from "../../../lib/format";

export interface OptimizationRunsTableProps {
  runs: OptimizationRunItem[];
  rankingMode: RankingMode;
  activePolicyVersionId: string | null;
  onActivatePolicy: (run: OptimizationRunItem) => void;
  onInactivatePolicy?: (run: OptimizationRunItem) => void;
  onRemoveRun?: (runId: string) => void;
  actionsDisabled?: boolean;
}

export const OptimizationRunsTable: React.FC<OptimizationRunsTableProps> = ({
  runs,
  rankingMode: _rankingMode,
  activePolicyVersionId,
  onActivatePolicy,
  onInactivatePolicy,
  onRemoveRun,
  actionsDisabled = false,
}) => {
  const visibleRuns = runs.filter((r) => !r.hiddenAt);

  return (
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Optimization runs table">
      <table className="run-table optimization-runs">
        <thead>
          <tr>
            <th>Optimization ID</th>
            <th>Created</th>
            <th>Strength</th>
            <th>Status</th>
            <th>Policy</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {visibleRuns.length > 0 ? (
            visibleRuns.map((item) => {
              const statusLabel = item.status === "candidate" ? "Candidate" : item.status;
              const active = item.policyVersionId && item.policyVersionId === activePolicyVersionId;
              const policy = active
                ? item.runtimeCompatible !== false
                  ? "Active"
                  : "Active · Not in use"
                : item.policyVersionId
                ? "Ready to activate"
                : "Not created";

              const removeDisabled = actionsDisabled || Boolean(active);
              const reason = actionsDisabled
                ? "Choose Personalized Ranking to use these actions."
                : active
                ? "Inactivate Policy before removing this run."
                : "";

              return (
                <tr key={item.id}>
                  <td>
                    <a
                      className="optimization-id-link run-id"
                      href={`#/preference-optimization/${encodeURIComponent(item.id)}`}
                      aria-label={`View details for ${item.id}`}
                    >
                      {item.id}
                    </a>
                  </td>
                  <td className="run-created">
                    {formatTimestamp(item.createdAt)}
                  </td>
                  <td>{item.strength.toFixed(2)}</td>
                  <td>
                    <span className="optimization-status" data-status={item.status}>
                      {statusLabel}
                    </span>
                  </td>
                  <td>{policy}</td>
                  <td>
                    <div className="job-action-row" style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      {(item.status === "Succeeded" || item.status === "candidate") && item.policyVersionId && (
                        <button
                          className="small-action"
                          type="button"
                          disabled={actionsDisabled}
                          onClick={() => {
                            if (active) {
                              onInactivatePolicy?.(item);
                            } else {
                              onActivatePolicy(item);
                            }
                          }}
                        >
                          {active ? "Inactivate Policy" : "Activate Policy"}
                        </button>
                      )}
                      {onRemoveRun && (
                        <button
                          className="small-action"
                          type="button"
                          disabled={removeDisabled}
                          onClick={() => onRemoveRun(item.id)}
                        >
                          Remove
                        </button>
                      )}
                    </div>
                    {reason && (
                      <p className="supporting-text" style={{ margin: "4px 0 0", fontSize: 11, color: "var(--muted)" }}>
                        {reason}
                      </p>
                    )}
                  </td>
                </tr>
              );
            })
          ) : (
            <tr>
              <td colSpan={6}>
                <div className="empty-state" style={{ textAlign: "center", padding: "32px 16px" }}>
                  <h3 style={{ margin: "0 0 4px", fontSize: 16 }}>No optimization runs</h3>
                  <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
                    Use Optimize Current Ratings to create one.
                  </p>
                </div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};
