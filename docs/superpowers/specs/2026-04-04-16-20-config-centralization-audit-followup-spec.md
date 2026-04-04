---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Centralize remaining shared prompts, policy knobs, and default settings so stage behavior stops drifting across code, config YAML, and admin schema."
invariants:
  - "Configuration must stay split by responsibility: runtime, policy, taxonomy, prompts, and schema/contract constants are not the same kind of config."
  - "A config miss may trigger a safe fallback, but defaults should live in one authoritative place."
  - "Prompt text should not be duplicated across multiple Python modules once a prompt-registry path exists."
  - "Stage-owned policy remains stage-owned even after centralization."
---

# Config Centralization Audit Follow-Up Spec

## Triage

Feature type: MODIFY  
Summary: Centralize the remaining shared prompts, settings defaults, and reusable policy/taxonomy surfaces that are still split across code and config.  
Reasoning: The project already has a strong config base, but important prompt text, policy weights, and UI defaults still live in multiple modules. This is a managed feature change because it alters how existing `cv_system` and `settings_system` behavior is sourced and validated, without changing the core stage order.  
Invariants:
- Config must remain responsibility-scoped rather than becoming one giant catch-all file.
- Centralization must reduce drift, not just move literals around.
- Prompt content, policy defaults, and schema/version constants should each have clear ownership.
- Admin-editable settings must not duplicate YAML defaults as a second truth source.
Dependencies:
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py)
- [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/ai_score.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/evidence.py)
- prompt registry files under [src/fitcv/prompts](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts)
Affected stages:
- `enrich`
- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`
Affected features:
- `cv_system`
- `settings_system`
- `inspection_debugging`
Primary lens: mixed
Affected docs:
  feature_yaml:
  - [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
  - [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/settings_system.yaml)
  - [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
  feature_history:
  - [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)
  - [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/settings_system/history.md)
  - [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/history.md)
  feature_docs: []
  cross_cutting_docs:
  - [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/FitCV-pipeline.md)
  readme: none
  generated:
  - `docs/generated/feature_overview.md`
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_capabilities_index.yaml`
Generated refresh required: yes  
Spec needed: yes  
Plan needed: yes  
Risk level: medium

## Why

The project already centralizes a lot of shared configuration well:

- runtime/model defaults in [pipeline.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/pipeline.yaml)
- ranking policy in [ranking.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/ranking.yaml)
- taxonomy in [taxonomy.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/taxonomy.yaml)
- CV composition in [cv.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/cv.yaml)
- one prompt-registry path for enrich in [registry.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/registry.py)

But the audit shows several important drifts remain:

- prompt text is still embedded directly in `ranking` and `cv_generation` code
- admin settings duplicate YAML defaults in the settings schema
- `cv_analysis` evidence-selection policy still depends on hardcoded module constants
- model-name fallbacks and contract/schema versions are still scattered across modules
- shared analysis-channel semantics are duplicated between retrieval and generation layers

This makes tuning slower and raises the chance that:

- the UI shows one “default” while the runtime actually uses another
- one stage evolves its prompts without the same provenance or contract shape as another
- policy changes require code edits instead of config edits
- tests and docs drift from actual runtime defaults

## Problem Statement

The current config system is strong but incomplete. Important shared behavior still lives in:

- Python string literals
- repeated module constants
- duplicated admin-schema defaults
- repeated fallback model names and schema/version strings

This creates four kinds of drift:

1. **Prompt drift**
- `enrich` uses a prompt registry
- `ranking` and `cv_generation` still embed prompt text directly in code

2. **Default-value drift**
- YAML contains defaults
- admin settings schema repeats many of the same defaults independently

3. **Policy drift**
- `cv_analysis` selection weights, quotas, and scoring bonuses/penalties are still owned by code constants rather than declarative config

4. **Contract drift**
- schema/version constants and stage-channel identifiers are repeated across modules without one canonical source

## Goals

1. Centralize prompt ownership for all major LLM-backed stages.
2. Remove duplicated defaults between config YAML and admin settings schema.
3. Move stage-policy knobs that are meant to be tuned into declarative config.
4. Centralize reusable contract/version constants in one code-owned module.
5. Keep responsibility boundaries clear between:
- runtime config
- business policy
- taxonomy/normalization
- prompt registry
- schema/version contracts

## Non-Goals

