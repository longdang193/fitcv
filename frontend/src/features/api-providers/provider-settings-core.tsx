import React, { useEffect, useState, useCallback, useRef } from "react";
import { Button, LoadingState, Dialog } from "../../components";
import { apiClient } from "../../lib/api-client";

export type ProviderModel = {
  model_record_id: string;
  provider_id: string;
  model_id: string;
  validation_status: string;
  revision?: number;
};

export type Provider = {
  provider_id: string;
  kind?: "predefined" | "custom";
  display_name: string;
  compatibility: "openai" | "anthropic";
  base_url: string | null;
  base_url_editable: boolean;
  supported_api_types?: string[];
  api_type_fixed?: boolean;
  api_type: string;
  connection_status: string;
  credential_configured: boolean;
  revision: number;
  models: ProviderModel[];
};

export type LlmConfig = {
  default_model_ref: string | null;
  tasks: Record<string, { model_ref: string | null; timeout_seconds: number; temperature: number }>;
  revision: number;
  eligible_models: Array<{ model_record_id: string; provider_display_name: string; model_id: string }>;
};

export function customProviderPayload(compatibility: "openai" | "anthropic") {
  return {
    display_name: compatibility === "anthropic"
      ? "New Anthropic-compatible provider"
      : "New OpenAI-compatible provider",
    compatibility,
  };
}

export function providerInitials(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join("")
      .toUpperCase() || "AI"
  );
}

export const LLM_TASKS = [
  { id: "candidate_profile_base_mapping", label: "Candidate Profile Base Mapping" },
  { id: "candidate_profile_derived_claims", label: "Candidate Profile Derived Claims" },
  { id: "enrich_extraction", label: "Enrich Extraction" },
  { id: "ranking_ai_score", label: "Ranking AI Score" },
  { id: "cv_generation_structured_write", label: "CV Generation" },
  { id: "synonym_triage_recommendation", label: "Synonym Recommendation" },
];

export function getProviderIdFromHash(hash: string): string | null {
  const normalized = hash.startsWith("#") ? hash : `#${hash}`;
  const clean = normalized.split("?")[0];
  const prefixes = [
    "#/settings/api-providers/",
    "#/api-providers/",
    "#/settings/providers/",
    "#/providers/",
  ];
  for (const prefix of prefixes) {
    if (clean.startsWith(prefix)) {
      const remainder = clean.slice(prefix.length).trim();
      if (remainder) return decodeURIComponent(remainder);
    }
  }
  return null;
}

export interface ProviderSettingsCoreProps {
  mode: "api-providers" | "llm-configuration";
}

