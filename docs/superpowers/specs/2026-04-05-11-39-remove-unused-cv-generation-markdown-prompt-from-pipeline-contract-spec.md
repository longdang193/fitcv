---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Remove the unused markdown CV-generation prompt from the active pipeline contract so runtime config and prompt provenance reflect the actual structured-only generation path."
invariants:
  - "The active `cv_generation` runtime path must continue to use the structured JSON generation contract."
  - "Removing the markdown prompt from the active pipeline contract must not change the structured CV schema contract."
  - "Prompt provenance and config should describe prompts that are actually used by the live pipeline."
  - "If markdown prompt assets remain on disk, they must be clearly classified as non-runtime legacy/internal assets rather than active pipeline configuration."
---

# Remove Unused CV-Generation Markdown Prompt From Pipeline Contract Spec

## Triage

Feature type: MODIFY  
Summary: Remove `cv_generation.write.v1` from the active pipeline contract now that the live `cv_generation` path only uses `cv_generation.structured_write.v1`.  
Reasoning: The current `e2e-0` runtime path generates structured CV JSON first, then renders markdown from that structured document. The markdown writer prompt is no longer used by the live pipeline, but it still appears in prompt config and runtime provenance as if it were an active contract. That creates configuration noise and misleading observability inside the managed `cv_system` feature.  
Invariants:
- The live `cv_generation` runtime path remains structured-first.
- Structured generation keeps its current schema and grounding behavior.
- Prompt config/runtime metadata should only describe active pipeline prompts unless an asset is explicitly marked legacy/internal.
- Debugging surfaces should become clearer, not less detailed.
Dependencies:
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [registry.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/registry.py)
- [prompts.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/runtime/prompts.yaml)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)
- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)
- [test_prompts.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_prompts.py)
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

The active `cv_generation` runtime path now works like this:

1. build a structured-generation prompt
2. generate structured CV JSON
3. validate/normalize the structured CV document
4. render markdown from the structured document

That means the live pipeline uses:

- `cv_generation.structured_write.v1`

and does **not** use:

- `cv_generation.write.v1`

as part of the active final-stage runtime path.

But the current config/runtime contract still suggests both are active pipeline prompts. That creates a mismatch between:

- what operators see in config
- what prompt provenance reports
- what the pipeline really executes

## Problem Statement

`cv_generation.write.v1` is now effectively dormant in the live pipeline:

- active generation uses `build_structured_generation_prompt()`
- `generate_cv()` calls `generate_structured_cv()`
- markdown is rendered from the structured CV document after generation

So the markdown writer prompt is no longer an active runtime dependency for final-stage generation.

Keeping it in the active pipeline contract creates several issues:

1. **Misleading config**
- `prompts.yaml` implies `cv_generation.write` is an active stage-owned runtime prompt

2. **Misleading provenance**
- `prompts_runtime` can imply two live `cv_generation` prompt contracts when only one is actually used

3. **Operator confusion**
- reviewers may think markdown prompt edits affect the live path when they do not

4. **Contract drift**
- config and artifacts stop reflecting the real execution boundary

## Goals

1. Remove the unused markdown prompt from the active pipeline contract.
2. Make `prompts.yaml` and prompt runtime metadata reflect the structured-only live path.
3. Keep the structured generation path unchanged in behavior.
4. Clarify whether the markdown prompt asset remains as legacy/internal or should be deleted.

## Non-Goals

- redesigning `cv_generation`
- changing the structured JSON schema
- changing markdown rendering from structured CV documents
- making prompt ids admin-editable
- introducing a new markdown-generation runtime path

## Current State

Today:

- [prompts.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/runtime/prompts.yaml) includes:
  - `prompts.cv_generation.write.prompt_id`
  - `prompts.cv_generation.structured_write.prompt_id`
- [registry.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/registry.py) registers both prompt ids
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py) builds prompt runtime metadata for both

But active generation in [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py):

- uses `get_cv_generation_structured_prompt_id(...)`
- does not use `get_cv_generation_prompt_id(...)` in the live generation path

So the markdown prompt is not part of the active final-stage runtime contract.

## Proposed Design

Treat `cv_generation.structured_write.v1` as the only active `cv_generation` prompt contract.

