---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Add a first-class structured CV-generation prompt contract and remove markdown-prompt rewriting from `cv_generator.py`."
---

# Structured CV-Generation Prompt Centralization Plan

## Summary

Implement the structured prompt centralization in a small, low-risk sequence:

- add a dedicated structured writer prompt id and template
- wire that prompt through config and runtime provenance
- refactor `cv_generator.py` to render the structured prompt directly
- remove string replacement against the markdown prompt
- lock the new contract with focused tests and doc updates

The goal is to make structured CV generation fully prompt-registry owned without changing the existing structured JSON schema contract.

## Scope

This plan covers:

- a new prompt id: `cv_generation.structured_write.v1`
- a new prompt template file for structured CV generation
- config/runtime support for selecting and surfacing the structured prompt
- refactoring the structured generation path in `cv_generator.py`
- focused regression coverage for config, registry, and prompt rendering
- source-of-truth and generated doc sync

This plan does not cover:

- redesigning the structured CV JSON schema
- changing markdown CV-generation behavior beyond shared-context refactoring
- making prompt ids admin-editable in this rollout
- changing repair-stage semantics

## Source-of-Truth Alignment

Affected current-state docs:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/cv_generation.yaml)

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_capabilities_index.yaml)

Primary code and config targets:

- [prompts.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/runtime/prompts.yaml)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [registry.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/registry.py)
- [renderer.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/renderer.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- `src/fitcv/prompts/templates/cv_generation_structured_write_v1.md` (new)

Primary tests:

- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)
- [test_prompts.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_prompts.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)

Generated refresh required:

- yes

## Invariants

- Markdown CV generation and structured CV generation remain distinct prompt contracts.
- Structured generation keeps the current JSON schema contract unless a deliberate version bump is introduced.
- Prompt text lives in prompt templates once the prompt-registry route exists.
- Config continues to select prompt ids rather than embedding prompt prose in code.

## Implementation Tasks

### Task 1: Add Structured Prompt Registry Entry

### Goal

Create a first-class structured CV-generation prompt contract in the registry.

### Code targets

- [registry.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/registry.py)
- `src/fitcv/prompts/templates/cv_generation_structured_write_v1.md`
- [test_prompts.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_prompts.py)

### Work

- add prompt id `cv_generation.structured_write.v1`
- create a dedicated structured prompt template file
- keep JSON-output instructions and structured schema ownership inside that template path
- register prompt metadata consistently with existing prompt entries

### Output

- registry-backed structured writer prompt ownership

### Task 2: Extend Prompt Config and Runtime Accessors

### Goal

Make the structured writer prompt selectable and visible through config/runtime metadata.

### Code targets

- [prompts.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/runtime/prompts.yaml)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)

### Work

- add `prompts.cv_generation.structured_write.prompt_id`
- add default constant and default application in config loading
- validate that the configured structured prompt id exists
- add accessor such as `get_cv_generation_structured_prompt_id(config)`
- extend prompt runtime/provenance output to include the structured writer prompt

### Output

- config-owned prompt selection for structured CV generation

### Task 3: Refactor Structured Prompt Rendering in `cv_generator.py`

### Goal

Render the structured prompt directly instead of rewriting the markdown prompt text in Python.

### Code targets

- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [renderer.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/renderer.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)

### Work

- extract a shared prompt-context builder for markdown and structured generation
- keep markdown generation rendering `cv_generation.write.v1`
- switch structured generation to render `cv_generation.structured_write.v1`
- pass shared context plus JSON-specific fields explicitly
- remove `.replace(...)` prompt surgery against rendered markdown prompt text

### Output

- direct structured prompt rendering with independent versioning

### Task 4: Preserve Structured Schema and Debug Provenance

### Goal

Keep behavior stable while improving prompt provenance visibility for debugging.

### Code targets

- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- any prompt runtime/debug surfaces that already expose prompt metadata
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)

### Work

- preserve the existing structured schema contract text/shape
- ensure structured generation debug metadata can identify the structured prompt id/version/template path
- keep markdown and structured prompt provenance distinct where surfaced

### Output

- stable structured-output contract plus clearer debugging visibility

### Task 5: Add Focused Regression Coverage

### Goal

Protect the prompt split with narrow tests around loading, rendering, and behavior parity.

### Test targets

- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)
- [test_prompts.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_prompts.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)

### Cases

- config defaults include `prompts.cv_generation.structured_write.prompt_id`
- prompt registry resolves `cv_generation.structured_write.v1`
- structured prompt rendering includes JSON-specific output instructions
- structured prompt rendering does not depend on markdown-only output instructions
- `build_structured_generation_prompt()` no longer uses string replacement against the markdown prompt

### Task 6: Sync Feature, Stage, and Generated Docs

### Goal

Update source-of-truth docs to reflect complete prompt centralization for the structured generation path.

### Doc targets

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/history.md)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/cv_generation.yaml)
- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/FitCV-pipeline.md)
- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/generated/feature_capabilities_index.yaml)

### Work

- document the new structured prompt contract and config key
- document distinct markdown vs structured prompt provenance in `cv_generation`
- refresh generated discovery docs after source-of-truth updates

## Verification

Run at minimum:

```powershell
.\.venv\Scripts\python.exe -m pytest -q .worktrees\e2e-0\tests\test_config.py .worktrees\e2e-0\tests\test_prompts.py .worktrees\e2e-0\tests\test_cv_generator.py -k "structured or prompt"
.\.venv\Scripts\python.exe -m py_compile .worktrees\e2e-0\src\fitcv\config.py .worktrees\e2e-0\src\fitcv\cv_generator.py .worktrees\e2e-0\src\fitcv\prompts\registry.py .worktrees\e2e-0\src\fitcv\prompts\renderer.py
```

If prompt provenance is surfaced through pipeline artifacts in this rollout, include the narrow pipeline/UI slice that covers that output.

## Risks

- structured generation may change wording-sensitive behavior if the new prompt does not preserve the current schema instructions closely enough
- config fixtures that only know about `cv_generation.write` will need compatibility handling or test updates
- prompt provenance snapshots may need small schema adjustments where debug/runtime metadata is asserted

## Rollout Order

1. add registry entry and template
2. add config/runtime support
3. refactor `cv_generator.py`
4. add focused tests
5. sync docs and generated discovery

## Done Criteria

- structured CV generation has its own prompt id and template file
- `cv_generator.py` no longer rewrites rendered markdown prompt text for structured generation
- config/runtime metadata exposes the structured prompt contract
- structured JSON schema contract remains unchanged
- focused tests cover config loading, registry resolution, and direct structured prompt rendering
