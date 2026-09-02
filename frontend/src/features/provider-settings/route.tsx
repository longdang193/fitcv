import React, { useEffect, useState } from "react";
import { Button, LoadingState } from "../../components";
import { apiClient } from "../../lib/api-client";

type Provider = {
  provider_id: string;
  display_name: string;
  compatibility: "openai" | "anthropic";
  base_url: string | null;
  base_url_editable: boolean;
  api_type: string;
  connection_status: string;
  credential_configured: boolean;
  connection_revision: number | null;
  revision: number;
  models: Array<{ model_record_id: string; model_id: string; validation_status: string }>;
};
type Llm = { default_model_ref: string | null; revision: number; eligible_models: Array<{ model_record_id: string; provider_display_name: string; model_id: string }> };

export const ProviderSettingsPage: React.FC = () => {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [llm, setLlm] = useState<Llm | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [modelId, setModelId] = useState("");
  const [newProviderName, setNewProviderName] = useState("");
  const [newCompatibility, setNewCompatibility] = useState<"openai" | "anthropic">("openai");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [providerResponse, llmResponse] = await Promise.all([
        apiClient.get<{ data: Provider[] }>("/api-providers"),
        apiClient.get<{ data: Llm }>("/llm-configuration"),
      ]);
      const nextProviders = providerResponse.data.data || [];
      setProviders(nextProviders);
      setLlm(llmResponse.data.data);
      const provider = nextProviders.find((item) => item.provider_id === selectedId) || nextProviders[0];
      if (provider) {
        setSelectedId(provider.provider_id);
        setBaseUrl(provider.base_url || "");
      }
    } catch (error: any) {
      setMessage(error.message || "Settings could not be loaded.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const provider = providers.find((item) => item.provider_id === selectedId);
  const run = async (operation: () => Promise<void>) => {
    setBusy(true);
    setMessage("");
    try { await operation(); await load(); setMessage("Saved."); }
    catch (error: any) { setMessage(`${error.message || "Request failed."}${error.action ? ` ${error.action}` : ""}`); }
    finally { setBusy(false); }
  };

  const createProvider = () => run(async () => {
    const response = await apiClient.post<{ data: Provider }>("/api-providers", { display_name: newProviderName.trim(), compatibility: newCompatibility }, { idempotencyKey: crypto.randomUUID() });
    setNewProviderName("");
    setSelectedId(response.data.data.provider_id);
  });

  if (loading) return <LoadingState message="Loading API Providers and LLM Configuration..." />;
  return (
    <div className="content-container">
      <div className="page-head"><div><p className="eyebrow">Settings</p><h2>API Providers &amp; LLM Configuration</h2><p>Verify one provider connection, add a validated model, then set Default Route.</p></div></div>
      {message && <div className="notice" role="status">{message}</div>}
      <section className="section-card" style={{ padding: 20, display: "grid", gap: 14 }}>
        <h3 style={{ margin: 0 }}>API Providers</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}><input className="field-input" style={{ flex: 1, minWidth: 220 }} value={newProviderName} onChange={(event) => setNewProviderName(event.target.value)} placeholder="New provider name" disabled={busy} /><select className="field-input" style={{ width: 150 }} value={newCompatibility} onChange={(event) => setNewCompatibility(event.target.value as "openai" | "anthropic")} disabled={busy}><option value="openai">OpenAI-compatible</option><option value="anthropic">Anthropic-compatible</option></select><Button variant="secondary" disabled={busy || !newProviderName.trim()} onClick={createProvider}>Add Provider</Button></div>
        <label className="field-group"><span className="field-label">Provider</span><select className="field-input" value={selectedId} onChange={(event) => { const next = providers.find((item) => item.provider_id === event.target.value); setSelectedId(event.target.value); setBaseUrl(next?.base_url || ""); }}><option value="">Select provider</option>{providers.map((item) => <option key={item.provider_id} value={item.provider_id}>{item.display_name} ({item.compatibility})</option>)}</select></label>
        {provider && <>
          <label className="field-group"><span className="field-label">Base URL</span><input className="field-input" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} disabled={!provider.base_url_editable || busy} /></label>
          <label className="field-group"><span className="field-label">API key</span><input className="field-input" type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} autoComplete="off" disabled={busy} placeholder={provider.credential_configured ? "Stored key unchanged" : "Required to verify connection"} /></label>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}><Button variant="primary" disabled={busy || !apiKey.trim()} onClick={() => run(async () => { await apiClient.put(`/api-providers/${encodeURIComponent(provider.provider_id)}/connection`, { base_url: baseUrl || null, api_type: provider.api_type, api_key: apiKey, expected_revision: provider.revision }); setApiKey(""); })}>Verify and Save Connection</Button><span style={{ color: "var(--muted)", fontSize: 12, alignSelf: "center" }}>{provider.connection_status === "verified" ? "Connection verified" : "Not verified"}</span></div>
          <label className="field-group"><span className="field-label">Model ID</span><input className="field-input" value={modelId} onChange={(event) => setModelId(event.target.value)} disabled={busy} placeholder="e.g. openai/gpt-4o-mini" /></label>
          <Button variant="secondary" disabled={busy || !modelId.trim() || provider.connection_status !== "verified"} onClick={() => run(async () => { await apiClient.post(`/api-providers/${encodeURIComponent(provider.provider_id)}/models`, { model_id: modelId, expected_revision: provider.revision }, { idempotencyKey: crypto.randomUUID() }); setModelId(""); })}>Test and Add Model</Button>
          {provider.models.length > 0 && <div style={{ color: "var(--muted)", fontSize: 13 }}>Models: {provider.models.map((item) => `${item.model_id} (${item.validation_status})`).join(", ")}</div>}
        </>}
      </section>
      <section className="section-card" style={{ padding: 20, display: "grid", gap: 14, marginTop: 16 }}>
        <h3 style={{ margin: 0 }}>LLM Configuration</h3>
        <label className="field-group"><span className="field-label">Default Route</span><select className="field-input" value={llm?.default_model_ref || ""} disabled={busy || !llm} onChange={(event) => { if (!llm) return; void run(async () => { await apiClient.patch("/llm-configuration", { default_model_ref: event.target.value || null, expected_revision: llm.revision }); }); }}><option value="">Select a validated model</option>{llm?.eligible_models.map((item) => <option key={item.model_record_id} value={item.model_record_id}>{item.provider_display_name} · {item.model_id}</option>)}</select></label>
        {llm && llm.eligible_models.length === 0 && <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>No validated models. Verify a provider and add one above.</p>}
      </section>
    </div>
  );
};

export const route = { id: "provider-settings", path: "#/settings/providers", title: "API Providers & LLM", group: "settings" as const, order: 35, component: ProviderSettingsPage };
export default route;
