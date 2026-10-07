import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";
import { AnalyticsDashboardPage } from "../features/analytics-dashboard/route";

describe("analytics dashboard", () => {
  it("is discovered as a workspace route", () => {
    const routes = discoverFeatureRoutes();
    const route = routes.find((item) => item.id === "analytics-dashboard");
    expect(route?.group).toBe("workspace");
    expect(matchRoute("#/analytics", routes).id).toBe("analytics-dashboard");
  });

  it("renders accessible loading state without claiming data", () => {
    const markup = renderToStaticMarkup(<AnalyticsDashboardPage />);
    expect(markup).toContain("Analytics");
    expect(markup).toContain("aria-busy=\"true\"");
    expect(markup).toContain("Loading published analytics");
  });
});
