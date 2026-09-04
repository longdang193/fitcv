import React, { useState } from "react";
import { OptimizationRunItem, RankingMode } from "../types";
import { OptimizationEvidenceTable } from "./OptimizationEvidenceTable";
import { Button } from "../../../components";

export interface OptimizationDetailsViewProps {
  item: OptimizationRunItem;
  rankingMode: RankingMode;
  activePolicyVersionId: string | null;
  onBack: () => void;
  onActivatePolicy: (run: OptimizationRunItem) => void;
  onInactivatePolicy?: (run: OptimizationRunItem) => void;
  actionsDisabled?: boolean;
}

export const OptimizationDetailsView: React.FC<OptimizationDetailsViewProps> = ({
  item,
  rankingMode,
  activePolicyVersionId,
  onBack,
  onActivatePolicy,
  onInactivatePolicy,
  actionsDisabled = false,
}) => {
  const [clearedConsole, setClearedConsole] = useState(false);

  const active = item.policyVersionId && item.policyVersionId === activePolicyVersionId;
  const policy = active
    ? item.runtimeCompatible !== false
      ? "Active"
      : "Active · Not in use"
    : item.policyVersionId
    ? "Ready to activate"
    : "Not created";

  const logs = clearedConsole ? [] : item.logs || [];

  return (
    <div className="content-container">
      <div className="details-page-head">
        <button
          type="button"
          className="details-page-back"
          onClick={onBack}
          style={{ background: "none", border: "none", color: "var(--accent)", cursor: "pointer", padding: "0 0 12px", display: "inline-flex", alignItems: "center", gap: 6, font: "inherit", fontWeight: 600 }}
        >
          &larr; Back to Preference Optimization
        </button>
        <div className="page-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
          <div>
            <p className="eyebrow" style={{ margin: "0 0 4px" }}>Preference Optimization</p>
            <h2 style={{ margin: 0, fontSize: 24 }}>Optimization {item.id}</h2>
            <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>
              Review saved inputs, rating evidence, and lifecycle events.
            </p>
          </div>
          <div className="run-selection-actions">
            {(item.status === "Succeeded" || item.status === "candidate") && item.policyVersionId && (
              <div className="optimization-policy-controls">
                <Button
                  variant={active ? "secondary" : "primary"}
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
                </Button>
                {actionsDisabled && (
                  <p className="supporting-text" style={{ margin: "4px 0 0", fontSize: 11, color: "var(--muted)" }}>
                    Choose Personalized Ranking to use this action.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
        {item.hiddenAt && (
          <p className="optimization-fallback">
            <strong>Removed from Optimization Runs</strong>
            <br />
            Historical details remain available.
          </p>
        )}
        {rankingMode === "personalized" && !active && (
          <p className="optimization-fallback">
            Baseline Ranking is being used until a policy is activated.
          </p>
        )}
      </div>

      <div className="stack" style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 20 }}>
        {/* Overview Section */}
        <details className="section-card collapsible-section drawer-section" open>
          <summary>
            <span className="section-heading">
              <strong>Overview</strong>
              <span>Saved result and inputs for this optimization.</span>
            </span>
            <span className="drawer-status">
              <span className="optimization-status" data-status={item.status}>
                {item.status}
              </span>
            </span>
          </summary>
          <div className="section-content drawer-section-content" style={{ padding: 20 }}>
            <dl className="details-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, margin: 0 }}>
              <div className="detail-item">
                <dt style={{ color: "var(--muted)", fontSize: 12 }}>Optimization ID</dt>
                <dd style={{ margin: "4px 0 0", fontWeight: 600, fontFamily: "var(--font-mono)" }}>{item.id}</dd>
              </div>
              <div className="detail-item">
                <dt style={{ color: "var(--muted)", fontSize: 12 }}>Status</dt>
                <dd style={{ margin: "4px 0 0", fontWeight: 600 }}>{item.status}</dd>
              </div>
              <div className="detail-item">
                <dt style={{ color: "var(--muted)", fontSize: 12 }}>Created</dt>
                <dd style={{ margin: "4px 0 0" }}>
                  {typeof item.createdAt === "number" ? new Date(item.createdAt).toLocaleString() : item.createdAt}
                </dd>
              </div>
              <div className="detail-item">
                <dt style={{ color: "var(--muted)", fontSize: 12 }}>Personalization Strength</dt>
                <dd style={{ margin: "4px 0 0" }}>{item.strength.toFixed(2)}</dd>
              </div>
              <div className="detail-item">
                <dt style={{ color: "var(--muted)", fontSize: 12 }}>Ratings Included</dt>
                <dd style={{ margin: "4px 0 0" }}>{item.evidence ? item.evidence.length : 0}</dd>
              </div>
              <div className="detail-item">
                <dt style={{ color: "var(--muted)", fontSize: 12 }}>Policy</dt>
                <dd style={{ margin: "4px 0 0" }}>{policy}</dd>
              </div>
            </dl>
          </div>
        </details>

        {/* Rating Evidence Section */}
        <details className="section-card collapsible-section drawer-section" open>
          <summary>
            <span className="section-heading">
              <strong>Rating Evidence</strong>
              <span>Historical ratings saved when this optimization ran.</span>
            </span>
          </summary>
          <div className="section-content">
            <OptimizationEvidenceTable rows={item.evidence} />
          </div>
        </details>

        {/* Console Log Section */}
        <details className="section-card collapsible-section drawer-section" open>
          <summary>
            <span className="section-heading">
              <strong>Console Log</strong>
              <span>Optimization lifecycle events.</span>
            </span>
          </summary>
          <div className="section-content drawer-section-content" style={{ padding: 20 }}>
            <div className="console-toolbar" style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
              <button
                className="small-action"
                type="button"
                disabled={clearedConsole || !item.logs || item.logs.length === 0}
                onClick={() => setClearedConsole(true)}
              >
                Clear
              </button>
            </div>
            <div
              className="console-log"
              role="log"
              aria-live="polite"
              aria-label={`Console log for ${item.id}`}
              style={{ maxHeight: 280, overflowY: "auto", background: "var(--surface-2)", padding: 12, borderRadius: 6, fontFamily: "var(--font-mono)", fontSize: 12 }}
            >
              {logs.length > 0 ? (
                logs.map((event, idx) => (
                  <div key={idx} className="console-line" data-level={event.level} style={{ display: "flex", gap: 12, padding: "2px 0" }}>
                    <span className="console-time" style={{ color: "var(--muted)" }}>
                      {new Date(event.recordedAt).toISOString()}
                    </span>
                    <span className="console-level" data-level={event.level} style={{ fontWeight: 600 }}>
                      {event.level.toUpperCase()}
                    </span>
                    <span className="console-message">{event.message}</span>
                  </div>
                ))
              ) : (
                <div className="console-empty" style={{ color: "var(--muted)", fontStyle: "italic" }}>
                  No console events in current view.
                </div>
              )}
            </div>
          </div>
        </details>
      </div>
    </div>
  );
};
