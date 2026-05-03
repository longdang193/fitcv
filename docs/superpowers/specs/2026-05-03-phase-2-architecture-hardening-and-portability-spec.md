---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
targets:
  - config/runtime/pipeline.yaml
  - config/runtime/control_plane.yaml
  - src/fitcv/config.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/
  - tests/test_fitcv_cp/
related_features: []
related_stages: []
---

# Phase 2 Architecture Hardening And Portability Spec

## 1) Summary

Strengthen Phase 2 architecture depth to Phase-1 quality by:

1. centralizing runtime configuration for model routing and control-plane data backend,
2. introducing an explicit model-tier contract (cheap model vs reasoning model),
3. adding provider-agnostic adapter contracts so providers can change without business-logic rewrites,
4. making observability tooling a first-class architecture layer,
5. decoupling control-plane startup from BigQuery-only assumptions so sqlite mode is a first-class portability path.

This spec is intentionally architecture-first and execution-bounded.

## 2) Problem Statement

Current Phase 2 portability surfaces are functional but too shallow in three ways:

1. **Config sprawl**
   - model/runtime/backend choices are spread across env vars, runtime yaml, and code literals.
   - no single contract declares “simple-task model” vs “reasoning-task model”.

2. **BigQuery-coupled startup**
   - control-plane startup path assumes GCP/BigQuery at import time.
   - local development and non-GCP execution fail before app boot when credentials are absent.

3. **Portability intent > implementation contract**
   - docs mention portability direction, but backend selection semantics and migration phases are not explicit enough for safe implementation sequencing.

4. **Observability layer under-specified**
   - provider/model/backend behavior lacks a dedicated telemetry contract for latency, fallback, failure, and cost signals.

## 3) Goals

1. Provide one central config contract for:
   - model routing tiers,
   - control-plane backend selection,
   - backend-specific connection settings.
2. Make backend choice explicit and deterministic at startup.
3. Allow non-GCP app boot path for sqlite mode (even if initial sqlite feature surface is bounded).
4. Keep current BigQuery behavior as default and backward compatible.
5. Make provider switching (for example Kimi via OpenAI-compatible API) configuration-only for supported task parts.
6. Enforce strict secret hygiene: no secrets and no secret key names in config yaml.

## 4) Non-Goals

1. Full parity migration of every BigQuery query path to sqlite in one pass.
2. Replacing existing policy/runtime files wholesale.
3. Changing ranking/CV decision semantics in this architecture pass.
4. Introducing dynamic hot-swap of backend/provider without restart in this phase.

## 5) Architecture Contract

## 5.1 Central Config Ownership

Use layered config ownership (not one giant file):

- `config/runtime/control_plane.yaml`
- `config/runtime/pipeline.yaml` (existing pipeline behavior/tuning)
- `.env` (secrets + deployment env only)

Owned sections:

1. `control_plane.data_backend`
   - `type`: `bigquery | sqlite`
   - backend-specific connection keys

2. `control_plane.providers`
   - provider registry metadata (non-secret only), such as base URLs and provider capabilities

3. `control_plane.model_routing`
   - per-task-part provider/model routing
   - optional tier defaults and overrides for known task families

4. `control_plane.observability`
   - tracing/logging/metrics contract for provider, model, backend, retries, latency, and fallbacks

5. `control_plane.feature_flags`
   - portability toggles and staged rollout guards

`src/fitcv/config.py` becomes the canonical loader and accessor layer.

## 5.2 Model Routing Tier Contract

Two explicit tiers:

1. **Simple-task model (cheap)**
   - high-volume, low-reasoning tasks
   - example: routine extraction/triage boilerplate

2. **Reasoning-task model**
   - complex decision/repair/explanation tasks
   - example: ambiguity resolution, structured repair, policy-heavy reasoning

Consumers must request model through a routing key (task part or tier), not hardcode provider model names.

## 5.3 Provider Adapter Contract

Introduce provider abstraction so each part can use different APIs/models with stable internal interfaces:

1. `LLMClient.generate(...)`
2. `EmbeddingClient.embed(...)`

Provider-specific transport/adaptation lives in isolated adapter modules. Business logic consumes only adapter interfaces.

## 5.4 Backend Selection Contract

