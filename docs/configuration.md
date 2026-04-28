---
doc_id: configuration
doc_type: operator-guide
explains:
  features:
    - settings_system
    - trigger_run_management
  configs:
    - config/env.yaml
    - config/runtime/pipeline.yaml
    - config/runtime/prompts.yaml
---

# Configuration

FitCV separates configuration by **runtime purpose** and by **ownership layer**.
This page is the cross-cutting map; the detailed semantics still live in the
config files, settings schemas, and managed architecture sources.

## Runtime Configuration Layers

### Repo-managed config files

The checked-in `config/` tree owns stable runtime defaults:

- `config/env.yaml`
  - environment-facing runtime values used by the app and worker
- `config/runtime/pipeline.yaml`
  - pipeline defaults and runtime behavior
- `config/runtime/prompts.yaml`
  - prompt selection and prompt registry inputs
- `config/policy/*.yaml`
  - policy-level CV, ranking, and analysis behavior
- `config/taxonomy/*.yaml`
  - taxonomy and synonym inputs such as `skill_synonyms.yaml`

### Persisted operator settings

The control plane also supports BigQuery-backed settings overrides. Those are
operator-facing runtime adjustments, not replacements for checked-in config
ownership.

In practice, effective run configuration resolves in this order:

1. checked-in YAML defaults
2. persisted active settings from the control plane
3. per-run overrides captured at trigger time
4. run-scoped `settings-used.json` exports as the historical record of what a finished run actually used

That layering matters because each run stores its own effective settings
snapshot and later inspection should reflect what the run actually used.

On `/admin/settings`, operators edit future-run defaults only. The page now
keeps fixed runtime-owned fields as metadata, keeps editable controls aligned
with real schema-backed persistence keys, and treats per-run overrides plus
`settings-used.json` as run-detail concerns rather than live settings-form
state.

The settings surface now includes a bounded `Agentic` section for schema-backed
future-run defaults. That section owns the late-stage agentic enablement flag
and the semantic-alignment controls that shape agentic retrieval and analysis
behavior. Advanced agentic tuning stays behind disclosure, while fixed runtime
metadata such as the current semantic-alignment model remains explanatory rather
than editable.

## Environment Variables And Services

Important runtime values include:

- `GCP_PROJECT`
- `BIGQUERY_DATASET`
- `REDIS_URL`
- `GOOGLE_APPLICATION_CREDENTIALS`

Local startup helpers and Docker both provide these, but through slightly
different paths.

## Managed Architecture Metadata Configuration

This repo is in `managed_architecture_metadata` mode. The human-owned metadata
inputs are not the generated YAML files; they are:

- `docs/features/<feature_id>/feature.source.yaml`
- `docs/stages/<stage_id>.source.yaml`
- selected root and operating-system docs that describe repo-wide behavior

Generated contracts and lineage outputs should be refreshed through the wrapper:

```powershell
python scripts/sync_architecture_docs.py
```

## What Belongs Where

- change `config/` when product/runtime defaults change
- change control-plane settings code when the editable settings surface changes
- change `docs/features/*` or `docs/stages/*` when managed architecture
  ownership or evidence changes
- avoid hand-editing generated docs in `docs/generated/`, generated feature
  contracts, or generated stage contracts

## Related Docs

- [setup.md](setup.md)
- [usage.md](usage.md)
- [architecture.md](architecture.md)
- [fitcv-control-plane-setup.md](fitcv-control-plane-setup.md)
