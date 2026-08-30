import { describe, it, expect } from "vitest";
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";

describe("route registry and navigation", () => {
  it("discovers default routes with valid paths and groups", () => {
    const routes = discoverFeatureRoutes();
    expect(routes.length).toBeGreaterThan(0);

    const overview = routes.find((r) => r.id === "overview");
    expect(overview).toBeDefined();
    expect(overview?.path).toBe("#/overview");
    expect(overview?.group).toBe("workspace");
  });

  it("matches hash routes correctly", () => {
    const routes = discoverFeatureRoutes();
    const matched = matchRoute("#/overview", routes);
    expect(matched.id).toBe("overview");

    const fallback = matchRoute("#/unknown-route", routes);
    expect(fallback.id).toBe("overview");
  });
});