### Active pipeline contract

Keep in active runtime config/provenance:

- `prompts.cv_generation.structured_write.prompt_id`

Remove from active runtime config/provenance:

- `prompts.cv_generation.write.prompt_id`

### Runtime/config behavior

Update config/runtime support so:

- `load_config()` does not add a default active `cv_generation.write` prompt id
- `prompts_runtime.cv_generation` surfaces only the structured writer prompt as the active runtime prompt
- config validation requires only the structured writer prompt for the active `cv_generation` contract

### Code behavior

Remove active runtime dependency on:

- `get_cv_generation_prompt_id(...)`
- any prompt provenance or validation paths that treat `cv_generation.write` as active

### Markdown prompt asset disposition

Use one of these two options explicitly:

#### Recommended option

Remove the file and registry entry entirely if no live or supported internal consumer remains:

- delete `cv_generation_write_v1.md`
- delete the registry entry
- delete markdown-prompt-specific tests

#### Safer transition option

Keep the file temporarily, but clearly classify it as:

- legacy/internal only
- not part of the active pipeline contract

If retained temporarily, it must no longer appear in:

- active prompt config
- prompt runtime metadata
- stage contract descriptions as an active runtime prompt

## Recommendation

Use the safer transition option for one cleanup cycle:

1. remove `cv_generation.write` from active config/runtime/provenance immediately
2. keep the file and registry entry only if tests or tooling still need a short migration window
3. delete the dormant asset in a follow-up cleanup once no supported consumer remains

This keeps the pipeline contract accurate now without forcing a risky hard delete in the same change.

## Example

### Current misleading contract

`prompts.yaml` implies:

```yaml
prompts:
  cv_generation:
    write:
      prompt_id: cv_generation.write.v1
    structured_write:
      prompt_id: cv_generation.structured_write.v1
```

An operator may reasonably infer that both are part of the active final-stage path.

### Proposed active contract

```yaml
prompts:
  cv_generation:
    structured_write:
      prompt_id: cv_generation.structured_write.v1
```

That makes config match the real runtime path:

- structured generation prompt is active
- markdown rendering is a post-generation rendering step, not a prompt-driven generation contract

## Artifact And Debugging Implications

After the cleanup:

- `prompts_runtime.cv_generation` should expose only the active structured prompt contract
- run artifacts and debug surfaces should no longer suggest a dormant markdown prompt is live
- prompt provenance becomes simpler and more accurate

If the markdown prompt asset remains on disk temporarily, it should not appear in active runtime provenance.

## Migration Strategy

### Phase 1

Remove `cv_generation.write` from:

- active config defaults
- active config validation
- prompt runtime metadata

### Phase 2

Refactor tests/docs to treat structured prompt as the sole active `cv_generation` runtime prompt.

### Phase 3

Decide whether the markdown prompt asset:

- is fully dead and should be deleted
- or remains as a temporary legacy/internal artifact

## Validation

Add or update tests to prove:

1. `load_config()` only adds:
- `prompts.cv_generation.structured_write.prompt_id`

2. `prompts_runtime.cv_generation` exposes:
- `structured_write`
- and not `write`

3. active `cv_generation` runtime code no longer depends on:
- `get_cv_generation_prompt_id(...)`

4. prompt provenance for `cv_generation` matches the live structured-only runtime path

## Risks

- some tests may still assume both prompt ids are active
- there may be a dormant internal helper path still referencing the markdown prompt
- deleting the prompt file too early could break local/debug-only code that has not been formally retired

## Rollback Strategy

Rollback trigger:

- hidden internal consumers still require `cv_generation.write.v1`
- prompt/runtime config tests fail for legitimate supported use cases

Rollback method:

- restore `cv_generation.write` to active config/runtime temporarily
- keep the structured-only cleanup scoped until all consumers are confirmed

## Acceptance Criteria

1. `cv_generation.structured_write.v1` is the only active `cv_generation` prompt contract in config/runtime provenance.
2. The live `cv_generation` path behaves the same as before.
3. Operators can no longer mistake the dormant markdown prompt for an active runtime dependency.
4. The markdown prompt asset is either removed or explicitly demoted to non-runtime legacy/internal status.