Startup behavior:

1. resolve backend from centralized config with env override support,
2. initialize only selected backend dependencies,
3. fail with clear backend-specific diagnostics (not generic import-time tracebacks).

Default remains:

- backend `bigquery`

Portable local mode:

- backend `sqlite`

## 5.5 Observability Tooling Contract

Observability is a first-class architecture layer, not optional diagnostics.

Must emit structured signals for:

1. request identity: `run_id`, `trace_id`, stage, task part
2. model execution: provider, model, latency, retries, timeout/failure class
3. backend execution: selected backend, unsupported capability checks, fallback behavior
4. policy events: routing decisions and override paths

Must support OTEL-compatible export when enabled and local structured logs when exporter is unavailable.

## 5.6 Secret Hygiene Contract

Strict rule:

1. config yaml must not contain secret values
2. config yaml must not contain secret env-key names (for example `api_key_env`)
3. secrets are loaded only from process environment (`.env` / deployment env injection)

## 6) Data/Config Schema (Proposed)

```yaml
control_plane:
  data_backend:
    type: bigquery  # bigquery | sqlite
    bigquery:
      project: fitcv-491123
      dataset: fitcv
    sqlite:
      path: data/fitcv_cp.sqlite3

  providers:
    openai_compatible:
      base_url: https://api.moonshot.ai/v1
    openai:
      base_url: https://api.openai.com/v1

  model_routing:
    parts:
      enrich_extraction:
        provider: openai_compatible
        model: kimi-k2-instruct
      cv_generation_structured_write:
        provider: openai_compatible
        model: kimi-k2-thinking
      cv_analysis_semantic_alignment:
        provider: openai
        model: text-embedding-3-large
    task_overrides: {}

  observability:
    emit_model_routing_diagnostics: true
    emit_backend_capability_diagnostics: true
    otel_export_enabled: true

  feature_flags:
    sqlite_mode_enabled: true
```

## 7) Migration Phases

## Phase A: Config Centralization

1. Add `control_plane` config file and loader accessors.
2. Keep legacy env reads as fallback, with warning logs.
3. Add tests for config hydration and precedence.

## Phase B: Startup Decoupling

1. Move backend initialization behind a backend resolver.
2. Prevent unconditional BigQuery client creation during sqlite startup.
3. Add health diagnostics exposing selected backend.
4. Resolve provider adapters at startup with clear validation errors for unsupported routing entries.

## Phase C: SQLite Capability Rollout

1. Define minimum sqlite-supported route set.
2. Introduce bounded storage adapter abstraction for control-plane store calls.
3. Expand feature parity incrementally by route family.

## 8) Compatibility And Risk

## Compatibility

1. Existing BigQuery deployments must continue working without config changes.
2. Current env-based deployment scripts remain valid during transition.

## Risks

1. Hidden BigQuery assumptions outside startup path.
2. Behavioral drift between backends if adapter contract is unclear.
3. Partial sqlite enablement confusing operators.

## Mitigations

1. explicit capability matrix in docs,
2. route-level backend support checks with clear messages,
3. test matrix per backend mode.
4. provider compatibility checks at startup and in CI contract tests.

## 9) Validation Gates

Required for each migration phase:

```powershell
python scripts/validate_repo_contracts.py --fast
python scripts/validate_planning_lifecycle.py --strict
pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py
```

Additional backend tests (new):

- config precedence tests (env vs central config),
- startup tests for `bigquery` and `sqlite`,
- backend capability assertion tests.
- provider-routing resolution tests by task part.
- observability emission tests (routing + backend diagnostics fields).

## 10) Acceptance Criteria

1. Central config defines model tiers and backend selection.
2. Control-plane starts in `sqlite` mode without requiring GCP ADC.
3. BigQuery mode remains default and backward compatible.
4. Model selection for control-plane task families can be switched by config only.
5. Portability/docs surface includes explicit backend capability boundaries.
6. Observability layer emits provider/model/backend diagnostics for all routed LLM calls.
7. Secret hygiene contract is enforced: no secret values or secret key names in yaml.

## 11) Decision Record

Recommendation: proceed with Phase A + Phase B immediately, then implement Phase C in bounded waves with explicit capability checkpoints.