- replacing the current config system wholesale
- moving all local constants into config
- making every prompt admin-editable in this rollout
- turning algorithmic flow into declarative YAML
- centralizing one-off implementation details used in exactly one local function

## Audit Findings

### 1. Prompt centralization is incomplete

Current state:

- `enrich` prompt uses the prompt registry and template path
- `ranking` prompt text is built inline in [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/ai_score.py)
- `cv_generation` guidance and writer instructions are embedded in [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)

Impact:

- prompt provenance is uneven across stages
- editing prompts requires code changes for some stages but not others
- prompt schema/versioning is stage-specific and inconsistent

### 2. Settings defaults are duplicated between YAML and the admin schema

Current state:

- YAML files already define baseline defaults
- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py) repeats many of them as `default`

Impact:

- UI defaults can drift from runtime defaults
- future config changes require edits in two places
- tests may silently validate the wrong source of truth

### 3. `cv_analysis` policy is still partly hardcoded

Current state:

[evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/evidence.py) still owns policy-like constants such as:

- channel weights
- default experience/project/achievement quotas
- selection bonuses and penalties
- type-weight factors

Impact:

- tuning requires code edits
- policy visibility is lower than it should be
- runtime contract is harder to explain from config and settings

### 4. Model fallbacks and contract/version constants are scattered

Current state:

- `gemini-2.5-flash`, `text-embedding-005`, `v1`, and schema/version ids appear across multiple modules

Impact:

- fallback behavior is harder to reason about
- stage contracts are versioned, but their constants are not centrally discoverable
- reuse and artifact contracts are more fragile than necessary

### 5. Analysis-channel semantics are duplicated

Current state:

- `required_skill_support`, `role_alignment`, `domain_alignment`, and `responsibility_alignment` live in `cv_analysis`
- `cv_generation` separately embeds prose about how those channels should be used

Impact:

- channel meaning can drift between selection and writing
- generation guidance is harder to update consistently

## Recommended Design

Use a **responsibility-split central configuration model** with five owned surfaces:

1. **Prompt registry**
2. **Config YAML for runtime and policy**
3. **Code-owned schema/version contract module**
4. **Taxonomy/normalization config**
5. **Settings-schema metadata that derives defaults from config**

## Centralization Targets

### A. Expand the prompt registry to all major LLM-backed stages

Keep prompt ownership in `src/fitcv/prompts/`.

Recommended new prompt ids:

- `ranking.ai_score.v1`
- `cv_generation.write.v1`
- later, optionally:
  - `cv_generation.repair.v1`
  - `cv_generation.validation_assist.v1` if needed

Expected changes:

