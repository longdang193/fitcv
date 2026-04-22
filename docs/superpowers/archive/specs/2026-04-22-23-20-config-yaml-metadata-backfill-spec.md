---
layer: change
artifact_type: spec
status: proposed
parent_workstream: none
targets:
  - config/env.yaml
  - config/policy/cv_analysis.yaml
  - config/policy/cv.yaml
  - config/policy/ranking.yaml
  - config/runtime/pipeline.yaml
  - config/runtime/prompts.yaml
  - config/taxonomy/skill_synonyms.yaml
  - config/taxonomy/taxonomy.yaml
  - docs/features/*/lineage.generated.yaml
  - docs/generated/capability_lineage.yaml
related_features:
  - cv_system
related_stages:
  - ranking
  - cv_analysis
  - cv_generation
---

# Config YAML Metadata Backfill

## Summary

Backfill starter-style `# @architecture` metadata into the repo's canonical `config/*.yaml` files so config-owned behavior shows up truthfully in generated lineage, especially for config-backed CV-system capabilities.

## Problem

The repo's runtime and policy config files materially own behavior, but today they carry no architecture metadata. As a result:

- `configs` and `config_evidence` stay empty even for config-owned capabilities
- `components` cannot be derived from config surfaces
- config-owned behavior is visible only through Python loader code, not through the config files that actually own the runtime contract

## Goals

- Add starter-style YAML metadata to each material file under `config/`
- keep the metadata narrow and truthful
- use stable component ids for config-backed architectural surfaces
- refresh generated lineage and capability discovery after the metadata backfill

## Config Ownership Targets

### `config/runtime/pipeline.yaml`

Own:

- `cv_system.analysis-evidence-selection`

Component ids:

- `config.runtime.pipeline`

### `config/runtime/prompts.yaml`

Own:

- `cv_system.config-owned-generation-contract`
- `inspection_debugging.prompt-provenance-diagnostics`

Component ids:

- `config.runtime.prompts`

### `config/policy/cv_analysis.yaml`

Own:

- `cv_system.analysis-evidence-selection`
- `cv_system.fit-gate-resolution`

Component ids:

- `config.policy.cv-analysis`

### `config/policy/cv.yaml`

Own:

- `cv_system.config-owned-generation-contract`

Component ids:

- `config.policy.cv-generation`

### `config/policy/ranking.yaml`

Own:

- `cv_system.fit-gate-resolution`

Component ids:

- `config.policy.ranking`

### `config/taxonomy/taxonomy.yaml`

Own:

- `cv_system.analysis-grounded-validation`

Component ids:

- `config.taxonomy.role-and-domain`

### `config/taxonomy/skill_synonyms.yaml`

Own:

- `cv_system.analysis-grounded-validation`

Component ids:

- `config.taxonomy.skill-synonyms`

### `config/env.yaml`

Own:

- no direct product capability ownership in this phase

Component ids:

- `config.infrastructure.defaults`

This file should still carry metadata as a canonical config surface, but it should not be attached to feature capabilities unless inspection proves direct capability ownership.

## Non-Goals

- Do not assign code-defaulted enrichment settings to `config/*.yaml` when the
  defaults actually live in Python settings/schema code.
- Do not assign every config file to every feature that merely reads it.
- Do not use config metadata to replace direct code or test evidence.
- Do not force `satisfies` values onto config files without a real requirement source.

## Acceptance Criteria

- every YAML file under `config/` has a valid top-of-file `# @architecture` block
- config-backed capability lineage now shows truthful `configs`
- at least the directly config-owned CV and enrichment capabilities now show non-empty `components`
- `satisfies` stays empty unless explicitly and truthfully declared
- generated lineage and repo-wide capability lineage refresh cleanly
