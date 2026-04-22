---
layer: operating_system
artifact_type: spec
status: proposed
parent_workstream: none
targets:
  - scripts/sync_architecture_docs.py
  - scripts/validate_adoption_shape.py
  - tests/test_sync_architecture_docs.py
  - tests/test_validate_adoption_shape.py
  - docs/operating_system/project-adoption-migration-guide.md
  - docs/operating_system/feature-lifecycle.md
related_features: []
related_stages: []
---

# Lineage Config And Component Schema Patch

## Summary

Patch the local Mode B generator and validator so `lineage.generated.yaml` no longer treats `components` and `satisfies` as decorative placeholders, and so `configs` / `config_evidence` come from real config metadata rather than staying empty because `config/` is not scanned.

## Problem

The current local lineage contract has three gaps:

- `configs` and `config_evidence` stay empty because `scripts/sync_architecture_docs.py` only buckets `repo_config/` as config evidence and does not ingest `config/*.yaml`.
- `components` and `component_evidence` stay empty because the generator never produces component ownership from any metadata source.
- `satisfies` is hardcoded to `[]`, so the field exists in generated outputs but has no producer path.

This creates a schema that claims more architectural structure than the repo can currently prove.

## Goals

- Keep `components` as a first-class lineage field.
- Keep `satisfies` as a first-class lineage field.
- Teach the generator how to ingest starter-style YAML `# @architecture` metadata from `config/*.yaml`.
- Populate `configs`, `config_evidence`, `components`, and `component_evidence` from truthful metadata.
- Stop validating `components` as if they were filesystem paths.
- Validate YAML config metadata shape and capability references when metadata is present.

## Non-Goals

- Do not invent a broad new requirement ontology for `satisfies`.
- Do not force every capability to have `components` or `satisfies` data immediately.
- Do not redesign the wider lineage schema in this phase.

## Target Contract

### Generator

`scripts/sync_architecture_docs.py` should:

- scan `config/**/*.yaml` for starter-style `# @architecture` comment blocks
- treat `config/` files as config evidence surfaces
- support metadata fields:
  - `owner`
  - `features`
  - `stages`
  - `capabilities`
  - `components`
  - `satisfies`
  - `role`
  - `canonical`
- populate:
  - `configs` as a list of config file paths
  - `config_evidence` as typed evidence records for those paths
  - `components` as stable component ids declared by metadata
  - `component_evidence` as typed evidence records that preserve both component id and source path
  - `satisfies` as declared requirement or contract ids when metadata provides them

### Validator

`scripts/validate_adoption_shape.py` should:

- continue validating path-backed evidence lists for:
  - `code`
  - `tests`
  - `docs`
  - `specs`
  - `plans`
  - `configs`
- stop treating `components` as path-backed evidence
- validate `components` as a list of non-empty strings
- validate `satisfies` as a list of non-empty strings
- validate `config_evidence` and `component_evidence` shape when present
- validate YAML `# @architecture` metadata in `config/*.yaml` when present, including:
  - parseable comment-block YAML
  - known capability ids
  - string-list shape for `capabilities`, `components`, and `satisfies`

## Source Metadata Model

The starter-aligned YAML metadata block should use comment-prefixed YAML at the top of the file:

```yaml
# @architecture
# owner: cv_system
# features:
#   - cv_system
# stages:
#   - cv_generation
# capabilities:
#   - cv_system.config-owned-generation-contract
# components:
#   - config.runtime.prompts
# role: config
# canonical: true
```

`satisfies` remains optional. The generator should emit it only when explicitly declared by source metadata.

## Acceptance Criteria

- `config/*.yaml` metadata can be parsed by the generator
- generated lineage uses real config evidence for config-owned capabilities
- generated lineage can carry non-empty `components`
- validator no longer misclassifies `components` as filesystem paths
- validator rejects malformed YAML config metadata and unknown config capability ids
- sync and validation tests cover the new ingestion path

