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

- `config/runtime/control_plane.yaml`
  - backend type (`sqlite` or `bigquery`)
  - provider registry
  - model-routing parts
  - observability flags
- `config/runtime/pipeline.yaml`
  - stage/runtime defaults
- `.env` / process env
  - secrets and env overrides

## Config Invariants

- secrets are env-only
- no secret values in YAML
- no secret key-name indirection in YAML
- `settings-used.json` is the run-time evidence snapshot

## Effective Settings Resolution

1. checked-in runtime YAML defaults
2. persisted control-plane settings overrides
3. run trigger-time overrides
4. runtime env overrides
5. run-scoped `settings-used.json` captures final effective view

## Backend and Provider Routing

- backend routing: resolved by control-plane runtime config + env override
- model/provider routing: resolved by `control_plane.model_routing.parts`
- provider credentials: read from process env only

## Managed Docs Note

Treat `docs/generated/`, generated feature contracts, and generated stage contracts as outputs. Refresh via sync scripts; do not hand-edit generated outputs.

## Related Docs

- [setup.md](setup.md)
- [usage.md](usage.md)
- [architecture.md](architecture.md)
