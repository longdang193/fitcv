---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Centralize structured CV-generation prompt ownership so `cv_generator.py` stops rewriting markdown prompts in Python."
invariants:
  - "Markdown CV generation and structured CV generation must remain distinct prompt contracts."
  - "Structured generation must keep producing the same JSON schema contract unless a deliberate schema-version bump is made."
  - "Prompt text must live in the prompt registry/templates path once a prompt-registry route exists."
  - "Config should continue to provide prompt-id selection rather than embedding prompt prose in code."
---

# Structured CV-Generation Prompt Centralization Spec

## Triage

Feature type: MODIFY  
Summary: Add a first-class structured CV-generation prompt so the structured-output path stops mutating the markdown writer prompt with string replacement in Python.  
Reasoning: The project already centralizes primary prompt content for `enrich`, `ranking`, and markdown `cv_generation`, but structured CV generation still depends on `build_structured_generation_prompt()` rewriting the markdown prompt text in code. That is a managed `cv_system` change because it alters prompt ownership and provenance for an existing final-stage behavior without changing the broader pipeline contract.  
Invariants:
- Structured-output generation must remain bounded to the existing CV JSON schema contract.
- Prompt provenance must become more explicit, not less.
- The markdown writer prompt and structured writer prompt must be independently versionable.
- Config-driven prompt selection must remain the control surface.
Dependencies:
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [registry.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/registry.py)
- [renderer.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/renderer.py)
- [prompts.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/runtime/prompts.yaml)
Affected stages:
- `cv_generation`
Affected features:
- `cv_system`
- `inspection_debugging`
Primary lens: mixed
Affected docs:
  feature_yaml:
  - [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
  - [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
  feature_history:
  - [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)
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
Risk level: low

## Why

Prompt centralization is almost complete, but one important gap remains:

- `enrich` uses a registry-backed prompt template
- `ranking` uses a registry-backed prompt template
- markdown `cv_generation` uses a registry-backed prompt template
- structured `cv_generation` still builds its prompt by:
  - rendering the markdown writer prompt
  - then replacing key instruction strings in Python
  - then appending an inline JSON schema block

That last part means the structured-output path still has hidden prompt ownership inside [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py), even though the project has already adopted a central prompt registry.

## Problem Statement

`build_structured_generation_prompt()` currently depends on string replacement against the rendered markdown writer prompt:

- replace the top instruction from markdown to JSON output
- rename the output-template section to a rendering reference
- replace the markdown-only output instruction with a JSON-only instruction
- inject a structured schema block inline

This creates several problems:

1. **Hidden prompt drift**
- if the markdown template wording changes, the structured path may silently stop matching the expected replacement targets

2. **Weak provenance**
- artifacts and runtime config know about `cv_generation.write.v1`
- but there is no separate structured-writer prompt contract to inspect or version independently

3. **Coupled evolution**
- improving markdown instructions can accidentally affect structured generation
- improving structured generation requires knowing the markdown prompt’s exact wording

4. **Incomplete centralization**
- prompt ownership is still split between:
  - prompt templates on disk
  - prompt surgery in Python

## Goals

1. Give structured CV generation a first-class prompt ID and template file.
2. Stop mutating prompt text with `.replace(...)` in `cv_generator.py`.
3. Keep markdown and structured generation independently versionable.
4. Preserve the current structured JSON schema contract and runtime behavior.
5. Make structured-prompt provenance available through the same config/registry path as other major prompts.

## Non-Goals

- redesigning the structured CV schema
- changing the final JSON output shape
- changing repair logic semantics
- making prompt text admin-editable in this rollout
- changing markdown CV-generation behavior beyond shared-context refactoring

## Current State

Today:

- [prompts.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/runtime/prompts.yaml) configures:
  - `prompts.enrich.extraction.prompt_id`
  - `prompts.ranking.ai_score.prompt_id`
  - `prompts.cv_generation.write.prompt_id`
- [registry.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/registry.py) registers:
  - `enrich.extraction.v1`
  - `ranking.ai_score.v1`
  - `cv_generation.write.v1`
- [cv_generation_write_v1.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/templates/cv_generation_write_v1.md) is the markdown writer template

But structured generation still does not have:

- its own prompt ID
- its own template file
- its own config key
- its own runtime provenance block

## Proposed Design

Introduce a distinct structured writer prompt contract.

### New prompt ID

Add:

- `cv_generation.structured_write.v1`

### New prompt template

Add a new template file under:

- `src/fitcv/prompts/templates/cv_generation_structured_write_v1.md`

This template should explicitly contain:

- JSON-output instruction
- rendering-reference template section
- structured schema section
- no markdown-only instructions

### New config key

Extend [prompts.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/runtime/prompts.yaml):

```yaml
prompts:
  cv_generation:
    write:
      prompt_id: cv_generation.write.v1
    structured_write:
      prompt_id: cv_generation.structured_write.v1
```

### New config/runtime accessors

Add structured-writer support in [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py):

- default prompt id constant
- default application
- validation
- runtime prompt provenance
- accessor such as:
  - `get_cv_generation_structured_prompt_id(config)`

### New rendering flow

Refactor `cv_generator.py` so:

- one helper builds the shared prompt context:
  - title
  - required skills
  - selected evidence
  - evidence-usage guidance
  - analysis summary
  - constraints
  - section-specific evidence
  - filtered output template
- markdown generation renders:
  - `cv_generation.write.v1`
- structured generation renders:
  - `cv_generation.structured_write.v1`

The structured path should pass:

- shared prompt context
- `structured_schema`
- JSON-specific `output_instruction`

The key rule is:

- no string replacement of rendered prompt text

## Example

### Current structured path

Code effectively does:

1. render `cv_generation.write.v1`
2. replace:
   - `"Generate a tailored CV in markdown format."`
   - `"## Output Template"`
   - `"Write only the completed CV markdown..."`
3. append structured schema text

This means a harmless markdown prompt edit like:

```text
You are a professional CV writer. Produce a tailored CV in markdown.
```

could break structured generation because the replacement target no longer matches exactly.

### Proposed path

Markdown:

- render `cv_generation.write.v1`

Structured:

- render `cv_generation.structured_write.v1`

Both use the same shared context builder, but each prompt template owns its own output instructions directly.

That means:

- markdown prompt wording can evolve safely
- structured prompt wording can evolve safely
- no fragile cross-prompt string surgery is needed

## Artifact And Debugging Implications

`cv_generation` runtime/debug output should be able to distinguish:

- markdown writer prompt provenance
- structured writer prompt provenance

At minimum, structured generation should expose:

- structured prompt id
- structured prompt version
- structured prompt template path

This may appear in:

- `prompts_runtime`
- debug snapshots
- run artifacts if prompt provenance is already surfaced there

## Migration Strategy

### Phase 1

Add the new structured prompt contract while preserving the existing markdown contract.

### Phase 2

Switch `build_structured_generation_prompt()` to render the structured template directly.

### Phase 3

Remove the old `.replace(...)` prompt-rewrite logic.

### Phase 4

Update tests to assert:

- config defaults include the structured writer prompt id
- prompt registry resolves the new prompt id
- structured generation uses the dedicated structured prompt template

## Validation

Add or update tests to prove:

1. `load_config()` adds:
- `prompts.cv_generation.structured_write.prompt_id`

2. `prompts_runtime` includes:
- `cv_generation.structured_write`

3. prompt registry resolves:
- `cv_generation.structured_write.v1`

4. rendered structured prompt includes:
- JSON-specific top instruction
- structured schema section
- no markdown-only output instruction

5. `build_structured_generation_prompt()` no longer depends on string replacement of markdown prompt text

## Risks

- config validation must remain backward-compatible for older config fixtures
- tests that only know about `cv_generation.write` will need updates
- if prompt provenance is surfaced in artifacts, those snapshots may need small schema additions

## Rollback Strategy

Rollback trigger:

- structured generation output changes unexpectedly
- prompt loading fails for existing runs/tests

Rollback method:

- keep the new prompt template file
- revert the runtime switch to direct structured rendering
- temporarily fall back to the current string-replacement path

## Acceptance Criteria

1. Structured CV generation has its own prompt ID and template.
2. `cv_generator.py` no longer rewrites markdown prompt text for structured generation.
3. Config and prompt runtime metadata include the structured writer prompt.
4. Markdown and structured generation prompts can evolve independently.
5. Structured generation keeps the existing JSON schema contract unchanged.
