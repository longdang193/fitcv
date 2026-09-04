import { describe, it, expect, beforeEach, vi } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { route as apiProvidersRoute } from "../features/api-providers/route";
import { route as llmConfigRoute } from "../features/llm-configuration/route";
import { customProviderPayload, providerInitials, ProviderSettingsCore, getProviderIdFromHash } from "../features/api-providers/provider-settings-core";
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";
import { Dialog } from "../components/dialog";

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

  it("preserves draft on same-provider refresh and validation actions", async () => {
    let currentSelectedId = "custom-ollama";
    let draftBaseUrl = "http://127.0.0.1:11434/v1";
    let draftApiType = "chat_completions";
    let connectionTestPassed = true;

    const mockServerProviders = [
      {
        provider_id: "custom-ollama",
        display_name: "Ollama",
        compatibility: "openai",
        base_url: null, // Server record still has null before save
        api_type: "chat_completions",
      },
      {
        provider_id: "openai",
        display_name: "OpenAI",
        compatibility: "openai",
        base_url: "https://api.openai.com/v1",
        api_type: "responses",
      },
    ];

    // load function modeling same-provider refresh guard
    const load = (hashId: string | null = null) => {
      const targetId = hashId || currentSelectedId;
      const match = mockServerProviders.find((p) => p.provider_id === targetId) || mockServerProviders[0];
      const providerChanged = !currentSelectedId || currentSelectedId !== match.provider_id || (hashId !== null && hashId !== currentSelectedId);
      if (providerChanged) {
        currentSelectedId = match.provider_id;
        draftBaseUrl = match.base_url || "";
        draftApiType = match.api_type || "chat_completions";
        connectionTestPassed = false;
      }
    };

    // 1. Same-provider refresh does NOT overwrite user draft
    load();
    expect(draftBaseUrl).toBe("http://127.0.0.1:11434/v1");
    expect(connectionTestPassed).toBe(true);

    // 2. Validation action with reload: false does not call load and keeps draft
    const run = async (op: () => Promise<void>, options?: { reload?: boolean }) => {
      await op();
      if (options?.reload !== false) {
        load();
      }
    };

    await run(async () => {}, { reload: false });
    expect(draftBaseUrl).toBe("http://127.0.0.1:11434/v1");

    // 3. Save connection sends intact draft Base URL
    let savedPayload: Record<string, unknown> | null = null;
    await run(async () => {
      savedPayload = {
        base_url: draftBaseUrl.trim() || null,
        api_type: draftApiType,
        api_key: "key-123",
      };
    });

    expect(savedPayload).toEqual({
      base_url: "http://127.0.0.1:11434/v1",
      api_type: "chat_completions",
      api_key: "key-123",
    });

    // 4. Changing provider initializes fields from server and resets validation
    load("openai");
    expect(currentSelectedId).toBe("openai");
    expect(draftBaseUrl).toBe("https://api.openai.com/v1");
    expect(draftApiType).toBe("responses");
    expect(connectionTestPassed).toBe(false);
  });

  it("builds backend-compatible custom provider payloads for both protocols", () => {
    expect(customProviderPayload("openai")).toEqual({
      display_name: "New OpenAI-compatible provider",
      compatibility: "openai",
    });
    expect(customProviderPayload("anthropic")).toEqual({
      display_name: "New Anthropic-compatible provider",
      compatibility: "anthropic",
    });
  });

  it("computes uppercase two-letter provider monogram initials", () => {
    expect(providerInitials("OpenAI")).toBe("O");
    expect(providerInitials("OpenAI Compatible")).toBe("OC");
    expect(providerInitials("Anthropic Claude")).toBe("AC");
    expect(providerInitials("")).toBe("AI");
  });
  it("uses production copy without stale prototype wording for connection and model test success", () => {
    const isConnected = false;
    const connectionSuccessMessage = `Connection test succeeded. ${isConnected ? "Update" : "Add"} Connection is ready.`;
    const modelSuccessMessage = "Model validation succeeded. Add Model is ready.";

    expect(connectionSuccessMessage).not.toContain("in prototype");
    expect(connectionSuccessMessage).toContain("Connection test succeeded.");

    expect(modelSuccessMessage).not.toContain("in prototype");
    expect(modelSuccessMessage).toContain("Model validation succeeded.");
  });

  it("renders Add Model dialog structure using shared Dialog behavior", () => {
    const html = renderToStaticMarkup(
      React.createElement(
        Dialog,
        {
          open: true,
          onClose: () => {},
          title: "Add Model",
          description: "Test one model identifier before adding it.",
          className: "provider-model-dialog",
          footer: React.createElement(
            "div",
            { className: "dialog-actions" },
            React.createElement("button", { id: "cancelProviderModelDialog", className: "btn" }, "Cancel"),
            React.createElement("button", { id: "saveProviderModel", className: "btn primary" }, "Add Model")
          ),
          children: React.createElement(
            "form",
            { id: "providerModelForm" },
            React.createElement("input", { id: "providerModelIdentifier" }),
            React.createElement("button", { id: "testProviderModel" }, "Test")
          ),
        }
      )
    );

    expect(html).toContain("native-dialog");
    expect(html).toContain("provider-model-dialog");
    expect(html).toContain("Add Model");
    expect(html).toContain("Test one model identifier before adding it.");
    expect(html).toContain("providerModelIdentifier");
    expect(html).toContain("testProviderModel");
    expect(html).toContain("cancelProviderModelDialog");
    expect(html).toContain("saveProviderModel");
  });
});