- move long prompt text out of [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/ai_score.py)
- move major writer-instruction blocks out of [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- keep stage-specific context rendering in code
- keep prompt prose and template files in the registry/templates path

This preserves:

- one place for prompt ids
- template-path provenance
- prompt versioning consistency across stages

### B. Make YAML the only source of baseline defaults

Keep [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/settings_schema.py) as:

- metadata
- validation rules
- display labels/descriptions
- option lists
- config paths

But stop treating it as an independent default store.

Recommended rule:

- default values displayed in the admin UI should be resolved from loaded config
- schema entries may keep a fallback only when the config path is intentionally optional

This should apply especially to:

- pipeline retrieval/timing defaults
- ranking weights and thresholds
- `cv_analysis` semantic-alignment values
- CV generation defaults

### C. Add a dedicated `cv_analysis` policy config slice

Create a new config surface for policy values now owned by [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/evidence.py).

Recommended file:

- `config/cv_analysis.yaml`

Recommended contents:

- channel selection weights
- type-weight factors
- evidence-type quotas
- selection bonuses / penalties
- residual-score contribution factors
- maybe channel display metadata if reused downstream

What stays in code:

- evidence-retrieval algorithms
- embedding calls
- scoring flow
- local helper math

### D. Add one code-owned contract/version module

Create a small shared module for:

- schema version constants
- contract version constants
- stable stage artifact schema ids
- maybe shared channel ids if used in more than one stage

Recommended file:

- `src/fitcv/contracts.py`
  or
- `src/fitcv/schema_versions.py`

Why code-owned, not YAML:

- these are software-contract identifiers
- they are tightly coupled to runtime behavior and tests
- they should be importable without config parsing

### E. Centralize shared model and config accessors

Keep raw YAML values in config, but centralize how code reads them.

Recommended helper accessors in [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py):

- `get_gemini_model(config)`
- `get_embedding_model(config)`
- `get_cv_generation_model(config)`
- `get_ranking_prompt_id(config)`
- `get_cv_generation_prompt_id(config)`

This avoids repeating:

- raw key traversal
- raw string fallbacks
- stage-local default literals

### F. Centralize analysis-channel semantics

Create one shared contract for channel meaning.

Recommended shape:

- code-owned constant map or small config-backed structure for:
  - `required_skill_support`
  - `role_alignment`
  - `domain_alignment`
  - `responsibility_alignment`

Include:

- channel id
- display label
- intended meaning
- allowed downstream uses

This gives `cv_analysis` and `cv_generation` one shared interpretation.

## Proposed Target Structure

```text
config/
├── env.yaml
├── pipeline.yaml
├── ranking.yaml
├── cv.yaml
├── cv_analysis.yaml
├── taxonomy.yaml
├── skill_synonyms.yaml
└── prompts.yaml              # active prompt ids per stage

src/fitcv/
├── config.py                 # load + validate config, accessors
├── contracts.py              # schema/contract/version constants
└── prompts/
    ├── registry.py
    ├── renderer.py
    └── templates/
        ├── enrich_extraction_v1.md
        ├── ranking_ai_score_v1.md
        └── cv_generation_write_v1.md
```

## Migration Order

### Phase 1: Prompt centralization

Move:

- ranking AI-score prompt
- CV generation writer guidance

into the prompt registry/templates path.

This is the highest-value centralization because it improves:

- provenance
- consistency
- prompt evolution safety

### Phase 2: Settings default deduplication

Refactor settings schema so defaults are read from loaded config instead of duplicated metadata.

This is the biggest drift-reduction step.

### Phase 3: `cv_analysis` policy extraction

Move evidence-selection policy knobs into `config/cv_analysis.yaml`.

This improves tunability and makes the stage contract easier to explain.

### Phase 4: Contract/version centralization

Move scattered schema/version literals into one code-owned module.

This is lower risk and easy to verify once the bigger config surfaces are stable.

### Phase 5: Shared channel-semantics contract

Use one owned map so `cv_analysis` and `cv_generation` stay aligned.

## Validation Rules

The central loader and schema layer should validate:

### Prompt config

- prompt ids must exist in the registry
- prompt templates must exist on disk
- prompt ids must be stage-compatible

### YAML-driven policy

- weights sum correctly where required
- quotas are non-negative integers
- known channel ids only
- no unknown top-level policy keys inside stage-owned config blocks

### Settings schema

- each setting path exists in the loaded config or is explicitly marked optional
- settings metadata does not define a conflicting baseline default

### Contracts

- schema/version identifiers remain unique
- reuse/serialization contract ids remain stable and explicit

## Risks

- centralizing too aggressively can turn local implementation details into noisy config
- prompt extraction can accidentally change prompt wording or whitespace-sensitive behavior
- settings default deduplication may surface hidden assumptions in tests
- a new `cv_analysis.yaml` file adds one more config surface, so ownership has to stay well documented

## Rollback Strategy

Rollback trigger:

- prompt-registry rollout changes stage outputs unexpectedly
- settings UI no longer reflects effective runtime defaults
- `cv_analysis` policy extraction causes config confusion rather than clarity

Rollback method:

- keep existing YAML files
- revert prompt-registry expansion stage by stage
- keep any new config accessors that are still useful
- revert only the extracted policy slice if it proves too noisy

## Acceptance Criteria

1. `enrich`, `ranking`, and `cv_generation` all use a shared prompt-registry path for primary prompt content.
2. Admin settings no longer maintain a competing second source of baseline defaults.
3. `cv_analysis` policy knobs that are intended for tuning live in declarative config rather than only in module constants.
4. Shared model-name and prompt-id accessors live in one place.
5. Schema/version constants are discoverable from one code-owned module.
6. Shared analysis-channel semantics no longer drift between retrieval and generation layers.

## Recommendation

If this is implemented incrementally, the best order is:

1. prompt centralization
2. settings-default deduplication
3. `cv_analysis` policy extraction
4. schema/version module
5. channel-semantics contract

That sequence gives the highest immediate drift reduction with the lowest risk.
