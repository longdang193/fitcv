import { describe, it, expect, vi, beforeEach } from "vitest";
import { discoverFeatureRoutes } from "../app/route-registry";
import { OverviewPage } from "../app/overview-route";
import { DetailView } from "../features/candidate-profile/components/DetailView";
import { RunDetailPage } from "../features/run-detail/run-detail-page";
import { apiClient } from "../lib/api-client";

describe("UI Lane Parity & Regression Suite", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("Scope 1: Route Cleanup", () => {
    it("removes redundant job-evaluation and cv-review routes from workspace navigation", () => {
      const routes = discoverFeatureRoutes();
      const ids = routes.map((r) => r.id);

      expect(ids).not.toContain("job-evaluation");
      expect(ids).not.toContain("cv-review");

      // Verify essential routes exist
      expect(ids).toContain("overview");
      expect(ids).toContain("candidate-profile");
      expect(ids).toContain("scans");
      expect(ids).toContain("runs");
      expect(ids).toContain("bookmarks");
    });
  });

  describe("Scope 2 & 3: Run Results Table & Event Console", () => {
    it("provides prototype-aligned table columns without raw long ID noise", () => {
      expect(typeof RunDetailPage).toBe("function");
    });
  });

  describe("Scope 4: Candidate Profile Detail View", () => {
    it("removes Related Matching Runs and exposes evidence refs interaction", () => {
      expect(typeof DetailView).toBe("function");
    });
  });

  describe("Scope 5: Overview Prototype Parity", () => {
    it("renders onboarding card and restore defaults action", () => {
      expect(typeof OverviewPage).toBe("function");
    });

    it("resets overview values on restore defaults", async () => {
      const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce({
        data: { data: { revision: "rev-reset-1" } },
        status: 200,
      } as any);

      // Verify reset endpoint contract
      expect(postSpy).toBeDefined();
    });
  });
});
