---
feature_type: add
feature_name: prompt_management
status: draft
summary: "Centralize prompt templates, metadata, and provenance so stage prompts stop drifting across enrich, ranking, and CV generation."
invariants:
  - Stage business logic stays in stage modules; only prompt text, prompt metadata, and rendering move into a shared prompt layer.
  - Existing stage behavior must remain reproducible through explicit prompt IDs and prompt versions.
  - Run inspection surfaces must be able to tell which effective prompt definition each stage used.
---

# Central Prompt Registry Spec

## Summary

Introduce a shared prompt-management layer for LLM-backed stages so prompt text, prompt metadata, and prompt provenance are managed in one place instead of being embedded separately in `enrich.py`, `ai_score.py`, and `cv_generator.py`.

This is a cross-cutting architecture change. It does not change the stage sequence. It changes how prompts are defined, loaded, versioned, rendered, and inspected.

## Problem

Prompt construction is currently scattered across stage modules:

- `src/fitcv/enrich.py`
- `src/fitcv/ai_score.py`
- `src/fitcv/cv_generator.py`

That creates a few recurring problems:

- prompt wording drifts across modules without a shared contract
- prompt versioning is inconsistent across stages
- reviewing prompt changes is harder because prompt text is mixed with stage code
- inspection/debugging cannot easily answer "which exact prompt definition did this run use?"
- stage-specific prompt iteration becomes harder than necessary, especially for `enrich`

## Goals

- Centralize prompt templates and prompt metadata.
- Keep stage modules responsible for stage logic, parsing, and validation.
- Make prompt selection explicit by `prompt_id` and `prompt_version`.
- Support prompt rendering with stage-specific runtime context.
- Persist prompt provenance into run inspection/debug surfaces.
- Make prompt text easier to review and update without digging through stage code.

## Non-Goals

- Replacing stage-local response schemas with a central schema registry in this phase
- Building a UI prompt editor in this phase
- Storing every fully rendered prompt body in BigQuery by default
- Changing the existing stage ordering or stage ownership

## Current State

### Prompt construction lives in code

- `enrich.py` builds the extraction prompt inline via `build_extraction_prompt(...)`
- `ai_score.py` builds the reranking/scoring prompt inline via `build_scoring_prompt(...)`
- `cv_generator.py` builds generation prompts inline via `build_generation_prompt(...)` and `build_structured_generation_prompt(...)`

### Prompt settings are partially centralized already

The runtime config already carries some prompt-related settings:

- model names
- `cv.generation.prompt_version`

But the actual prompt bodies and their metadata are not centrally managed.

## Proposed Design

### 1. Add a shared prompt registry layer

Introduce a new prompt package under `src/fitcv/prompts/`.

Recommended layout:

```text
src/fitcv/prompts/
├── __init__.py
├── registry.py
├── loader.py
├── models.py
├── renderer.py
└── templates/
    ├── enrich_extraction_v1.md
    ├── ai_score_v1.md
    ├── cv_generation_v1.md
    └── cv_generation_structured_v1.md
```

### 2. Separate prompt concerns from stage concerns

The prompt layer should own:

- prompt IDs
- prompt versions
- prompt template files
- prompt metadata such as owning stage and intended model family
- rendering inputs and fallback defaults

The stage modules should continue to own:

- input preparation
- response schema definitions
- parsing and validation
- retries and fallbacks
- stage-local post-processing

### 3. Prompt definitions become named artifacts

Each prompt should be addressed by a stable identifier such as:

- `enrich.extraction.v1`
- `ranking.ai_score.v1`
- `cv.generation.v1`
- `cv.generation_structured.v1`

Each definition should include metadata like:

```yaml
prompt_id: enrich.extraction.v1
stage_id: enrich
template_path: enrich_extraction_v1.md
model_family: gemini
owner_module: fitcv.enrich
summary: Structured JD extraction prompt for enrich stage.
```

The metadata may live in Python objects or small YAML sidecars. Phase 1 may keep the registry in Python if that is simpler and more testable.

### 4. Templates move out of stage code

Prompt bodies should live in template files, not large inline Python strings.

That gives us:

- easier review in diffs
- easier version bumps
- better separation between content and implementation
- simpler future prompt experimentation

Templates should be rendered with explicit context, for example:

- candidate profile summary
- raw JD text
- extracted field guidance
- evidence blocks
- gap summaries

### 5. Rendering stays explicit and typed

Stage modules should call something like:

```python
prompt = get_rendered_prompt(
    prompt_id="enrich.extraction.v1",
    context={...},
)
```

The rendering layer should:

- validate required template variables
- return the rendered text
- return prompt metadata for provenance

