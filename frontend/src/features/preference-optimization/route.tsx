import React, { useState, useEffect, useCallback } from "react";
import {
  activatePersonalizationCandidate,
  createPersonalizationCandidate,
  fetchPersonalization,
  fetchPersonalizationOptimization,
  patchPersonalization,
} from "./api";
import {
  OptimizationRunItem,
  PersonalizationOptimizationResource,
  PersonalizationResource,
  RankingMode,
} from "./types";
import { LoadingState } from "../../components";
import { StrengthDialog } from "./components/StrengthDialog";
import { ConflictDialog } from "./components/ConflictDialog";
import { OptimizationEvidenceTable } from "./components/OptimizationEvidenceTable";
import { OptimizationRunsTable } from "./components/OptimizationRunsTable";
import { OptimizationDetailsView } from "./components/OptimizationDetailsView";
import { notificationStore } from "../../lib/notifications";
import { ApiClientError } from "../../lib/api-client";

function optimizationRunsFromResource(
  resource: PersonalizationOptimizationResource
): OptimizationRunItem[] {
  const candidate = resource.latest_candidate;
  const id = candidate?.policy_snapshot_id || resource.preference_optimization_run_id;
  if (!candidate || !id) return [];

  return [
    {
      id,
      policyVersionId: candidate.policy_snapshot_id || resource.policy_snapshot_id || null,
      createdAt: candidate.created_at || "—",
      strength: resource.personalization_strength,
      status: candidate.status || resource.status || "Unknown",
      comparisons: resource.rating_event_count,
      usage: candidate.policy_snapshot_id === resource.active_policy_id ? "Active" : "Inactive",
      runtimeCompatible: true,
    },
  ];
}

