import { describe, it, expect } from "vitest";
import { discoverFeatureRoutes, matchRoute } from "./route-registry";

describe("route-registry", () => {
  it("discovers feature routes and sorts by order", () => {
    const routes = discoverFeatureRoutes();
    expect(routes.length).toBeGreaterThanOrEqual(1);

    // Verify ordering
    for (let i = 1; i < routes.length; i++) {
      const prevOrder = routes[i - 1].order ?? 100;
      const currOrder = routes[i].order ?? 100;
      expect(currOrder).toBeGreaterThanOrEqual(prevOrder);
    }

    // Verify key routes
    const ids = routes.map((r) => r.id);
    expect(ids).toContain("overview");
    expect(ids).toContain("api-providers");
    expect(ids).toContain("llm-configuration");
  });

  it("matches exact routes, query parameter paths, and sub-paths", () => {
    const routes = discoverFeatureRoutes();

    // Exact
    expect(matchRoute("#/overview", routes).id).toBe("overview");
    expect(matchRoute("#/runs", routes).id).toBe("runs");
    expect(matchRoute("#/candidate-profile", routes).id).toBe("candidate-profile");
    expect(matchRoute("#/settings/api-providers", routes).id).toBe("api-providers");
    expect(matchRoute("#/settings/llm-configuration", routes).id).toBe("llm-configuration");

    // Query parameters
    expect(matchRoute("#/runs?view=archived&page=2", routes).id).toBe("runs");
    expect(matchRoute("#/scans?lifecycle=archived", routes).id).toBe("scans");

    // Sub-path prefix & deep links
    expect(matchRoute("#/candidate-profile/create", routes).id).toBe("candidate-profile");
    expect(matchRoute("#/candidate-profile/create/attempt-123/baseline", routes).id).toBe("candidate-profile");
    expect(matchRoute("#/settings/api-providers/openai", routes).id).toBe("api-providers");

    // Alias compatibility
    expect(matchRoute("#/synonyms", routes).id).toBe("synonyms");
    expect(matchRoute("#/settings/synonyms", routes).id).toBe("synonyms");
    expect(matchRoute("#/candidate-profiles/create", routes).id).toBe("candidate-profile");
    expect(matchRoute("#/candidate-profiles", routes).id).toBe("candidate-profile");
    expect(matchRoute("#/settings/providers", routes).id).toBe("api-providers");
    expect(matchRoute("#/providers", routes).id).toBe("api-providers");
    expect(matchRoute("#/api-providers", routes).id).toBe("api-providers");
    expect(matchRoute("#/llm-configuration", routes).id).toBe("llm-configuration");

    // Fallback for unknown
    expect(matchRoute("#/non-existent-random-route", routes).id).toBe("overview");
  });
});
