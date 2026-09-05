import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchPersonalization,
  patchPersonalization,
  fetchPersonalizationOptimization,
  createPersonalizationCandidate,
  activatePersonalizationCandidate,
} from "../features/preference-optimization/api";
import { apiClient, ApiClientError } from "../lib/api-client";
import { formatTimestamp } from "../lib/format";
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";
import { OptimizationRunsTable } from "../features/preference-optimization/components/OptimizationRunsTable";
import { OptimizationEvidenceTable } from "../features/preference-optimization/components/OptimizationEvidenceTable";
import { OptimizationDetailsView } from "../features/preference-optimization/components/OptimizationDetailsView";
import { StrengthDialog } from "../features/preference-optimization/components/StrengthDialog";

describe("preference optimization slice and api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("registers and matches preference-optimization feature route, plus legacy personalization aliases", () => {
    const routes = discoverFeatureRoutes();
    const optRoute = routes.find((r) => r.id === "preference-optimization");
    expect(optRoute).toBeDefined();
    expect(optRoute?.path).toBe("#/preference-optimization");
    expect(optRoute?.group).toBe("settings");
    expect(optRoute?.title).toBe("Preference Optimization");

    // Exact matches
    expect(matchRoute("#/preference-optimization", routes).id).toBe("preference-optimization");
    expect(matchRoute("#preference-optimization", routes).id).toBe("preference-optimization");

    // Subpaths
    expect(matchRoute("#/preference-optimization/por_20260904_01", routes).id).toBe("preference-optimization");
    expect(matchRoute("#preference-optimization/por_20260904_01", routes).id).toBe("preference-optimization");

    // Legacy aliases
    expect(matchRoute("#/settings/preference-optimization", routes).id).toBe("preference-optimization");
    expect(matchRoute("#/settings/personalization", routes).id).toBe("preference-optimization");
    expect(matchRoute("#personalization", routes).id).toBe("preference-optimization");
    expect(matchRoute("#/personalization", routes).id).toBe("preference-optimization");
  });

  it("fetches personalization resource with ETag and fallback status", async () => {
    const mockData = {
      data: {
        data: {
          ranking_mode: "personalized",
          effective_ranking_mode: "baseline",
          personalization_strength: 0.05,
          baseline_fallback: true,
          active_policy_id: null,
          revision: "rev-snapshot-123",
          bounds: { minimum: 0.01, maximum: 0.1, step: 0.01 },
        },
      },
      etag: '"rev-snapshot-123"',
      status: 200,
    };

    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockData as any);

    const { resource, etag } = await fetchPersonalization();
    expect(getSpy).toHaveBeenCalledWith("/personalization");
    expect(resource.ranking_mode).toBe("personalized");
    expect(resource.effective_ranking_mode).toBe("baseline");
    expect(resource.baseline_fallback).toBe(true);
    expect(etag).toBe('"rev-snapshot-123"');
  });

  it("patches personalization resource with CAS revision check", async () => {
    const mockUpdated = {
      data: {
        data: {
          ranking_mode: "baseline",
          effective_ranking_mode: "baseline",
          personalization_strength: 0.05,
          baseline_fallback: false,
          active_policy_id: null,
          revision: "rev-snapshot-456",
          bounds: { minimum: 0.01, maximum: 0.1, step: 0.01 },
        },
      },
      etag: '"rev-snapshot-456"',
      status: 200,
    };

    const patchSpy = vi.spyOn(apiClient, "patch").mockResolvedValueOnce(mockUpdated as any);

    const { resource, etag } = await patchPersonalization({
      ranking_mode: "baseline",
      personalization_strength: null,
      expected_revision: "rev-snapshot-123",
    });

    expect(patchSpy).toHaveBeenCalledWith("/personalization", {
      ranking_mode: "baseline",
      personalization_strength: null,
      expected_revision: "rev-snapshot-123",
    });
    expect(resource.ranking_mode).toBe("baseline");
    expect(resource.revision).toBe("rev-snapshot-456");
    expect(etag).toBe('"rev-snapshot-456"');
  });

  it("propagates 409 conflict error on stale revision", async () => {
    vi.spyOn(apiClient, "patch").mockRejectedValueOnce(
      new ApiClientError(
        409,
        "personalization_revision_conflict",
        "Personalization changed since last read.",
        "Reload Personalization and retry."
      )
    );

    await expect(
      patchPersonalization({
        ranking_mode: "personalized",
        personalization_strength: 0.08,
        expected_revision: "stale-rev",
      })
    ).rejects.toThrow("Personalization changed since last read.");
  });

  it("loads optimization evidence and parent compare state", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: {
        data: {
          domain_id: "ranking_v1",
          ranking_mode: "personalized",
          effective_ranking_mode: "baseline",
          personalization_strength: 0.05,
          baseline_fallback: true,
          active_policy_id: null,
          settings_revision: "settings-1",
          evidence_head_fingerprint: "evidence-1",
          evidence_ready: true,
          episode_count: 2,
          rating_event_count: 3,
          current_parent_ref: "zero_residual:baseline",
          latest_candidate: null,
          candidate_activation_eligible: false,
          status: null,
          error_code: null,
          message: null,
        },
      },
      status: 200,
    } as any);

    const resource = await fetchPersonalizationOptimization();
    expect(getSpy).toHaveBeenCalledWith("/personalization/optimization");
    expect(resource.evidence_ready).toBe(true);
    expect(resource.current_parent_ref).toBe("zero_residual:baseline");
  });

  it("creates and activates a candidate with CAS tokens and actor", async () => {
    const postSpy = vi.spyOn(apiClient, "post")
      .mockResolvedValueOnce({
        data: { data: { status: "candidate_created", policy_snapshot_id: "snapshot-1" } },
        status: 200,
      } as any)
      .mockResolvedValueOnce({
        data: { data: { status: "activation_completed", policy_snapshot_id: "snapshot-1" } },
        status: 200,
      } as any);

    await createPersonalizationCandidate({
      expected_evidence_head_fingerprint: "evidence-1",
      expected_parent_ref: "zero_residual:baseline",
    });
    await activatePersonalizationCandidate("snapshot-1", {
      actor: "local operator",
      expected_evidence_head_fingerprint: "evidence-1",
      expected_parent_ref: "zero_residual:baseline",
    });

    expect(postSpy).toHaveBeenNthCalledWith(
      1,
      "/personalization/optimization/candidate",
      {
        expected_evidence_head_fingerprint: "evidence-1",
        expected_parent_ref: "zero_residual:baseline",
      }
    );
    expect(postSpy).toHaveBeenNthCalledWith(
      2,
      "/personalization/optimization/candidates/snapshot-1/activate",
      {
        actor: "local operator",
        expected_evidence_head_fingerprint: "evidence-1",
        expected_parent_ref: "zero_residual:baseline",
      }
    );
  });

  it("renders truthful empty states for Rating Evidence and Optimization Runs tables", () => {
    const evidenceMarkup = renderToStaticMarkup(
      React.createElement(OptimizationEvidenceTable, { rows: [] })
    );
    expect(evidenceMarkup).toContain("No saved ratings");
    expect(evidenceMarkup).toContain("Ratings from completed runs will appear here.");

    const runsMarkup = renderToStaticMarkup(
      React.createElement(OptimizationRunsTable, {
        runs: [],
        rankingMode: "personalized",
        activePolicyVersionId: null,
        onActivatePolicy: () => {},
      })
    );
    expect(runsMarkup).toContain("No optimization runs");
    expect(runsMarkup).toContain("Use Optimize Current Ratings to create one.");
  });

  it("renders optimization runs with active status and details view", () => {
    const sampleRun = {
      id: "por_20260904_01",
      policyVersionId: "RP-20260904-01",
      createdAt: 1788549600000,
      strength: 0.05,
      status: "Succeeded",
      runtimeCompatible: true,
      logs: [
        {
          recordedAt: 1788549600000,
          level: "info",
          operation: "optimization",
          message: "Started preference optimization.",
        },
      ],
    };

    const runsMarkup = renderToStaticMarkup(
      React.createElement(OptimizationRunsTable, {
        runs: [sampleRun],
        rankingMode: "personalized",
        activePolicyVersionId: "RP-20260904-01",
        onActivatePolicy: () => {},
      })
    );
    expect(runsMarkup).toContain("por_20260904_01");
    expect(runsMarkup).toContain("Succeeded");
    expect(runsMarkup).toContain("Active");
    expect(runsMarkup).toContain("Inactivate Policy");
    expect(runsMarkup).toContain('href="#/preference-optimization/por_20260904_01"');
    expect(runsMarkup).toContain(formatTimestamp(sampleRun.createdAt));
    expect(runsMarkup).toContain('role="region"');
    expect(runsMarkup).toContain('aria-label="Optimization runs table"');

    const detailsMarkup = renderToStaticMarkup(
      React.createElement(OptimizationDetailsView, {
        item: sampleRun,
        rankingMode: "personalized",
        activePolicyVersionId: "RP-20260904-01",
        onBack: () => {},
        onActivatePolicy: () => {},
      })
    );
    expect(detailsMarkup).toContain("Optimization por_20260904_01");
    expect(detailsMarkup).toContain("Overview");
    expect(detailsMarkup).toContain("Console Log");
    expect(detailsMarkup).toContain("Started preference optimization.");
    expect(detailsMarkup).toContain(formatTimestamp(sampleRun.createdAt));
    expect(detailsMarkup).toContain(formatTimestamp(sampleRun.logs[0].recordedAt));
    expect(detailsMarkup).toContain('aria-label="Optimization rating evidence table"');
  });


  it("renders canonical row-level rating evidence when present in OptimizationEvidenceTable", () => {
    const sampleRows = [
      {
        ratedAt: "2026-07-16T12:00:00Z",
        runId: "run-42",
        job: "Senior Platform Engineer",
        jobUrl: "https://jobs.example.test/42",
        savedRank: 1,
        baselineFit: 0.952,
        rating: 5,
      },
    ];
    const markup = renderToStaticMarkup(
      React.createElement(OptimizationEvidenceTable, {
        rows: sampleRows,
        savedRatingsCount: 1,
      })
    );
    expect(markup).toContain("run-42");
    expect(markup).toContain('href="#/runs?run_id=run-42"');
    expect(markup).toContain("Senior Platform Engineer");
    expect(markup).toContain('href="https://jobs.example.test/42"');
    expect(markup).toContain("0.952");
    expect(markup).toContain("5 / 5");
    expect(markup).not.toContain("Rating details unavailable");
    expect(markup).not.toContain("No saved ratings");
  });

  it("retains truthful unavailable empty state when rating evidence is absent but count > 0", () => {
    const markup = renderToStaticMarkup(
      React.createElement(OptimizationEvidenceTable, {
        rows: undefined,
        savedRatingsCount: 5,
      })
    );
    expect(markup).toContain("Rating details unavailable");
    expect(markup).toContain("5 saved ratings exist, but row-level details are not available from the current API.");
  });

  it("renders OptimizationDetailsView using canonical evidence rows when provided", () => {
    const sampleRun = {
      id: "por_20260904_02",
      policyVersionId: "RP-20260904-02",
      createdAt: 1788549600000,
      strength: 0.08,
      status: "Succeeded",
      runtimeCompatible: true,
      evidence: [
        {
          ratedAt: "2026-07-16T12:00:00Z",
          runId: "run-42",
          job: "Senior Platform Engineer",
          savedRank: 1,
          baselineFit: 0.95,
          rating: 4,
        },
      ],
    };

    const detailsMarkup = renderToStaticMarkup(
      React.createElement(OptimizationDetailsView, {
        item: sampleRun,
        rankingMode: "personalized",
        activePolicyVersionId: "RP-20260904-02",
        onBack: () => {},
        onActivatePolicy: () => {},
      })
    );
    expect(detailsMarkup).toContain("Ratings Included");
    expect(detailsMarkup).toContain("Senior Platform Engineer");
    expect(detailsMarkup).toContain("4 / 5");
  });
  it("renders StrengthDialog with bounded step and validation constraints", () => {
    const dialogMarkup = renderToStaticMarkup(
      React.createElement(StrengthDialog, {
        open: true,
        onClose: () => {},
        currentStrength: 0.05,
        bounds: { minimum: 0.01, maximum: 0.1, step: 0.01 },
        onSave: () => {},
      })
    );
    expect(dialogMarkup).toContain("Personalization Strength");
    expect(dialogMarkup).toContain("Choose a value from 0.01 to 0.10.");
    expect(dialogMarkup).toContain("min=\"0.01\"");
    expect(dialogMarkup).toContain("max=\"0.1\"");
  });
});
