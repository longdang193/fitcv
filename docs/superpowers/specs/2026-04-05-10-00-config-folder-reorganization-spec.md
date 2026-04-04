---
feature_type: modify
feature_name: settings_system
status: draft
summary: "Reorganize repository configuration into one top-level config room with responsibility-based subfolders while preserving runtime compatibility during migration."
---

# Config Folder Reorganization Spec

## Summary

This spec proposes a directory-only reorganization of configurable files so the project has one obvious home for settings: `config/`.

Instead of keeping all config files flat under `config/`, the repo should group them into responsibility-based subfolders:

- environment and infrastructure
- runtime behavior
- business policy
- taxonomy and normalization

The goal is to make it easier for maintainers to answer:

- where do I change a runtime limit?
- where do I change a ranking or CV policy?
- where do I change a normalization map?
- which files are actual settings versus prompt content or rendering templates?

This is a layout and ownership refactor, not a semantic redesign of config values.

## Problem

The repo already centralizes many settings into `config/`, but the current flat layout is starting to blur responsibility boundaries:

- `pipeline.yaml` mixes model/runtime execution defaults with canonical pipeline limits
- `prompts.yaml` lives beside policy files even though it is really runtime prompt selection
- `cv_analysis.yaml`, `cv.yaml`, and `ranking.yaml` are all policy-oriented but are not grouped together
- `taxonomy.yaml` and `skill_synonyms.yaml` are normalization/taxonomy assets but look like peers of execution config

This makes the config room harder to scan as the system grows.

The current flat `config/` directory also makes it easier for future additions to drift into the wrong file or duplicate concerns.

## Goals

- Keep one top-level config room: `config/`
- Organize settings files into clear responsibility-based subfolders
- Preserve YAML as the baseline source of configurable defaults
- Preserve current runtime semantics during migration
- Keep prompt text and CV document templates outside the config room
- Make the loader contract explicit and easy to extend later

## Non-Goals

- Rewriting the whole config loader architecture
- Changing prompt text ownership
- Changing CV markdown template ownership
- Renaming every config key during the same migration
- Making all config files admin-editable

## Target Structure

```text
config/
  env.yaml
  runtime/
    pipeline.yaml
    prompts.yaml
  policy/
    ranking.yaml
    cv_analysis.yaml
    cv.yaml
  taxonomy/
    taxonomy.yaml
    skill_synonyms.yaml
```

## Proposed Migration Map

### 1. Environment / infrastructure

Keep environment-specific settings in:

```text
config/env.yaml
```

Expected content:

- `gcp_project`
- `bigquery_dataset`
- `service_account_key`
- `vertex_location`
- `paths.*`
- environment-specific overrides

### 2. Runtime behavior

Move execution/runtime files into:

```text
config/runtime/
```

#### `config/runtime/pipeline.yaml`

Moves from current:

- `config/pipeline.yaml`

Expected content:

- `gemini_model`
- `embedding_model`
- `enrichment_sleep_secs`
- `embedding_batch_size`
- `vector_max_candidate_skills`
- `retrieval_strategy`
- canonical nested runtime limits:
  - `pipeline.vector_search_top_n`
  - `pipeline.ai_score_top_n`
  - `pipeline.final_top_n`
  - `pipeline.evidence_top_k`

Legacy compatibility values such as top-level `vector_top_n` and `rerank_top_n` may remain temporarily during migration, but they should be treated as compatibility projections, not the canonical source.

#### `config/runtime/prompts.yaml`

Moves from current:

- `config/prompts.yaml`

Expected content:

- active prompt ids only, for example:

```yaml
prompts:
  enrich:
    extraction:
      prompt_id: enrich.extraction.v1
  ranking:
    ai_score:
      prompt_id: ranking.ai_score.v1
  cv_generation:
    write:
      prompt_id: cv_generation.write.v1
```

This file chooses active prompt versions but does not contain the prompt text itself.

### 3. Business policy

