import React, { useEffect, useState, useCallback, useRef } from "react";
import { Button, LoadingState } from "../../components";
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
  const [selectedId, setSelectedId] = useState<string>(() =>
    typeof window !== "undefined" ? getProviderIdFromHash(window.location.hash) || "" : ""
  );
  const selectedIdRef = useRef<string>(selectedId);
  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiType, setApiType] = useState("chat_completions");
  const [modelId, setModelId] = useState("");
  const [testedModelId, setTestedModelId] = useState("");
  const [modelTestPassed, setModelTestPassed] = useState(false);
  const [connectionTestPassed, setConnectionTestPassed] = useState(false);
  const [connectionStatusText, setConnectionStatusText] = useState("");
  const [newProviderName, setNewProviderName] = useState("");
  const [newCompatibility, setNewCompatibility] = useState<"openai" | "anthropic">("openai");

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
        const match = next.find((p) => p.provider_id === targetId) || next[0];
        if (match) {
          const providerChanged = !currentId || currentId !== match.provider_id || (hashId !== null && hashId !== currentId);
          if (providerChanged) {
            setSelectedId(match.provider_id);
            selectedIdRef.current = match.provider_id;
            setBaseUrl(match.base_url || "");
            setApiType(match.api_type || "chat_completions");
            setApiKey("");
            setConnectionTestPassed(false);
            setConnectionStatusText("");
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
      if (fromHash && fromHash !== selectedIdRef.current) {
        setSelectedId(fromHash);
        selectedIdRef.current = fromHash;
        const match = providers.find((p) => p.provider_id === fromHash);
        if (match) {
          setBaseUrl(match.base_url || "");
          setApiType(match.api_type || "chat_completions");
          setApiKey("");
          setConnectionTestPassed(false);
          setConnectionStatusText("");
        }
      }
    };
    window.addEventListener("hashchange", handleHash);
    return () => window.removeEventListener("hashchange", handleHash);
  }, [mode, providers]);

  const provider = providers.find((p) => p.provider_id === selectedId);

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

  const createProvider = () => run(async () => {
    const res = await apiClient.post<{ data: Provider }>("/api-providers", {
      display_name: newProviderName.trim(),
      compatibility: newCompatibility,
    }, { idempotencyKey: crypto.randomUUID() });
    setNewProviderName("");
    setSelectedId(res.data.data.provider_id);
    window.location.hash = `#/settings/api-providers/${encodeURIComponent(res.data.data.provider_id)}`;
    setMessage("Provider created.");
  });

  const deleteProvider = () => {
    if (!provider || !confirm(`Delete ${provider.display_name}?`)) return;
    void run(async () => {
      await apiClient.delete(`/api-providers/${encodeURIComponent(provider.provider_id)}`, {
        body: { expected_revision: provider.revision },
      });
      setSelectedId("");
      window.location.hash = "#/settings/api-providers";
      setMessage("Provider deleted.");
    });
  };

  const testConnection = () => {
    if (!provider) return;
    void run(async () => {
      const res = await apiClient.post<{ data: { ok: boolean; failure_code?: string } }>(
        `/api-providers/${encodeURIComponent(provider.provider_id)}/connection/actions/test`,
        {
          base_url: baseUrl.trim() || null,
          api_type: provider.compatibility === "anthropic" ? "messages" : apiType,
          ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
        }
      );
      if (res.data.data.ok) {
        setConnectionTestPassed(true);
        setConnectionStatusText("Connection test succeeded. Save Connection is ready.");
        setMessage("Connection test succeeded.");
      } else {
        setConnectionTestPassed(false);
        setConnectionStatusText(`Connection test failed: ${res.data.data.failure_code || "Check details."}`);
        setMessage(`Connection test failed: ${res.data.data.failure_code || "Check details."}`);
      }
    }, { reload: false });
  };

  const saveConnection = () => {
    if (!provider) return;
    void run(async () => {
      await apiClient.put(`/api-providers/${encodeURIComponent(provider.provider_id)}/connection`, {
        base_url: baseUrl.trim() || null,
        api_type: provider.compatibility === "anthropic" ? "messages" : apiType,
        api_key: apiKey.trim() || null,
        expected_revision: provider.revision,
      });
      setApiKey("");
      setConnectionTestPassed(false);
      setConnectionStatusText("");
      setMessage("Connection saved.");
    });
  };

  const removeConnection = () => {
    if (!provider) return;
    void run(async () => {
      await apiClient.delete(`/api-providers/${encodeURIComponent(provider.provider_id)}/connection`, {
        body: { expected_revision: provider.revision },
      });
      setConnectionTestPassed(false);
      setMessage("Connection removed.");
    });
  };

  const testModel = () => {
    if (!provider || !modelId.trim()) return;
    const trimmed = modelId.trim();
    void run(async () => {
      const res = await apiClient.post<{ data: { ok: boolean; failure_code?: string } }>(
        `/api-providers/${encodeURIComponent(provider.provider_id)}/models/actions/test`,
        { model_id: trimmed }
      );
      if (res.data.data.ok) {
        setTestedModelId(trimmed);
        setModelTestPassed(true);
        setMessage(`Model ${trimmed} validation succeeded. Add Model is ready.`);
      } else {
        setModelTestPassed(false);
        setMessage(`Model test failed: ${res.data.data.failure_code || "Check Model ID."}`);
      }
    }, { reload: false });
  };

  const addModel = () => {
    if (!provider || !modelTestPassed || testedModelId !== modelId.trim()) return;
    void run(async () => {
      await apiClient.post(
        `/api-providers/${encodeURIComponent(provider.provider_id)}/models`,
        { model_id: testedModelId, expected_revision: provider.revision },
        { idempotencyKey: crypto.randomUUID() }
      );
      setModelId("");
      setTestedModelId("");
      setModelTestPassed(false);
      setMessage(`Model ${testedModelId} added.`);
    });
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
        <section className="section-card" style={{ padding: 20, display: "grid", gap: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
            <h3 style={{ margin: 0 }}>Manage Provider</h3>
            {provider?.kind === "custom" && (
              <Button variant="danger" disabled={busy} onClick={deleteProvider}>
                Delete Custom Provider
              </Button>
            )}
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input className="field-input" style={{ flex: 1, minWidth: 220 }} value={newProviderName} onChange={(event) => setNewProviderName(event.target.value)} placeholder="New custom provider name" disabled={busy} />
            <select className="field-input" style={{ width: 180 }} value={newCompatibility} onChange={(event) => setNewCompatibility(event.target.value as "openai" | "anthropic")} disabled={busy}>
              <option value="openai">OpenAI-compatible</option>
              <option value="anthropic">Anthropic-compatible</option>
            </select>
            <Button variant="secondary" disabled={busy || !newProviderName.trim()} onClick={createProvider}>Add Custom Provider</Button>
          </div>
          <label className="field-group">
            <span className="field-label">Provider</span>
            <select
              className="field-input"
              value={selectedId}
              onChange={(event) => {
                const nextId = event.target.value;
                const next = providers.find((item) => item.provider_id === nextId);
                setSelectedId(nextId);
                selectedIdRef.current = nextId;
                setBaseUrl(next?.base_url || "");
                setApiType(next?.api_type || "chat_completions");
                setApiKey("");
                setConnectionTestPassed(false);
                setConnectionStatusText("");
                if (nextId) {
                  window.location.hash = `#/settings/api-providers/${encodeURIComponent(nextId)}`;
                }
              }}
            >
              <option value="">Select provider</option>
              {providers.map((item) => (
                <option key={item.provider_id} value={item.provider_id}>
                  {item.display_name} ({item.compatibility})
                </option>
              ))}
            </select>
          </label>
          {provider && <>
            <label className="field-group">
              <span className="field-label">Base URL</span>
              <input className="field-input" value={baseUrl} onChange={(event) => { setBaseUrl(event.target.value); setConnectionTestPassed(false); }} disabled={!provider.base_url_editable || busy} />
            </label>
            {provider.compatibility === "openai" && (
              <label className="field-group">
                <span className="field-label">API Type</span>
                <select
                  className="field-input"
                  value={apiType}
                  onChange={(event) => {
                    setApiType(event.target.value);
                    setConnectionTestPassed(false);
                  }}
                  disabled={provider.api_type_fixed || busy}
                >
                  {(provider.supported_api_types && provider.supported_api_types.length > 0
                    ? provider.supported_api_types
                    : ["chat_completions", "responses"]
                  ).map((type) => (
                    <option key={type} value={type}>
                      {type === "chat_completions"
                        ? "Chat Completions (/v1/chat/completions)"
                        : type === "responses"
                        ? "Responses (/v1/responses)"
                        : type}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="field-group">
              <span className="field-label">API key</span>
              <input className="field-input" type="password" value={apiKey} onChange={(event) => { setApiKey(event.target.value); setConnectionTestPassed(false); }} autoComplete="off" disabled={busy} placeholder={provider.credential_configured ? "Stored key unchanged" : "Required to verify connection"} />
            </label>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <Button variant="secondary" disabled={busy || (!apiKey.trim() && !provider.credential_configured)} onClick={testConnection}>Test Connection</Button>
              <Button variant="primary" disabled={busy || !connectionTestPassed} onClick={saveConnection}>
                {provider.connection_status === "verified" ? "Update Connection" : "Save Connection"}
              </Button>
              {provider.credential_configured && (
                <Button variant="danger" disabled={busy} onClick={removeConnection}>Remove Connection</Button>
              )}
              <span style={{ color: provider.connection_status === "verified" ? "var(--success)" : "var(--muted)", fontSize: 12 }}>
                {provider.connection_status === "verified" ? "✓ Connection verified" : "Not configured"}
              </span>
            </div>
            {connectionStatusText && <div style={{ fontSize: 13, color: connectionTestPassed ? "var(--success)" : "var(--danger)" }}>{connectionStatusText}</div>}

            <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--border-soft)", display: "grid", gap: 10 }}>
              <h4 style={{ margin: 0 }}>Models</h4>
              <label className="field-group">
                <span className="field-label">Model ID</span>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <input
                    className="field-input"
                    style={{ flex: 1, minWidth: 200 }}
                    value={modelId}
                    onChange={(event) => {
                      setModelId(event.target.value);
                      setModelTestPassed(false);
                    }}
                    disabled={busy}
                    placeholder="e.g. openai/gpt-4o-mini"
                  />
                  <Button variant="secondary" disabled={busy || !modelId.trim() || provider.connection_status !== "verified"} onClick={testModel}>Test Model</Button>
                  <Button variant="primary" disabled={busy || !modelTestPassed || testedModelId !== modelId.trim()} onClick={addModel}>Add Model</Button>
                </div>
                <small style={{ color: "var(--muted)", fontSize: 12 }}>Test model identifier before adding.</small>
              </label>
              {provider.models.length > 0 && (
                <div style={{ display: "grid", gap: 6, marginTop: 4 }}>
                  {provider.models.map((item) => (
                    <div key={item.model_record_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6 }}>
                      <div>
                        <code>{item.model_id}</code>
                        <span style={{ marginLeft: 8, fontSize: 12, color: item.validation_status === "validated" ? "var(--success)" : "var(--muted)" }}>
                          ({item.validation_status})
                        </span>
                      </div>
                      <div style={{ display: "flex", gap: 6 }}>
                        <Button size="compact" variant="secondary" disabled={busy || provider.connection_status !== "verified"} onClick={() => run(async () => { await apiClient.post(`/api-providers/${encodeURIComponent(provider.provider_id)}/models/${encodeURIComponent(item.model_record_id)}/actions/test`, { expected_revision: item.revision || provider.revision }); setMessage(`${item.model_id} retested.`); }, { reload: false })}>Test</Button>
                        <Button size="compact" variant="danger" disabled={busy} onClick={() => run(async () => { await apiClient.delete(`/api-providers/${encodeURIComponent(provider.provider_id)}/models/${encodeURIComponent(item.model_record_id)}`, { body: { expected_revision: item.revision || provider.revision } }); setMessage(`${item.model_id} removed.`); })}>Remove</Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>}
        </section>
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