### 6. Effective prompt provenance must be persisted

Each run should capture the effective prompt identity used by each LLM-backed stage.

Phase 1 minimum:

- prompt ID
- prompt version
- template source path or registry key
- model name used

Recommended inspection shape:

```json
{
  "stage_id": "enrich",
  "prompt_id": "enrich.extraction.v1",
  "prompt_version": "v1",
  "template_path": "src/fitcv/prompts/templates/enrich_extraction_v1.md",
  "model": "gemini-2.5-flash"
}
```

This should be visible in settings-used snapshots and stage inspection surfaces.

### 7. Support prompt overrides without code edits

The registry should support controlled prompt overrides from config.

Recommended override layers:

1. built-in default registry definition
2. optional config-selected prompt version
3. optional runtime override for debug/manual runs

That mirrors the runtime synonym overlay pattern already introduced elsewhere in the pipeline.

Phase 1 does not need full UI editing. It only needs deterministic selection and provenance.

## Scope by Stage

### Enrich

Move the extraction prompt body and its field instructions into the prompt registry first.

Why first:

- `enrich` prompt content changes frequently
- it is currently the most sensitive prompt
- prompt iteration here directly affects canonical skill quality

### Ranking / AI score

Move `ai_score` prompt construction into the same registry next.

This gives ranking a clearer prompt contract and improves traceability for score changes.

### CV generation

Move both generation prompt variants into the registry:

- freeform/base generation prompt
- structured generation wrapper prompt

Because CV generation has the richest prompt surface, it benefits from shared provenance even if its rollout happens after `enrich`.

## Config Contract

Prompt selection should be configurable without scattering new keys through stage modules.

Recommended config shape:

```yaml
prompts:
  enrich:
    extraction:
      prompt_id: enrich.extraction.v1
  ranking:
    ai_score:
      prompt_id: ranking.ai_score.v1
  cv:
    generation:
      prompt_id: cv.generation.v1
    structured_generation:
      prompt_id: cv.generation_structured.v1
```

Existing config such as `cv.generation.prompt_version` may be migrated or aliased into this structure during rollout.

## Inspection and Debugging Contract

The inspection layer should be able to answer:

- which prompt definition a stage used
- which model it used
- whether a prompt override was active

Phase 1 recommended surfaces:

- settings-used snapshot carries effective prompt IDs
- stage artifacts carry prompt provenance for LLM-backed stages
- export/debug JSON includes prompt provenance where stage-local output already exists

Phase 1 does not require rendering full prompt text into artifacts by default. A prompt hash or prompt ID/version is enough unless a debug mode explicitly asks for more.

## Migration Strategy

### Phase 1

- introduce prompt registry package
- migrate `enrich` prompt first
- persist enrich prompt provenance

### Phase 2

- migrate `ai_score`
- persist ranking prompt provenance

### Phase 3

- migrate `cv_generation`
- unify CV prompt provenance with the existing `cv_prompt_version` concept

## Risks

- Prompt text can drift between the new templates and old inline builders during migration if both stay live too long.
- Over-centralizing too early could make simple stage-local prompt updates feel heavy.
- If the registry owns too much, stage modules may become awkward wrappers instead of clear business-logic owners.

## Mitigations

- Migrate one prompt family at a time.
- Keep response schemas in stage modules for now.
- Keep registry scope limited to prompt text, selection, metadata, and rendering.
- Add tests that compare prompt selection and required render variables by stage.

## Recommended First Implementation Slice

Implement only the `enrich` prompt registry path first:

- add prompt registry package
- move `build_extraction_prompt(...)` content into a template
- keep the current schema and enrich parsing logic unchanged
- store enrich prompt provenance in the run/debug surfaces

This gives us the biggest immediate benefit with the lowest migration risk.

## Triage

Feature type: ADD
Summary: Add a central prompt registry and template system for LLM-backed pipeline stages.
Reasoning: This is a new cross-cutting architecture layer rather than a modification owned by one existing feature contract.
Invariants:
  - Stage business logic remains stage-local.
  - Prompt identity and version must be inspectable per run.
  - Prompt behavior must remain reproducible across stages.
Dependencies:
  - `enrich`
  - `ranking`
  - `cv_generation`
  - runtime config loading
  - inspection/debug exports
Affected stages:
  - enrich
  - ranking
  - cv_generation
Affected features:
  - inspection_debugging
  - cv_system
  - pipeline_performance
Primary lens: mixed
Affected docs:
  feature_yaml: none
  feature_history: none
  feature_docs: none
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/feature_overview.md`
    - `docs/generated/features_index.yaml`
Generated refresh required: yes
Spec needed: yes
Plan needed: yes
