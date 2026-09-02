import React from "react";
import { StatusBadge, Button } from "../../../components";
import {
  PersonalizationOptimizationResource,
  PersonalizationResource,
  RankingMode,
} from "../types";

export interface PersonalizationCardProps {
  personalization: PersonalizationResource;
  rankingMode: RankingMode;
  strength: number;
  onRankingModeChange: (mode: RankingMode) => void;
  onStrengthChange: (strength: number) => void;
  onSave: () => void;
  onReset: () => void;
  saving?: boolean;
  hasChanges?: boolean;
  optimization?: PersonalizationOptimizationResource | null;
  optimizationBusy?: boolean;
  optimizationStatus?: string | null;
  actor?: string;
  onActorChange?: (actor: string) => void;
  onCreateCandidate?: () => void;
  onActivateCandidate?: () => void;
}

export const PersonalizationCard: React.FC<PersonalizationCardProps> = ({
  personalization,
  rankingMode,
  strength,
  onRankingModeChange,
  onStrengthChange,
  onSave,
  onReset,
  saving = false,
  hasChanges = false,
  optimization,
  optimizationBusy = false,
  optimizationStatus,
  actor = "",
  onActorChange,
  onCreateCandidate,
  onActivateCandidate,
}) => {
  const bounds = personalization.bounds || { minimum: 0.0, maximum: 1.0, step: 0.01 };

  return (
    <div className="table-card" style={{ padding: "24px", maxWidth: 780 }}>
      {/* Title & Effective Status */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 20,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <h3 style={{ margin: "0 0 4px", fontSize: 18 }}>Ranking Preference</h3>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
            Configure whether future job ranking incorporates learned candidate preferences.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>Effective Mode:</span>
          <StatusBadge
            status={
              personalization.effective_ranking_mode === "personalized"
                ? "info"
                : "neutral"
            }
            label={
              personalization.effective_ranking_mode === "personalized"
                ? "Personalized"
                : "Baseline"
            }
          />
        </div>
      </div>

      {/* Fallback Banner if personalized requested but fallback active */}
      {personalization.baseline_fallback && (
        <div
          className="notice warning"
          role="status"
          style={{
            marginBottom: 20,
            padding: "12px 14px",
            background: "var(--surface-2)",
            border: "1px solid var(--border-soft)",
            borderRadius: 8,
          }}
        >
          <strong style={{ display: "block", fontSize: 13, color: "var(--text)" }}>
            Baseline Fallback Active
          </strong>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>
            Personalized ranking is selected, but no compatible active optimization policy is currently available. The pipeline will truthfully use baseline ranking until a compatible policy exists.
          </span>
        </div>
      )}

      {optimization && rankingMode === "personalized" && (
        <div
          className="notice"
          role={optimizationStatus ? "alert" : "status"}
          style={{
            marginBottom: 20,
            padding: "12px 14px",
            border: "1px solid var(--border-soft)",
            borderRadius: 8,
          }}
        >
          <strong style={{ display: "block", fontSize: 13, color: "var(--text)" }}>
            Preference Evidence
          </strong>
          <span style={{ display: "block", fontSize: 12, color: "var(--muted)" }}>
            {optimization.episode_count} episode{optimization.episode_count === 1 ? "" : "s"} · {optimization.rating_event_count} rating event{optimization.rating_event_count === 1 ? "" : "s"}
          </span>
          <code style={{ display: "block", marginTop: 6, fontSize: 11 }}>
            Parent: {optimization.current_parent_ref}
          </code>
          {optimizationStatus && (
            <span style={{ display: "block", marginTop: 8, fontSize: 12 }}>
              {optimizationStatus}
            </span>
          )}
          {optimization.baseline_fallback && optimization.evidence_ready && onCreateCandidate && (
            <Button
              variant="secondary"
              onClick={onCreateCandidate}
              disabled={optimizationBusy}
              style={{ marginTop: 10 }}
            >
              {optimizationBusy ? "Creating..." : "Create Policy Candidate"}
            </Button>
          )}
          {optimization.policy_snapshot_id &&
            (optimization.status === "candidate_created" ||
              optimization.latest_candidate?.status === "candidate") &&
            onActivateCandidate && (
              <div style={{ display: "flex", alignItems: "end", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
                <label style={{ display: "grid", gap: 4, fontSize: 11, color: "var(--muted)" }}>
                  Actor
                  <input
                    value={actor}
                    onChange={(event) => onActorChange?.(event.target.value)}
                    disabled={optimizationBusy}
                    aria-label="Activation actor"
                    style={{ padding: "7px 8px", border: "1px solid var(--border)", borderRadius: 6 }}
                  />
                </label>
                <Button
                  variant="primary"
                  onClick={onActivateCandidate}
                  disabled={optimizationBusy || !actor.trim()}
                >
                  {optimizationBusy ? "Activating..." : "Activate Candidate"}
                </Button>
              </div>
            )}
        </div>
      )}

      {/* Form Controls */}
      <div style={{ display: "grid", gap: 20 }}>
        {/* Mode Radio Group */}
        <div>
          <label style={{ display: "block", fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
            Ranking Mode
          </label>
          <div style={{ display: "grid", gap: 10 }}>
            <label
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 10,
                padding: "12px 14px",
                border: "1px solid var(--border)",
                borderRadius: 8,
                cursor: "pointer",
                background: rankingMode === "baseline" ? "var(--surface-2)" : "transparent",
              }}
            >
              <input
                type="radio"
                name="ranking_mode"
                value="baseline"
                checked={rankingMode === "baseline"}
                onChange={() => onRankingModeChange("baseline")}
                style={{ marginTop: 2 }}
              />
              <div>
                <strong style={{ display: "block", fontSize: 14 }}>Baseline Ranking</strong>
                <span style={{ fontSize: 12, color: "var(--muted)" }}>
                  Order jobs strictly by objective qualification match and core fit factors.
                </span>
              </div>
            </label>

            <label
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 10,
                padding: "12px 14px",
                border: "1px solid var(--border)",
                borderRadius: 8,
                cursor: "pointer",
                background: rankingMode === "personalized" ? "var(--surface-2)" : "transparent",
              }}
            >
              <input
                type="radio"
                name="ranking_mode"
                value="personalized"
                checked={rankingMode === "personalized"}
                onChange={() => onRankingModeChange("personalized")}
                style={{ marginTop: 2 }}
              />
              <div>
                <strong style={{ display: "block", fontSize: 14 }}>Personalized Ranking</strong>
                <span style={{ fontSize: 12, color: "var(--muted)" }}>
                  Incorporate historical Application Interest patterns into job order. Suitability qualification is never modified.
                </span>
              </div>
            </label>
          </div>
        </div>

        {/* Strength Slider */}
        <div style={{ opacity: rankingMode === "baseline" ? 0.6 : 1, transition: "opacity 0.2s" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <label
              htmlFor="personalization-strength"
              style={{ fontWeight: 600, fontSize: 13 }}
            >
              Personalization Strength
            </label>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 600 }}>
              {strength.toFixed(2)}
            </span>
          </div>
          <input
            id="personalization-strength"
            type="range"
            min={bounds.minimum}
            max={bounds.maximum}
            step={bounds.step}
            value={strength}
            disabled={rankingMode === "baseline"}
            onChange={(e) => onStrengthChange(parseFloat(e.target.value))}
            style={{ width: "100%", accentColor: "var(--accent)" }}
          />
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: 11,
              color: "var(--muted)",
              marginTop: 4,
            }}
          >
            <span>Min ({bounds.minimum})</span>
            <span>Max ({bounds.maximum})</span>
          </div>
        </div>

        {/* Revision info */}
        <div
          style={{
            borderTop: "1px solid var(--border-soft)",
            paddingTop: 14,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: 12,
            color: "var(--muted)",
            flexWrap: "wrap",
            gap: 8,
          }}
        >
          <span>
            Revision: <strong style={{ fontFamily: "var(--font-mono)" }}>{personalization.revision}</strong>
          </span>
          {personalization.active_policy_id && (
            <span>
              Policy ID: <strong style={{ fontFamily: "var(--font-mono)" }}>{personalization.active_policy_id}</strong>
            </span>
          )}
        </div>

        {/* Action Footer */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 4 }}>
          {hasChanges && (
            <Button variant="secondary" onClick={onReset} disabled={saving}>
              Reset
            </Button>
          )}
          <Button
            variant="primary"
            onClick={onSave}
            disabled={saving || !hasChanges}
          >
            {saving ? "Saving..." : "Save Preferences"}
          </Button>
        </div>
      </div>
    </div>
  );
};
