import React, { useState, useEffect, useCallback } from "react";
import { PersonalizationCard } from "./components/PersonalizationCard";
import {
  activatePersonalizationCandidate,
  createPersonalizationCandidate,
  fetchPersonalization,
  fetchPersonalizationOptimization,
  patchPersonalization,
} from "./api";
import {
  PersonalizationOptimizationResource,
  PersonalizationResource,
  RankingMode,
} from "./types";
import { LoadingState, Dialog, Button } from "../../components";
import { notificationStore } from "../../lib/notifications";
import { ApiClientError } from "../../lib/api-client";

export const PersonalizationPage: React.FC = () => {
  const [personalization, setPersonalization] = useState<PersonalizationResource | null>(null);
  const [optimization, setOptimization] = useState<PersonalizationOptimizationResource | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [optimizationBusy, setOptimizationBusy] = useState(false);
  const [optimizationStatus, setOptimizationStatus] = useState<string | null>(null);
  const [actor, setActor] = useState("local operator");

  // Form state
  const [rankingMode, setRankingMode] = useState<RankingMode>("baseline");
  const [strength, setStrength] = useState<number>(0.05);

  // Conflict state
  const [conflictOpen, setConflictOpen] = useState(false);
  const [conflictMessage, setConflictMessage] = useState<string | null>(null);

  const loadPersonalizationData = useCallback(async () => {
    setLoading(true);
    try {
      const [{ resource }, optimizationResource] = await Promise.all([
        fetchPersonalization(),
        fetchPersonalizationOptimization(),
      ]);
      setPersonalization(resource);
      setOptimization(optimizationResource);
      setRankingMode(resource.ranking_mode);
      setStrength(resource.personalization_strength);
    } catch (err: any) {
      notificationStore.notify({
        dedupe: `req:load_personalization:${Date.now()}`,
        type: "error",
        title: "Failed to load personalization settings",
        message: err.message,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPersonalizationData();
  }, [loadPersonalizationData]);

  const handleReset = () => {
    if (!personalization) return;
    setRankingMode(personalization.ranking_mode);
    setStrength(personalization.personalization_strength);
  };

  const handleSave = async () => {
    if (!personalization) return;
    setSaving(true);

    try {
      const { resource } = await patchPersonalization({
        ranking_mode: rankingMode,
        personalization_strength: rankingMode === "personalized" ? strength : null,
        expected_revision: personalization.revision,
      });
      const optimizationResource = await fetchPersonalizationOptimization();

      setPersonalization(resource);
      setOptimization(optimizationResource);
      setRankingMode(resource.ranking_mode);
      setStrength(resource.personalization_strength);

      notificationStore.notify({
        dedupe: `action:save_personalization:${Date.now()}`,
        type: "success",
        title: "Personalization saved",
        message: `Ranking mode updated to ${resource.ranking_mode}.`,
      });
    } catch (err: any) {
      if (err instanceof ApiClientError && err.status === 409) {
        setConflictMessage(
          err.message || "Personalization settings were updated by another process since last read."
        );
        setConflictOpen(true);
      } else {
        notificationStore.notify({
          dedupe: `error:save_personalization:${Date.now()}`,
          type: "error",
          title: "Save failed",
          message: err.message || "Failed to update personalization settings.",
        });
      }
    } finally {
      setSaving(false);
    }
  };

  const handleReloadAfterConflict = async () => {
    setConflictOpen(false);
    await loadPersonalizationData();
  };

  const handleCreateCandidate = async () => {
    if (!optimization) return;
    setOptimizationBusy(true);
    setOptimizationStatus(null);
    try {
      const resource = await createPersonalizationCandidate({
        expected_evidence_head_fingerprint: optimization.evidence_head_fingerprint,
        expected_parent_ref: optimization.current_parent_ref,
      });
      setOptimization(resource);
      setOptimizationStatus(resource.message || "Candidate created. Activation remains manual.");
    } catch (err: any) {
      setOptimizationStatus(`${err.message || "Candidate creation failed."} (${err.code || "request_failed"})`);
      await loadPersonalizationData();
    } finally {
      setOptimizationBusy(false);
    }
  };

  const handleActivateCandidate = async () => {
    if (!optimization) return;
    const snapshotId =
      optimization.latest_candidate?.policy_snapshot_id || optimization.policy_snapshot_id;
    if (!snapshotId) return;
    setOptimizationBusy(true);
    setOptimizationStatus(null);
    try {
      const resource = await activatePersonalizationCandidate(snapshotId, {
        actor,
        expected_evidence_head_fingerprint: optimization.evidence_head_fingerprint,
        expected_parent_ref: optimization.current_parent_ref,
      });
      setOptimization(resource);
      setOptimizationStatus(resource.message || "Candidate activated.");
      await loadPersonalizationData();
    } catch (err: any) {
      setOptimizationStatus(`${err.message || "Candidate activation failed."} (${err.code || "request_failed"})`);
      await loadPersonalizationData();
    } finally {
      setOptimizationBusy(false);
    }
  };

  if (loading || !personalization) {
    return <LoadingState message="Loading personalization settings..." />;
  }

  const hasChanges =
    rankingMode !== personalization.ranking_mode ||
    (rankingMode === "personalized" && strength !== personalization.personalization_strength);

  return (
    <div className="content-container">
      {/* Page Header */}
      <div className="page-head" style={{ marginBottom: 24 }}>
        <div>
          <p
            className="eyebrow"
            style={{
              color: "var(--accent)",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              margin: "0 0 4px",
            }}
          >
            Settings & Preferences
          </p>
          <h2
            style={{
              margin: 0,
              fontFamily: "var(--display-font)",
              fontSize: 24,
              letterSpacing: "-0.02em",
            }}
          >
            Personalization
          </h2>
          <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>
            Manage core ranking mode preferences and strength parameters with atomic CAS validation.
          </p>
        </div>
      </div>

      {/* Main Settings Card */}
      <PersonalizationCard
        personalization={personalization}
        rankingMode={rankingMode}
        strength={strength}
        onRankingModeChange={setRankingMode}
        onStrengthChange={setStrength}
        onSave={handleSave}
        onReset={handleReset}
        saving={saving}
        hasChanges={hasChanges}
        optimization={optimization}
        optimizationBusy={optimizationBusy}
        optimizationStatus={optimizationStatus}
        actor={actor}
        onActorChange={setActor}
        onCreateCandidate={handleCreateCandidate}
        onActivateCandidate={handleActivateCandidate}
      />

      {/* Conflict Dialog */}
      <Dialog
        open={conflictOpen}
        onClose={() => setConflictOpen(false)}
        title="Settings Conflict (409)"
        description={conflictMessage || "Settings changed since last read."}
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button variant="secondary" onClick={() => setConflictOpen(false)}>
              Dismiss
            </Button>
            <Button variant="primary" onClick={handleReloadAfterConflict}>
              Reload Latest Settings
            </Button>
          </div>
        }
      >
        <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
          To prevent overwriting newer updates, please reload the current configuration and apply your adjustments again.
        </p>
      </Dialog>
    </div>
  );
};

export const route = {
  id: "personalization",
  path: "#/settings/personalization",
  title: "Personalization",
  group: "settings" as const,
  order: 90,
  component: PersonalizationPage,
};

export default route;
