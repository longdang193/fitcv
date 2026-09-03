import { describe, it, expect, beforeEach, vi } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { route as apiProvidersRoute } from "../features/api-providers/route";
import { route as llmConfigRoute } from "../features/llm-configuration/route";
import { ProviderSettingsCore, getProviderIdFromHash } from "../features/api-providers/provider-settings-core";
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";

describe("provider-settings routes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("defines distinct route metadata for separate prototype pages", () => {
    expect(apiProvidersRoute.id).toBe("api-providers");
    expect(apiProvidersRoute.path).toBe("#/settings/api-providers");
    expect(apiProvidersRoute.title).toBe("API Providers");
    expect(apiProvidersRoute.group).toBe("settings");

    expect(llmConfigRoute.id).toBe("llm-configuration");
    expect(llmConfigRoute.path).toBe("#/settings/llm-configuration");
    expect(llmConfigRoute.title).toBe("LLM Configuration");
    expect(llmConfigRoute.group).toBe("settings");
  });

  it("registers both routes and resolves compatibility aliases", () => {
    const routes = discoverFeatureRoutes();
    const ids = routes.map((r) => r.id);
    expect(ids).toContain("api-providers");
    expect(ids).toContain("llm-configuration");

    // Exact matches
    expect(matchRoute("#/settings/api-providers", routes).id).toBe("api-providers");
    expect(matchRoute("#/settings/llm-configuration", routes).id).toBe("llm-configuration");

    // Deep link matches
    expect(matchRoute("#/settings/api-providers/openai", routes).id).toBe("api-providers");

    // Compatibility alias matches
    expect(matchRoute("#/settings/providers", routes).id).toBe("api-providers");
    expect(matchRoute("#/providers", routes).id).toBe("api-providers");
    expect(matchRoute("#/api-providers", routes).id).toBe("api-providers");
    expect(matchRoute("#/llm-configuration", routes).id).toBe("llm-configuration");
  });

  it("extracts provider ID from various hash formats", () => {
    expect(getProviderIdFromHash("#/settings/api-providers/openai")).toBe("openai");
    expect(getProviderIdFromHash("#/api-providers/custom-123")).toBe("custom-123");
    expect(getProviderIdFromHash("#/settings/providers/anthropic")).toBe("anthropic");
    expect(getProviderIdFromHash("#/providers/openai?view=models")).toBe("openai");
    expect(getProviderIdFromHash("#/settings/api-providers")).toBe(null);
  });

  it("renders API Providers loading state and component skeleton", () => {
    const html = renderToStaticMarkup(
      React.createElement(ProviderSettingsCore, { mode: "api-providers" })
    );
    expect(html).toContain("Loading API Providers");
  });

  it("renders LLM Configuration loading state and component skeleton", () => {
    const html = renderToStaticMarkup(
      React.createElement(ProviderSettingsCore, { mode: "llm-configuration" })
    );
    expect(html).toContain("Loading LLM Configuration");
  });
});