export const ProviderSettingsCore: React.FC<ProviderSettingsCoreProps> = ({ mode }) => {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [llm, setLlm] = useState<LlmConfig | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(() =>
    typeof window !== "undefined" ? getProviderIdFromHash(window.location.hash) : null
  );
  const selectedIdRef = useRef<string | null>(selectedId);
  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);
  const [displayName, setDisplayName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiType, setApiType] = useState("responses");
  const [isModelDialogOpen, setIsModelDialogOpen] = useState(false);
  const [newModelId, setNewModelId] = useState("");
  const [testedNewModelId, setTestedNewModelId] = useState("");
  const [modelTestPassed, setModelTestPassed] = useState(false);
  const [modelStatusMessage, setModelStatusMessage] = useState("");
  const [modelStatusKind, setModelStatusKind] = useState<"" | "valid" | "error">("");
  const [connectionTestPassed, setConnectionTestPassed] = useState(false);
  const [connectionStatusText, setConnectionStatusText] = useState("");
  const [connectionStatusKind, setConnectionStatusKind] = useState<"" | "valid" | "error">("");
  const [providerSearch, setProviderSearch] = useState("");

  // LLM task editing state
  const [editingTask, setEditingTask] = useState<string | null>(null);
  const [taskModel, setTaskModel] = useState<string>("");
  const [taskTimeout, setTaskTimeout] = useState<number>(120);
  const [taskTemperature, setTaskTemperature] = useState<number>(0.2);

  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (mode === "api-providers") {
        const res = await apiClient.get<{ data: Provider[] }>("/api-providers");
        const next = res.data.data || [];
        setProviders(next);
        const hashId = typeof window !== "undefined" ? getProviderIdFromHash(window.location.hash) : null;
        const currentId = selectedIdRef.current;
        const targetId = hashId || currentId;
        setSelectedId(hashId);
        selectedIdRef.current = hashId;
        if (targetId) {
          const match = next.find((p) => p.provider_id === targetId);
          if (match) {
            setDisplayName(match.display_name);
            setBaseUrl(match.base_url || "");
            setApiType(match.compatibility === "anthropic" ? "messages" : match.api_type === "chat_completions" ? "chat-completions" : "responses");
            setApiKey("");
            setConnectionTestPassed(false);
            setConnectionStatusText("");
            setConnectionStatusKind("");
          }
        }
      } else {
        const res = await apiClient.get<{ data: LlmConfig }>("/llm-configuration");
        setLlm(res.data.data);
      }
    } catch (err: any) {
      setMessage(err.message || "Failed to load settings.");
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    if (mode !== "api-providers") return;
    const handleHash = () => {
      const fromHash = getProviderIdFromHash(window.location.hash);
      setSelectedId(fromHash);
      selectedIdRef.current = fromHash;
    };
    window.addEventListener("hashchange", handleHash);
    return () => window.removeEventListener("hashchange", handleHash);
  }, [mode]);

  const provider = providers.find((p) => p.provider_id === selectedId);

  useEffect(() => {
    if (provider) {
      setDisplayName(provider.display_name);
      setBaseUrl(provider.base_url || "");
      setApiType(provider.compatibility === "anthropic" ? "messages" : provider.api_type === "chat_completions" ? "chat-completions" : "responses");
      setApiKey("");
      setConnectionTestPassed(false);
      setConnectionStatusText("");
      setConnectionStatusKind("");
    }
  }, [provider?.provider_id, provider?.revision]);

  const run = async (operation: () => Promise<void>, options?: { reload?: boolean }) => {
    setBusy(true);
    setMessage("");
    try {
      await operation();
      if (options?.reload !== false) {
        await load();
      }
    } catch (err: any) {
      setMessage(`${err.message || "Request failed."}${err.action ? ` ${err.action}` : ""}`);
    } finally {
      setBusy(false);
    }
  };

  const handleAddCustomProvider = (compatibility: "openai" | "anthropic") => {
    void run(async () => {
      const res = await apiClient.post<{ data: Provider }>(
        "/api-providers",
        customProviderPayload(compatibility),
        { idempotencyKey: crypto.randomUUID() }
      );
      const created = res.data.data;
      window.location.hash = `#/settings/api-providers/${encodeURIComponent(created.provider_id)}`;
    });
  };

  const resetConnectionTest = () => {
    setConnectionTestPassed(false);
    setConnectionStatusText(
      provider && provider.connection_status === "verified"
        ? "Current connection remains active. Test changes before updating."
        : "Test connection details before adding."
    );
    setConnectionStatusKind("");
  };

  const validateConnectionDraft = (): { name: string; baseUrl: string; apiKey: string; apiType: string } | null => {
    if (!provider) return null;
    const isCustom = provider.kind === "custom" || provider.base_url_editable || provider.provider_id.startsWith("custom-");
    const trimmedName = displayName.trim() || provider.display_name;
    if (isCustom && !trimmedName) {
      setConnectionTestPassed(false);
      setConnectionStatusText("Display Name is required.");
      setConnectionStatusKind("error");
      return null;
    }
    const trimmedBaseUrl = baseUrl.trim();
    try {
      const parsed = new URL(trimmedBaseUrl);
      if (!["http:", "https:"].includes(parsed.protocol)) throw new Error();
    } catch {
      setConnectionTestPassed(false);
      setConnectionStatusText("Base URL must be a valid HTTP or HTTPS URL.");
      setConnectionStatusKind("error");
      return null;
    }
    if (!provider.credential_configured && !apiKey.trim()) {
      setConnectionTestPassed(false);
      setConnectionStatusText("API Key is required for first connection.");
      setConnectionStatusKind("error");
      return null;
    }
    return {
      name: trimmedName,
      baseUrl: trimmedBaseUrl,
      apiKey: apiKey.trim(),
      apiType: provider.compatibility === "anthropic" ? "messages" : apiType === "chat-completions" ? "chat_completions" : "responses",
    };
  };

  const testConnection = () => {
    if (!provider) return;
    const draft = validateConnectionDraft();
    if (!draft) return;
    void run(async () => {
      setConnectionStatusText("Testing connection...");
      setConnectionStatusKind("");
      const res = await apiClient.post<{ data: { ok: boolean; failure_code?: string; supported_api_types?: string[] } }>(
        `/api-providers/${encodeURIComponent(provider.provider_id)}/connection/actions/test`,
        {
          base_url: draft.baseUrl || null,
          api_type: draft.apiType,
          api_key: draft.apiKey || null,
        }
      );
      if (res.data.data.ok) {
        setConnectionTestPassed(true);
        const isConnected = provider.connection_status === "verified";
        setConnectionStatusText(`Connection test succeeded. ${isConnected ? "Update" : "Add"} Connection is ready.`);
        setConnectionStatusKind("valid");
      } else {
        setConnectionTestPassed(false);
        setConnectionStatusText(`Connection test failed: ${res.data.data.failure_code || "Check Base URL, API Type, or API key."}`);
        setConnectionStatusKind("error");
      }
    }, { reload: false });
  };

  const saveConnection = () => {
    if (!provider) return;
    if (!connectionTestPassed) {
      setConnectionStatusText("Test this connection successfully before saving it.");
      setConnectionStatusKind("error");
      return;
    }
    const draft = validateConnectionDraft();
    if (!draft) return;

    void run(async () => {
      const isCustom = provider.kind === "custom" || provider.base_url_editable || provider.provider_id.startsWith("custom-");
      let expectedRevision = provider.revision;
      if (isCustom && draft.name !== provider.display_name) {
        const response = await apiClient.patch<{ data: Provider }>(
          `/api-providers/${encodeURIComponent(provider.provider_id)}`,
          { display_name: draft.name, expected_revision: provider.revision }
        );
        const revision = response.data.data?.revision;
        if (typeof revision !== "number") {
          throw new Error("Provider update response missing revision.");
        }
        expectedRevision = revision;
      }

      await apiClient.put(
        `/api-providers/${encodeURIComponent(provider.provider_id)}/connection`,
        {
          base_url: draft.baseUrl || null,
          api_type: draft.apiType,
          api_key: draft.apiKey || null,
          expected_revision: expectedRevision,
        }
      );

      setApiKey("");
      setConnectionTestPassed(false);
      setConnectionStatusText("");
      setConnectionStatusKind("");
    });
  };

  const removeConnection = () => {
    if (!provider) return;
    void run(async () => {
      await apiClient.delete(
        `/api-providers/${encodeURIComponent(provider.provider_id)}/connection`,
        { body: { expected_revision: provider.revision } }
      );
      setConnectionTestPassed(false);
      setConnectionStatusText("");
      setConnectionStatusKind("");
    });
  };

  const deleteCustomProvider = () => {
    if (!provider) return;
    void run(async () => {
      await apiClient.delete(`/api-providers/${encodeURIComponent(provider.provider_id)}`, {
        body: { expected_revision: provider.revision },
      });
      window.location.hash = "#/settings/api-providers";
    });
  };

  const openModelDialog = () => {
    if (!provider || provider.connection_status !== "verified") return;
    setNewModelId("");
    setTestedNewModelId("");
    setModelTestPassed(false);
    setModelStatusMessage("Add Model saves only after a successful test.");
    setModelStatusKind("");
    setIsModelDialogOpen(true);
  };

  const closeModelDialog = () => {
    setIsModelDialogOpen(false);
    setNewModelId("");
    setTestedNewModelId("");
    setModelTestPassed(false);
  };

  const resetModelTest = (msg = "Add Model saves only after a successful test.") => {
    setTestedNewModelId("");
    setModelTestPassed(false);
    setModelStatusMessage(msg);
    setModelStatusKind("");
  };

  const testNewModel = () => {
    if (!provider || provider.connection_status !== "verified") {
      setModelStatusMessage("Configure and test a provider connection before testing models.");
      setModelStatusKind("error");
      return;
    }
    const trimmed = newModelId.trim();
    if (!trimmed) {
      setModelStatusMessage("Enter a Model ID before testing.");
      setModelStatusKind("error");
      return;
    }
    if (provider.models.some((m) => m.model_id === trimmed)) {
      setModelStatusMessage("This model is already available for the provider.");
      setModelStatusKind("error");
      return;
    }

    void run(async () => {
      setModelStatusMessage("Testing model...");
      setModelStatusKind("");
      const res = await apiClient.post<{ data: { ok: boolean; failure_code?: string } }>(
        `/api-providers/${encodeURIComponent(provider.provider_id)}/models/actions/test`,
        { model_id: trimmed }
      );
      if (res.data.data.ok) {
        setTestedNewModelId(trimmed);
        setModelTestPassed(true);
        setModelStatusMessage("Model validation succeeded. Add Model is ready.");
        setModelStatusKind("valid");
      } else {
        setModelTestPassed(false);
        setModelStatusMessage(`Model test failed: ${res.data.data.failure_code || "Check Model ID."}`);
        setModelStatusKind("error");
      }
    }, { reload: false });
  };

  const addModel = () => {
    if (!provider || !modelTestPassed || testedNewModelId !== newModelId.trim()) {
      setModelStatusMessage("Test this Model ID successfully before adding it.");
      setModelStatusKind("error");
      return;
    }
    const trimmed = newModelId.trim();
    void run(async () => {
      await apiClient.post(
        `/api-providers/${encodeURIComponent(provider.provider_id)}/models`,
        { model_id: trimmed, expected_revision: provider.revision },
        { idempotencyKey: crypto.randomUUID() }
      );
      closeModelDialog();
    });
  };

  const retestModel = (model: ProviderModel) => {
    if (!provider || provider.connection_status !== "verified") return;
    void run(async () => {
      await apiClient.post(
        `/api-providers/${encodeURIComponent(provider.provider_id)}/models/${encodeURIComponent(model.model_record_id)}/actions/test`,
        { expected_revision: model.revision || provider.revision }
      );
    }, { reload: true });
  };

  const removeModel = (model: ProviderModel) => {
    if (!provider || provider.connection_status !== "verified") return;
    void run(async () => {
      await apiClient.delete(
        `/api-providers/${encodeURIComponent(provider.provider_id)}/models/${encodeURIComponent(model.model_record_id)}`,
        { body: { expected_revision: model.revision || provider.revision } }
      );
    });
  };

  const customProviders = providers.filter(
    (p) => p.kind === "custom" || p.base_url_editable || p.provider_id.startsWith("custom-")
  );
  const predefinedProviders = providers.filter(
    (p) => !(p.kind === "custom" || p.base_url_editable || p.provider_id.startsWith("custom-"))
  );

  const searchNormalized = providerSearch.trim().toLowerCase();
  const matchesSearch = (p: Provider) =>
    !searchNormalized ||
    `${p.display_name} ${p.compatibility === "anthropic" ? "anthropic-compatible anthropic" : "openai-compatible openai"}`
      .toLowerCase()
      .includes(searchNormalized);

  const filteredCustom = customProviders.filter(matchesSearch);
  const filteredPredefined = predefinedProviders.filter(matchesSearch);

  const renderProviderCard = (p: Provider) => {
    const isConnected = p.connection_status === "verified";
    return (
      <a
        key={p.provider_id}
        className="provider-card"
        href={`#/settings/api-providers/${encodeURIComponent(p.provider_id)}`}
        data-provider-card
        data-provider-search={`${p.display_name} ${p.compatibility === "anthropic" ? "anthropic-compatible" : "openai-compatible"}`.toLowerCase()}
      >
        <span className="provider-monogram" aria-hidden="true">
          {providerInitials(p.display_name)}
        </span>
        <span className="provider-card-copy">
          <strong>{p.display_name}</strong>
          <span>
            {p.compatibility === "anthropic" ? "Anthropic-compatible" : "OpenAI-compatible"}
          </span>
        </span>
        <span className={`provider-status${isConnected ? " connected" : ""}`}>
          {isConnected ? "Connected" : "No connection"}
        </span>
        <span className="provider-chevron" aria-hidden="true">
          ›
        </span>
      </a>
    );
  };

  const updateDefaultModel = (newModelRef: string) => {
    if (!llm) return;
    void run(async () => {
      await apiClient.patch("/llm-configuration", {
        default_model_ref: newModelRef || null,
        expected_revision: llm.revision,
      });
      setMessage("Default route saved.");
    });
  };

  const openTaskEditor = (taskId: string) => {
    if (!llm) return;
    const cfg = llm.tasks?.[taskId];
    setEditingTask(taskId);
    setTaskModel(cfg?.model_ref || "");
    setTaskTimeout(cfg?.timeout_seconds ?? 120);
    setTaskTemperature(cfg?.temperature ?? 0.2);
  };

  const saveTaskConfig = () => {
    if (!llm || !editingTask) return;
    void run(async () => {
      await apiClient.patch("/llm-configuration", {
        tasks: {
          [editingTask]: {
            model_ref: taskModel || null,
            timeout_seconds: Number(taskTimeout),
            temperature: Number(taskTemperature),
          },
        },
        expected_revision: llm.revision,
      });
      setEditingTask(null);
      const def = LLM_TASKS.find((t) => t.id === editingTask);
      setMessage(`${def ? def.label : "Task"} configuration saved.`);
    });
  };

  if (loading) return <LoadingState message={`Loading ${mode === "api-providers" ? "API Providers" : "LLM Configuration"}...`} />;

  // API Providers Page Mode
  if (mode === "api-providers") {
    if (selectedId) {
      if (!provider) {
        return (
          <div className="content-container">
            <div className="details-page-head">
              <a className="details-page-back" href="#/settings/api-providers">
                ← Back to API Providers
              </a>
              <div className="page-head">
                <div>
                  <p className="eyebrow">Application</p>
                  <h2>Provider Not Found</h2>
                  <p>The requested provider could not be found.</p>
                </div>
              </div>
            </div>
            <div className="provider-empty">
              Provider \"{selectedId}\" was not found. <a href="#/settings/api-providers">Return to API Providers</a>
            </div>
          </div>
        );
      }

      const isCustom = provider.kind === "custom" || provider.base_url_editable || provider.provider_id.startsWith("custom-");
      const connected = provider.connection_status === "verified";
      const hasCredential = provider.credential_configured;
      const fixedApiType = provider.compatibility === "anthropic" || provider.api_type_fixed;

      return (
        <div className="content-container">
          <div className="details-page-head">
            <a className="details-page-back" href="#/settings/api-providers">
              ← Back to API Providers
            </a>
            <div className="page-head">
              <div>
                <p className="eyebrow">API Provider</p>
                <h2>{provider.display_name}</h2>
                <p>
                  {provider.compatibility === "anthropic"
                    ? "Anthropic-compatible provider using Messages API."
                    : "OpenAI-compatible provider."}
                </p>
              </div>
              {isCustom && (
                <button
                  className="btn danger"
                  id="deleteCustomProvider"
                  type="button"
                  onClick={deleteCustomProvider}
                  disabled={busy}
                >
                  Delete Provider
                </button>
              )}
            </div>
          </div>

          <div className="provider-detail-stack">
            <section className="section-card provider-connection-card" aria-labelledby="connectionTitle">
              <div className="provider-connection-head">
                <div className="provider-connection-copy">
                  <h3 id="connectionTitle">Connection</h3>
                  <p>{connected ? "Connection tested and ready." : "No verified connection."}</p>
                </div>
                <span className={`provider-status${connected ? " connected" : ""}`}>
                  {connected ? "Connected" : "No connection"}
                </span>
              </div>
              <div className="provider-form-grid">
                {isCustom && (
                  <div className="provider-field full">
                    <label htmlFor="providerDisplayName">Display Name</label>
                    <input
                      className="field"
                      id="providerDisplayName"
                      type="text"
                      maxLength={80}
                      value={displayName}
                      onChange={(e) => {
                        setDisplayName(e.target.value);
                        resetConnectionTest();
                      }}
                      required
                      disabled={busy}
                    />
                  </div>
                )}
                <div className="provider-field full">
                  <label htmlFor="providerBaseUrl">Base URL</label>
                  <input
                    className="field"
                    id="providerBaseUrl"
                    type="url"
                    value={baseUrl}
                    placeholder="https://api.example.com/v1"
                    disabled={!isCustom || busy}
                    onChange={(e) => {
                      setBaseUrl(e.target.value);
                      resetConnectionTest();
                    }}
                    required
                  />
                  <small>{isCustom ? "Configure provider endpoint." : "Defined by FitCV for this provider."}</small>
                </div>
                <div className="provider-field">
                  <label htmlFor="providerApiKey">API Key</label>
                  <input
                    className="field"
                    id="providerApiKey"
                    type="password"
                    autoComplete="new-password"
                    spellCheck={false}
                    placeholder={hasCredential ? "••••••••••••" : "Enter API key"}
                    value={apiKey}
                    onChange={(e) => {
                      setApiKey(e.target.value);
                      resetConnectionTest();
                    }}
                    disabled={busy}
                  />
                  <small>
                    {hasCredential
                      ? "Saved as a credential. Enter a new key only to replace it."
                      : "Required to create connection."}
                  </small>
                </div>
                <div className="provider-field">
                  <label htmlFor="providerApiType">API Type</label>
                  <select
                    className="field"
                    id="providerApiType"
                    disabled={fixedApiType || busy}
                    value={apiType}
                    onChange={(e) => {
                      setApiType(e.target.value);
                      resetConnectionTest();
                    }}
                  >
                    {fixedApiType ? (
                      <option value="messages">Messages API</option>
                    ) : (
                      <>
                        <option value="chat-completions">Chat Completions</option>
                        <option value="responses">Responses API</option>
                      </>
                    )}
                  </select>
                  <small>{fixedApiType ? "Fixed by provider protocol." : "Choose provider request format."}</small>
                </div>
              </div>
              <p className="provider-helper">
                <strong>Credential safety:</strong> API keys are never saved in browser storage. Later backend integration stores credentials in Windows Credential Manager.
              </p>
              <p
                className={`provider-form-status${connectionStatusKind === "error" ? " error" : connectionStatusKind === "valid" ? " valid" : ""}`}
                id="providerConnectionStatus"
                role="status"
                aria-live="polite"
              >
                {connectionStatusText ||
                  (connected
                    ? "Current connection remains active. Test changes before updating."
                    : hasCredential
                    ? "Test the saved connection before adding it."
                    : "Test connection details before adding.")}
              </p>
              <div className="backup-actions">
                <button className="btn" id="testProviderConnection" type="button" onClick={testConnection} disabled={busy}>
                  Test
                </button>
                <button
                  className="btn primary"
                  id="saveProviderConnection"
                  type="button"
                  disabled={!connectionTestPassed || busy}
                  onClick={saveConnection}
                >
                  {connected ? "Update Connection" : "Add Connection"}
                </button>
                {hasCredential && (
                  <button
                    className="btn danger"
                    id="removeProviderConnection"
                    type="button"
                    onClick={removeConnection}
                    disabled={busy}
                  >
                    Remove Connection
                  </button>
                )}
              </div>
            </section>

            <section
              className={`section-card provider-models${connected ? "" : " is-disabled"}`}
              aria-labelledby="modelsTitle"
              aria-disabled={!connected}
            >
              <div className="provider-models-head">
                <div>
                  <h3 id="modelsTitle">Available Models</h3>
                  <p>
                    {connected
                      ? "Models become available after successful validation."
                      : "Connection required before adding or testing models."}
                  </p>
                </div>
                <button
                  className="btn"
                  id="openProviderModelDialog"
                  type="button"
                  disabled={!connected || busy}
                  onClick={openModelDialog}
                >
                  Add Model
                </button>
              </div>
              {provider.models && provider.models.length > 0 ? (
                <div className="model-grid">
                  {provider.models.map((model) => (
                    <article className="model-card" key={model.model_record_id || model.model_id}>
                      <div>
                        <code>{model.model_id}</code>
                        <div className={`model-state${model.validation_status === "verified" ? " verified" : ""}`}>
                          {model.validation_status === "verified" ? "Validated" : "Needs retest"}
                        </div>
                      </div>
                      <div className="model-card-actions">
                        <button
                          className="btn"
                          type="button"
                          data-test-model={model.model_id}
                          disabled={!connected || busy}
                          onClick={() => retestModel(model)}
                        >
                          Test
                        </button>
                        <button
                          className="btn danger"
                          type="button"
                          data-remove-model={model.model_id}
                          disabled={!connected || busy}
                          onClick={() => removeModel(model)}
                        >
                          Remove
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="provider-empty">
                  {connected ? "No models added yet." : "Test and add a connection to manage models."}
                </div>
              )}
            </section>
          </div>

          {isModelDialogOpen && (
            <Dialog
              open={isModelDialogOpen}
              onClose={closeModelDialog}
              title="Add Model"
              description="Test one model identifier before adding it."
              className="provider-model-dialog"
              footer={
                <div className="dialog-actions">
                  <button
                    className="btn"
                    id="cancelProviderModelDialog"
                    type="button"
                    onClick={closeModelDialog}
                    disabled={busy}
                  >
                    Cancel
                  </button>
                  <button
                    className="btn primary"
                    id="saveProviderModel"
                    type="button"
                    disabled={!modelTestPassed || testedNewModelId !== newModelId.trim() || busy}
                    onClick={addModel}
                  >
                    Add Model
                  </button>
                </div>
              }
            >
              <form
                className="run-form"
                id="providerModelForm"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (modelTestPassed) addModel();
                }}
              >
                <div className="run-field">
                  <label htmlFor="providerModelIdentifier">Model ID</label>
                  <div className="model-test-row">
                    <input
                      className="field"
                      id="providerModelIdentifier"
                      type="text"
                      maxLength={160}
                      autoComplete="off"
                      spellCheck={false}
                      placeholder="model-id"
                      value={newModelId}
                      onChange={(e) => {
                        setNewModelId(e.target.value);
                        resetModelTest();
                      }}
                      required
                      disabled={busy}
                    />
                    <button
                      className="btn"
                      id="testProviderModel"
                      type="button"
                      onClick={testNewModel}
                      disabled={busy || !newModelId.trim()}
                    >
                      Test
                    </button>
                  </div>
                  <small className="provider-model-preview">
                    Sent to provider as: <code id="providerModelPreview">{newModelId.trim() || "—"}</code>
                  </small>
                </div>
              </form>
              <p
                className={`run-dialog-status provider-model-status${modelStatusKind === "valid" ? " valid" : modelStatusKind === "error" ? " error" : ""}`}
                id="providerModelStatus"
                role="status"
                aria-live="polite"
              >
                {modelStatusMessage || "Add Model saves only after a successful test."}
              </p>
            </Dialog>
          )}
        </div>
      );
    }

    return (
      <div className="content-container">
        <div className="page-head">
          <div>
            <p className="eyebrow">Application</p>
            <h2>API Providers</h2>
            <p>Manage predefined and custom AI provider connections. Each provider supports one connection.</p>
          </div>
        </div>
        {message && <div className="notice" role="status">{message}</div>}
        <div className="provider-section">
          <div className="provider-page-actions">
            <label className="provider-field provider-search">
              <span className="sr-only">Search providers</span>
              <input
                className="field"
                id="providerSearch"
                type="search"
                placeholder="Search providers"
                aria-label="Search API providers"
                value={providerSearch}
                onChange={(e) => setProviderSearch(e.target.value)}
              />
            </label>
            <div className="provider-add-actions">
              <button
                className="btn"
                type="button"
                data-add-custom-provider="openai-compatible"
                onClick={() => handleAddCustomProvider("openai")}
                disabled={busy}
              >
                Add OpenAI-compatible
              </button>
              <button
                className="btn"
                type="button"
                data-add-custom-provider="anthropic-compatible"
                onClick={() => handleAddCustomProvider("anthropic")}
                disabled={busy}
              >
                Add Anthropic-compatible
              </button>
            </div>
          </div>
          <details className="section-card collapsible-section setting-section" open>
            <summary>
              <span className="section-heading">
                <strong>Custom Providers</strong>
                <span>Connect OpenAI-compatible or Anthropic-compatible endpoints.</span>
              </span>
            </summary>
            <div className="section-content settings-card">
              {filteredCustom.length > 0 ? (
                <div className="provider-grid">
                  {filteredCustom.map(renderProviderCard)}
                </div>
              ) : (
                <div className="provider-empty">
                  No custom providers yet. Add one from buttons above.
                </div>
              )}
            </div>
          </details>
          <details className="section-card collapsible-section setting-section" open>
            <summary>
              <span className="section-heading">
                <strong>API Key Providers</strong>
                <span>Predefined API-key providers supplied by FitCV.</span>
              </span>
            </summary>
            <div className="section-content settings-card">
              {filteredPredefined.length > 0 ? (
                <div className="provider-grid">
                  {filteredPredefined.map(renderProviderCard)}
                </div>
              ) : (
                <div className="provider-empty">
                  No predefined providers found.
                </div>
              )}
            </div>
          </details>
        </div>
      </div>
    );
  }

  // LLM Configuration Page Mode
  const eligibleModels = llm?.eligible_models || [];
  const defaultSelected = Boolean(llm?.default_model_ref);

  const getModelLabel = (modelRef: string | null) => {
    if (!modelRef) return "Default";
    const match = eligibleModels.find((m) => m.model_record_id === modelRef);
    return match ? `${match.provider_display_name} · ${match.model_id}` : "Default";
  };

  return (
    <div className="content-container">
      <div className="page-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div>
          <p className="eyebrow">Application</p>
          <h2>LLM Configuration</h2>
          <p>Choose model routes and runtime behavior for Candidate Profile generation and pipeline AI tasks.</p>
        </div>
        <a href="#/settings/api-providers" className="btn" style={{ textDecoration: "none" }}>
          Manage API Providers
        </a>
      </div>
      {message && <div className="notice" role="status">{message}</div>}

      <div style={{ display: "grid", gap: 16 }}>
        <section className="section-card" style={{ padding: 20, display: "grid", gap: 14 }}>
          <h3 style={{ margin: 0 }}>Default Route</h3>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
            Used by tasks whose Model remains Default. Options come from validated models on connected providers.
          </p>
          <label className="field-group">
            <span className="field-label">Default Model</span>
            <select
              className="field-input"
              value={llm?.default_model_ref || ""}
              disabled={busy || !llm || eligibleModels.length === 0}
              onChange={(e) => updateDefaultModel(e.target.value)}
              aria-invalid={!defaultSelected}
            >
              <option value="">Select a validated model</option>
              {eligibleModels.map((item) => (
                <option key={item.model_record_id} value={item.model_record_id}>
                  {item.provider_display_name} · {item.model_id}
                </option>
              ))}
            </select>
          </label>
          {!defaultSelected && (
            <p style={{ margin: 0, color: "var(--accent)", fontSize: 13 }} role="alert">
              {eligibleModels.length > 0
                ? "Select a default model before running AI tasks."
                : "No validated models. Add a provider connection and validate a model first."}
            </p>
          )}
        </section>

        <section className="section-card" style={{ padding: 20, display: "grid", gap: 14 }}>
          <h3 style={{ margin: 0 }}>Task Configuration</h3>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
            Manage model, timeout, and temperature independently for each AI-powered task.
          </p>

          <div style={{ display: "grid", gap: 8 }}>
            {LLM_TASKS.map((task) => {
              const taskConfig = llm?.tasks?.[task.id];
              const routeLabel = getModelLabel(taskConfig?.model_ref || null);
              const timeout = taskConfig?.timeout_seconds ?? 120;
              const temperature = taskConfig?.temperature ?? 0.2;
              const isEditing = editingTask === task.id;

              return (
                <div
                  key={task.id}
                  style={{
                    padding: "12px 14px",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    background: "var(--surface)",
                    display: "grid",
                    gap: 10,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                    <div>
                      <strong style={{ fontSize: 14 }}>{task.label}</strong>
                      <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 2 }}>
                        {routeLabel} · {timeout}s · temperature {temperature}
                      </div>
                    </div>
                    <Button
                      size="compact"
                      variant="secondary"
                      disabled={busy}
                      onClick={() => (isEditing ? setEditingTask(null) : openTaskEditor(task.id))}
                    >
                      {isEditing ? "Close" : "Manage"}
                    </Button>
                  </div>

                  {isEditing && (
                    <div style={{ display: "grid", gap: 10, marginTop: 6, paddingTop: 10, borderTop: "1px solid var(--border-soft)" }}>
                      <label className="field-group">
                        <span className="field-label">Model</span>
                        <select
                          className="field-input"
                          value={taskModel}
                          onChange={(e) => setTaskModel(e.target.value)}
                          disabled={busy}
                        >
                          <option value="">Default</option>
                          {eligibleModels.map((item) => (
                            <option key={item.model_record_id} value={item.model_record_id}>
                              {item.provider_display_name} · {item.model_id}
                            </option>
                          ))}
                        </select>
                        <small style={{ color: "var(--muted)", fontSize: 12 }}>Default follows application Default Route.</small>
                      </label>

                      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                        <label className="field-group" style={{ flex: 1, minWidth: 140 }}>
                          <span className="field-label">Timeout (seconds)</span>
                          <input
                            className="field-input"
                            type="number"
                            min={1}
                            max={3600}
                            value={taskTimeout}
                            onChange={(e) => setTaskTimeout(Number(e.target.value))}
                            disabled={busy}
                          />
                        </label>
                        <label className="field-group" style={{ flex: 1, minWidth: 140 }}>
                          <span className="field-label">Temperature</span>
                          <input
                            className="field-input"
                            type="number"
                            min={0}
                            max={2}
                            step={0.1}
                            value={taskTemperature}
                            onChange={(e) => setTaskTemperature(Number(e.target.value))}
                            disabled={busy}
                          />
                        </label>
                      </div>

                      <div style={{ display: "flex", gap: 8 }}>
                        <Button variant="primary" disabled={busy} onClick={saveTaskConfig}>Save Task</Button>
                        <Button variant="secondary" disabled={busy} onClick={() => setEditingTask(null)}>Cancel</Button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
};