export const PreferenceOptimizationPage: React.FC = () => {
  const [personalization, setPersonalization] = useState<PersonalizationResource | null>(null);
  const [optimization, setOptimization] = useState<PersonalizationOptimizationResource | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [optimizationBusy, setOptimizationBusy] = useState(false);

  // Selected run for detail view
  const [selectedRunId, setSelectedRunId] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    const hash = window.location.hash || "";
    const p1 = "#/preference-optimization/";
    const p2 = "#preference-optimization/";
    if (hash.startsWith(p1)) return decodeURIComponent(hash.slice(p1.length));
    if (hash.startsWith(p2)) return decodeURIComponent(hash.slice(p2.length));
    return null;
  });

  // Current candidate summary from canonical optimization state.
  const [runsHistory, setRunsHistory] = useState<OptimizationRunItem[]>([]);

  // Dialog states
  const [strengthDialogOpen, setStrengthDialogOpen] = useState(false);
  const [conflictOpen, setConflictOpen] = useState(false);
  const [conflictMessage, setConflictMessage] = useState<string | null>(null);

  // Synchronize URL hash with selectedRunId
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash || "";
      const p1 = "#/preference-optimization/";
      const p2 = "#preference-optimization/";
      if (hash.startsWith(p1)) {
        setSelectedRunId(decodeURIComponent(hash.slice(p1.length)));
      } else if (hash.startsWith(p2)) {
        setSelectedRunId(decodeURIComponent(hash.slice(p2.length)));
      } else if (hash === "#/preference-optimization" || hash === "#preference-optimization") {
        setSelectedRunId(null);
      }
    };
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [{ resource }, optResource] = await Promise.all([
        fetchPersonalization(),
        fetchPersonalizationOptimization(),
      ]);
      setPersonalization(resource);
      setOptimization(optResource);
      setRunsHistory(optimizationRunsFromResource(optResource));
    } catch (err: any) {
      notificationStore.notify({
        dedupe: `req:load_preference_optimization:${Date.now()}`,
        type: "error",
        title: "Failed to load preference optimization settings",
        message: err.message,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Ranking mode update handler
  const handleRankingModeChange = async (newMode: RankingMode) => {
    if (!personalization || saving) return;
    setSaving(true);
    try {
      const { resource } = await patchPersonalization({
        ranking_mode: newMode,
        personalization_strength:
          newMode === "personalized" ? personalization.personalization_strength : null,
        expected_revision: personalization.revision,
      });
      const optResource = await fetchPersonalizationOptimization();
      setPersonalization(resource);
      setOptimization(optResource);

      notificationStore.notify({
        dedupe: `action:ranking_mode:${Date.now()}`,
        type: "success",
        title: `${newMode === "personalized" ? "Personalized" : "Baseline"} Ranking selected`,
        message: `Ranking mode updated to ${newMode}.`,
      });
    } catch (err: any) {
      if (err instanceof ApiClientError && err.status === 409) {
        setConflictMessage(
          err.message || "Preference settings were updated by another process since last read."
        );
        setConflictOpen(true);
      } else {
        notificationStore.notify({
          dedupe: `error:ranking_mode:${Date.now()}`,
          type: "error",
          title: "Update failed",
          message: err.message || "Failed to update ranking mode.",
        });
      }
    } finally {
      setSaving(false);
    }
  };

  // Personalization Strength update handler
  const handleSaveStrength = async (newStrength: number) => {
    if (!personalization) return;
    setSaving(true);
    try {
      const { resource } = await patchPersonalization({
        ranking_mode: personalization.ranking_mode,
        personalization_strength: newStrength,
        expected_revision: personalization.revision,
      });
      const optResource = await fetchPersonalizationOptimization();
      setPersonalization(resource);
      setOptimization(optResource);

      notificationStore.notify({
        dedupe: `action:save_strength:${Date.now()}`,
        type: "success",
        title: "Personalization Strength saved",
        message: `Strength updated to ${newStrength.toFixed(2)}.`,
      });
    } catch (err: any) {
      if (err instanceof ApiClientError && err.status === 409) {
        setConflictMessage(
          err.message || "Preference settings were updated by another process since last read."
        );
        setConflictOpen(true);
      } else {
        notificationStore.notify({
          dedupe: `error:save_strength:${Date.now()}`,
          type: "error",
          title: "Save failed",
          message: err.message || "Failed to update personalization strength.",
        });
      }
    } finally {
      setSaving(false);
    }
  };

  // Start Optimization action
  const handleStartOptimization = async () => {
    if (!optimization || optimizationBusy) return;
    setOptimizationBusy(true);
    try {
      const optResource = await createPersonalizationCandidate({
        expected_evidence_head_fingerprint: optimization.evidence_head_fingerprint,
        expected_parent_ref: optimization.current_parent_ref,
      });
      setOptimization(optResource);
      setRunsHistory(optimizationRunsFromResource(optResource));

      const resultStatus = optResource.status;
      const resultNotice =
        resultStatus === "candidate_created"
          ? { type: "success" as const, title: "Optimization candidate created" }
          : resultStatus === "no_op"
          ? { type: "info" as const, title: "No preference change found" }
          : resultStatus === "evaluation_rejected"
          ? { type: "warning" as const, title: "Optimization candidate rejected" }
          : resultStatus === "insufficient_evidence"
          ? { type: "warning" as const, title: "More rating evidence needed" }
          : { type: "error" as const, title: "Optimization did not complete" };
      notificationStore.notify({
        dedupe: `action:start_optimization:${Date.now()}`,
        type: resultNotice.type,
        title: resultNotice.title,
        message: optResource.message || "Review current optimization state.",
      });
    } catch (err: any) {
      notificationStore.notify({
        dedupe: `error:start_optimization:${Date.now()}`,
        type: "error",
        title: "Optimization failed",
        message: err.message || "Failed to start optimization.",
      });
      await loadData();
    } finally {
      setOptimizationBusy(false);
    }
  };

  // Activate Candidate Policy action
  const handleActivatePolicy = async (run: OptimizationRunItem) => {
    if (!optimization || !run.policyVersionId) return;
    setOptimizationBusy(true);
    try {
      const optResource = await activatePersonalizationCandidate(run.policyVersionId, {
        actor: "local operator",
        expected_evidence_head_fingerprint: optimization.evidence_head_fingerprint,
        expected_parent_ref: optimization.current_parent_ref,
      });
      setOptimization(optResource);

      // If ranking mode was baseline, activate also sets ranking mode to personalized
      if (personalization && personalization.ranking_mode !== "personalized") {
        await patchPersonalization({
          ranking_mode: "personalized",
          personalization_strength: personalization.personalization_strength,
          expected_revision: personalization.revision,
        });
      }

      await loadData();

      notificationStore.notify({
        dedupe: `action:activate_policy:${Date.now()}`,
        type: "success",
        title: "Policy activated",
        message: `Policy ${run.policyVersionId} is now active.`,
      });
    } catch (err: any) {
      notificationStore.notify({
        dedupe: `error:activate_policy:${Date.now()}`,
        type: "error",
        title: "Activation failed",
        message: err.message || "Failed to activate candidate policy.",
      });
      await loadData();
    } finally {
      setOptimizationBusy(false);
    }
  };

  // Inactivate Policy action
  const handleInactivatePolicy = async (_run: OptimizationRunItem) => {
    // In canonical REST settings, setting mode to baseline inactivates personalized ranking
    if (!personalization) return;
    setSaving(true);
    try {
      const { resource } = await patchPersonalization({
        ranking_mode: "baseline",
        personalization_strength: personalization.personalization_strength,
        expected_revision: personalization.revision,
      });
      setPersonalization(resource);
      const optResource = await fetchPersonalizationOptimization();
      setOptimization(optResource);

      notificationStore.notify({
        dedupe: `action:inactivate_policy:${Date.now()}`,
        type: "info",
        title: "Policy inactivated",
        message: "Baseline Ranking is being used until another policy is activated.",
      });
    } catch (err: any) {
      notificationStore.notify({
        dedupe: `error:inactivate_policy:${Date.now()}`,
        type: "error",
        title: "Inactivation failed",
        message: err.message || "Failed to inactivate policy.",
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading || !personalization) {
    return <LoadingState message="Loading preference optimization settings..." />;
  }

  const personalized = personalization.ranking_mode === "personalized";
  const activePolicyId = personalization.active_policy_id || optimization?.active_policy_id || null;
  const activeOptimizationRun = runsHistory.find(
    (r) => r.policyVersionId && r.policyVersionId === activePolicyId
  );

  const strengthDisabled = !personalized || Boolean(activeOptimizationRun);
  const strengthReason = !personalized
    ? "Choose Personalized Ranking to manage this setting."
    : activeOptimizationRun
    ? "Inactivate Policy before changing Personalization Strength."
    : "";

  const optimizationActionsDisabled = !personalized;
  const optimizeReason = !personalized
    ? "Choose Personalized Ranking to optimize ratings."
    : "";

  const fallback =
    personalized && (!activePolicyId || personalization.baseline_fallback) ? (
      <p className="optimization-fallback">
        Baseline Ranking is being used until a policy is activated.
      </p>
    ) : null;

  // Render detail view if a run is selected
  if (selectedRunId) {
    const selectedItem = runsHistory.find((r) => r.id === selectedRunId);
    if (selectedItem) {
      return (
        <OptimizationDetailsView
          item={selectedItem}
          rankingMode={personalization.ranking_mode}
          activePolicyVersionId={activePolicyId}
          onBack={() => {
            setSelectedRunId(null);
            if (window.location.hash.includes("/")) {
              window.location.hash = "#/preference-optimization";
            }
          }}
          onActivatePolicy={handleActivatePolicy}
          onInactivatePolicy={handleInactivatePolicy}
          actionsDisabled={optimizationActionsDisabled}
        />
      );
    }
  }

  const bounds = personalization.bounds || { minimum: 0.01, maximum: 0.1, step: 0.01 };
  const evidenceSummary = {
    savedRatings: optimization?.rating_event_count ?? 0,
    episodes: optimization?.episode_count ?? 0,
  };
  const ratingEvidenceRows = optimization?.rating_evidence?.map((row) => ({
    ratedAt: row.rated_at,
    runId: row.run_id,
    job: row.job_label || row.alternative_id,
    savedRank: row.displayed_rank,
    baselineFit: row.baseline_fit,
    rating: row.rating,
  }));

  return (
    <div className="content-container">
      {/* Page Header */}
      <div className="page-head" style={{ marginBottom: 24 }}>
        <div>
          <p className="eyebrow">Pipeline</p>
          <h2>Preference Optimization</h2>
          <p>Choose ranking behavior, review saved ratings, and manage learned policies.</p>
        </div>
      </div>

      <div className="stack" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Section 1: Ranking Mode */}
        <details className="section-card collapsible-section setting-section" open>
          <summary>
            <span className="section-heading">
              <strong>Ranking Mode</strong>
              <span>Choose standard ranking or ranking adjusted by your saved ratings.</span>
            </span>
          </summary>
          <div className="section-content">
            <div className="settings-card" style={{ padding: "18px 22px" }}>
              <label
                className="row"
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}
              >
                <span>
                  <strong>Ranking Mode</strong>
                  <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>
                    Applies to future ranking runs across this workspace.
                  </p>
                </span>
                <span className="control">
                  <select
                    className="field preference-mode-field"
                    id="preferenceRankingMode"
                    aria-label="Ranking Mode"
                    value={personalization.ranking_mode}
                    onChange={(e) => handleRankingModeChange(e.target.value as RankingMode)}
                    disabled={saving}
                  >
                    <option value="baseline">Baseline Ranking</option>
                    <option value="personalized">Personalized Ranking</option>
                  </select>
                </span>
              </label>
            </div>
            {fallback}
          </div>
        </details>

        {/* Section 2: Personalization Strength */}
        <details className="section-card collapsible-section setting-section" open>
          <summary>
            <span className="section-heading">
              <strong>Personalization Strength</strong>
              <span>Controls how strongly saved ratings adjust job order.</span>
            </span>
          </summary>
          <div className="section-content settings-card" style={{ padding: "18px 22px" }}>
            <div
              className={`row ${strengthDisabled ? "is-disabled" : ""}`.trim()}
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}
            >
              <span>
                <strong>Personalization Strength</strong>
                <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>
                  Higher values allow larger changes from Baseline Ranking.
                </p>
                <p className="supporting-text" style={{ margin: "4px 0 0", fontSize: 12, color: "var(--muted)" }}>
                  Current value: {personalization.personalization_strength.toFixed(2)}
                </p>
                {strengthReason && (
                  <p
                    className="supporting-text"
                    id="personalizationStrengthDisabledReason"
                    style={{ margin: "4px 0 0", fontSize: 12, color: "var(--muted)" }}
                  >
                    {strengthReason}
                  </p>
                )}
              </span>
              <span className="control">
                <button
                  className="btn"
                  id="managePersonalizationStrength"
                  type="button"
                  disabled={strengthDisabled}
                  aria-describedby={strengthDisabled ? "personalizationStrengthDisabledReason" : undefined}
                  onClick={() => setStrengthDialogOpen(true)}
                >
                  Manage
                </button>
              </span>
            </div>
          </div>
        </details>

        {/* Section 3: Rating Evidence */}
        <details className="section-card collapsible-section setting-section" open>
          <summary>
            <span className="section-heading">
              <strong>Rating Evidence</strong>
              <span>Saved job ratings currently available for a new optimization.</span>
            </span>
          </summary>
          <div className="section-content">
            <div className="settings-card" style={{ padding: "18px 22px" }}>
              <div
                className="row"
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}
              >
                <span>
                  <strong>Saved Ratings</strong>
                  <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>
                    {evidenceSummary.savedRatings} ratings across {evidenceSummary.episodes} completed runs.
                  </p>
                  {optimizeReason && (
                    <p className="supporting-text" style={{ margin: "4px 0 0", fontSize: 12, color: "var(--muted)" }}>
                      {optimizeReason}
                    </p>
                  )}
                </span>
                <span className="control">
                  <button
                    className="btn primary"
                    id="optimizeCurrentRatings"
                    type="button"
                    disabled={
                      optimizationActionsDisabled ||
                      !optimization?.evidence_ready ||
                      optimizationBusy
                    }
                    onClick={handleStartOptimization}
                  >
                    {optimizationBusy ? "Optimizing…" : "Optimize Current Ratings"}
                  </button>
                </span>
              </div>
            </div>
            <OptimizationEvidenceTable rows={ratingEvidenceRows} savedRatingsCount={evidenceSummary.savedRatings} />
          </div>
        </details>

        {/* Section 4: Optimization Runs */}
        <details className="section-card collapsible-section setting-section" open>
          <summary>
            <span className="section-heading">
              <strong>Optimization Runs</strong>
              <span>Review results and manage the policy created by each run.</span>
            </span>
          </summary>
          <div className="section-content">
            <OptimizationRunsTable
              runs={runsHistory}
              rankingMode={personalization.ranking_mode}
              activePolicyVersionId={activePolicyId}
              onSelectRun={(id) => {
                setSelectedRunId(id);
                window.location.hash = `#/preference-optimization/${encodeURIComponent(id)}`;
              }}
              onActivatePolicy={handleActivatePolicy}
              onInactivatePolicy={handleInactivatePolicy}
              actionsDisabled={optimizationActionsDisabled}
            />
          </div>
        </details>
      </div>

      {/* Strength Dialog */}
      <StrengthDialog
        open={strengthDialogOpen}
        onClose={() => setStrengthDialogOpen(false)}
        currentStrength={personalization.personalization_strength}
        bounds={bounds}
        onSave={handleSaveStrength}
        saving={saving}
      />

      {/* Conflict Dialog */}
      <ConflictDialog
        open={conflictOpen}
        onClose={() => setConflictOpen(false)}
        onReload={async () => {
          setConflictOpen(false);
          await loadData();
        }}
        message={conflictMessage}
      />
    </div>
  );
};

export const route = {
  id: "preference-optimization",
  path: "#/preference-optimization",
  title: "Preference Optimization",
  group: "settings" as const,
  order: 90,
  component: PreferenceOptimizationPage,
};

export default route;
