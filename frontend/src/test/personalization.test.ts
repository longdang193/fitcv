import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchPersonalization,
  patchPersonalization,
  fetchPersonalizationOptimization,
  createPersonalizationCandidate,
  activatePersonalizationCandidate,
} from "../features/personalization/api";
import { apiClient, ApiClientError } from "../lib/api-client";
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";

describe("personalization slice and api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("registers and matches personalization feature route", () => {
    const routes = discoverFeatureRoutes();
    const persRoute = routes.find((r) => r.id === "personalization");
    expect(persRoute).toBeDefined();
    expect(persRoute?.path).toBe("#/settings/personalization");
    expect(persRoute?.group).toBe("settings");

    const matched = matchRoute("#/settings/personalization", routes);
    expect(matched.id).toBe("personalization");
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
          bounds: { minimum: 0.0, maximum: 1.0, step: 0.01 },
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
          bounds: { minimum: 0.0, maximum: 1.0, step: 0.01 },
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
});
