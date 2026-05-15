---
doc_id: configuration
doc_type: operator-guide
explains:
  features:
    - settings_system
    - trigger_run_management
  configs:
    - .env
    - config/runtime/control_plane.yaml
    - config/runtime/pipeline.yaml
---

# Configuration

FitCV uses layered configuration with clear ownership boundaries.

## Primary Runtime Inputs

- trigger base config file (`config_path` in `/runs` request; default `config/env.yaml`)
- persisted control-plane settings (`/admin/settings` and `/settings` surfaces)
- per-run trigger overrides (`config_overrides` in `/runs`)
- process environment variables for backend/provider credentials and runtime toggles

## Config Invariants

- secrets are env-only
- no secret values in YAML
- no secret key-name indirection in YAML
- `settings-used.json` is the run-time evidence snapshot

## Effective Settings Resolution

At trigger time, the control plane composes effective run settings in this order:

1. load base config from `config_path` (`TriggerRequest.config_path`)
2. load persisted active settings (`load_active_settings(...)`)
3. apply persisted settings into base config (`apply_settings_to_config`)
4. apply run-scoped trigger overrides (`config_overrides`) after validation/coercion
5. recompute derived compatibility fields
6. persist the run-scoped snapshot as `settings-used.json`/effective settings payload

Interpretation rules:

- `/admin/settings` edits persisted defaults for future runs only.
- trigger-time per-run overrides do not mutate saved defaults.
- completed-run truth belongs to the run-scoped effective settings snapshot.
- process environment variables control backend/provider credentials and runtime wiring; they are not persisted through settings-save routes.

## Settings Surface Ownership

The settings page intentionally mixes editable controls with metadata-only rows.

- editable: schema-backed controls with persistence keys and save handlers
- metadata-only: fixed/runtime-owned values shown for operator context and provenance

Examples:

- editable: retrieval funnel sizes, ranking weights, timing, run lifecycle guard, CV composition toggles
- metadata-only: fixed runtime-contract fields such as single-option model metadata

## Backend and Provider Routing

- backend routing: process env `FITCV_CP_DATA_BACKEND` selects backend mode (`sqlite` / `bigquery`) at runtime
- model/provider routing defaults: canonical owner is `config/runtime/control_plane.yaml`
  - `control_plane.providers.*.base_url`
  - `control_plane.providers.*.wire_api`
  - `control_plane.model_routing.parts.*.provider`
  - `control_plane.model_routing.parts.*.model`
- env overrides for LangGraph runtime expectation are optional and override-only:
  - `FITCV_LANGGRAPH_PROVIDER`
  - `FITCV_LANGGRAPH_MODEL`
  - `FITCV_LANGGRAPH_OPENAI_BASE_URL`
  - `FITCV_LANGGRAPH_WIRE_API`
- precedence for routing expectation:
  1. non-empty `FITCV_LANGGRAPH_*` env values (override-only path)
  2. control-plane defaults from `config/runtime/control_plane.yaml`
  3. fail fast if required fields remain unresolved
- provider credentials: read from process env

## Related Docs

- [setup.md](setup.md)
- [usage.md](usage.md)
- [architecture.md](architecture.md)