Move stage/business-rule policy files into:

```text
config/policy/
```

#### `config/policy/ranking.yaml`

Moves from current:

- `config/ranking.yaml`

Expected content:

- `ranking_weights`
- `preference_fit_weights`
- `fit_label_thresholds`
- `gap_thresholds`
- `missing_value_defaults`

#### `config/policy/cv_analysis.yaml`

Moves from current:

- `config/cv_analysis.yaml`

Expected content:

- `cv_analysis.semantic_alignment.*`
- `cv_analysis.selection_policy.*`

#### `config/policy/cv.yaml`

Moves from current:

- `config/cv.yaml`

Expected content:

- `cv.preset`
- `cv.generation.*`
- `cv.composition.*`
- `cv.content_rules.*`
- `cv.validation.*`

### 4. Taxonomy / normalization

Move normalization and taxonomy files into:

```text
config/taxonomy/
```

#### `config/taxonomy/taxonomy.yaml`

Moves from current:

- `config/taxonomy.yaml`

Expected content:

- role families
- neighbors
- canonical-role mappings
- other taxonomy-style classification structures

#### `config/taxonomy/skill_synonyms.yaml`

Moves from current:

- `config/skill_synonyms.yaml`

Expected content:

- skill normalization aliases and canonical mappings

## What Must Stay Outside `config/`

### Prompt text

Prompt content stays in:

```text
src/fitcv/prompts/templates/
```

Reason:

- these are stage prompt bodies, not configurable settings
- config should select prompt ids, not store prompt prose

### Final CV document template

The CV layout template stays in:

```text
templates/cv_template.md
```

Reason:

- this is a rendering/output template, not a settings file

## Loader Contract

The config loader should load in this logical order:

1. `config/env.yaml`
2. `config/runtime/pipeline.yaml`
3. `config/runtime/prompts.yaml`
4. `config/policy/ranking.yaml`
5. `config/policy/cv_analysis.yaml`
6. `config/policy/cv.yaml`
7. `config/taxonomy/taxonomy.yaml`
8. `config/taxonomy/skill_synonyms.yaml`

The loader may support temporary fallback reads from the old flat paths during the migration window, but the new subfolder layout becomes the declared source-of-truth structure.

## Compatibility Strategy

This migration should be low-risk and staged.

### Phase 1: Introduce new layout

- create the new subfolders
- copy or move files into the new locations
- update loader to prefer new paths
- preserve old-path fallback loading for one migration window

### Phase 2: Stabilize callers

- keep runtime key compatibility where existing modules still read projected legacy keys
- keep settings UI and docs working against the same resolved config

### Phase 3: Remove flat-path compatibility

- remove old flat config-file fallback paths only after:
  - tests pass
  - Docker/manual runs pass
  - source-of-truth docs are updated

## Invariants

- `config/` is the only top-level room for configurable YAML assets
- subfolders are responsibility-based, not stage-name-based by default
- prompt text does not move into config
- CV output template does not move into config
- runtime behavior must remain unchanged through the initial migration
- old paths may be supported temporarily, but the new structure is the declared target

## Risks

- mixed old/new loader behavior could briefly make path resolution harder to reason about during migration
- tests may rely on old relative config-discovery assumptions
- tools or scripts outside the main loader may still reference old flat paths
- generated docs may drift if not refreshed after source-layer updates

## Acceptance Criteria

- the repo has one top-level config room with the responsibility-based subfolder structure described here
- loader behavior prefers the new paths
- runtime behavior remains compatible during the migration window
- docs clearly distinguish:
  - config files
  - prompt templates
  - CV rendering templates
- maintainers can find runtime, policy, and taxonomy settings without scanning one flat mixed directory

## Affected Features And Docs

Affected features:

- `settings_system`
- `cv_system`
- `inspection_debugging`

Primary source-of-truth docs to update during implementation:

- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/settings_system.yaml)
- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/FitCV-pipeline.md)

Generated refresh required:

- yes
