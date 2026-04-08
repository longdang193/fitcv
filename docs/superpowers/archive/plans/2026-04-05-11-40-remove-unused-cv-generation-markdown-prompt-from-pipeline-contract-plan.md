---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Remove the dormant markdown CV-generation prompt from the active pipeline contract so config and provenance reflect the structured-only live path."
---

# Remove Unused CV-Generation Markdown Prompt From Pipeline Contract Plan

## Summary

Implement the prompt-contract cleanup in a small, low-risk order:

- remove `cv_generation.write` from active config defaults and validation
- remove it from active prompt runtime/provenance
- refactor tests and docs to treat `structured_write` as the only live `cv_generation` prompt
- explicitly decide whether the markdown prompt asset is deleted now or retained as legacy/internal only

The goal is to make the pipeline contract match the actual structured-first `cv_generation` runtime path.

## Scope

This plan covers:

- removal of `prompts.cv_generation.write.prompt_id` from active pipeline config
- removal of active runtime provenance for `cv_generation.write`
- cleanup of config accessors and tests that still treat the markdown prompt as live
- doc updates so `cv_generation` prompt ownership matches the real runtime path
- explicit handling of the markdown prompt asset as either deleted or legacy/internal

This plan does not cover:

- redesigning `cv_generation`
- changing the structured CV schema
- changing structured generation behavior
- introducing a new markdown-generation runtime path
- making prompts admin-editable

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
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- `src/fitcv/prompts/templates/cv_generation_write_v1.md` (candidate for deletion or legacy retention)

Primary tests:

- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)
- [test_prompts.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_prompts.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)

Generated refresh required:

- yes

## Invariants

- `cv_generation` remains a structured-first runtime path.
- Structured prompt config and provenance remain active and accurate.
- Removing the markdown prompt from the active contract must not change structured generation behavior.
- If the markdown prompt asset remains on disk temporarily, it must not be presented as a live runtime dependency.

## Implementation Tasks

### Task 1: Remove Markdown Prompt From Active Runtime Config

### Goal

Make config reflect the single active `cv_generation` prompt contract.

### Code targets

- [prompts.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/config/runtime/prompts.yaml)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)

### Work

- remove `prompts.cv_generation.write.prompt_id` from canonical config
- stop applying a default active `cv_generation.write` prompt id during config load
- stop validating `cv_generation.write` as a required active runtime prompt

### Output

- active config only declares `cv_generation.structured_write`

### Task 2: Remove Markdown Prompt From Active Runtime Provenance

### Goal

Ensure prompt provenance only reports prompts the live pipeline actually uses.

### Code targets

- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- any runtime/debug consumers that read `prompts_runtime`
- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)

### Work

- remove `prompts_runtime.cv_generation.write` from active runtime metadata
- keep `prompts_runtime.cv_generation.structured_write` as the only active `cv_generation` prompt provenance block

### Output

- runtime/debug prompt provenance matches the real structured-only execution path

### Task 3: Remove Dormant Markdown-Prompt Runtime Dependencies

### Goal

Retire code paths that still treat the markdown prompt as an active pipeline contract.

### Code targets

- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/cv_generator.py)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/config.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)

### Work

- remove active runtime use of `get_cv_generation_prompt_id(...)` if it no longer serves a live path
- update helper/test expectations so structured generation is the only live prompt-driven generation contract
- keep markdown rendering from structured CV documents intact

### Output

- no live runtime dependency remains on the dormant markdown prompt contract

### Task 4: Decide Asset Disposition for `cv_generation_write_v1.md`

### Goal

Make the markdown prompt file’s status explicit instead of leaving it ambiguous.

### Code targets

- [registry.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/prompts/registry.py)
- `src/fitcv/prompts/templates/cv_generation_write_v1.md`
- [test_prompts.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_prompts.py)

### Work

Choose one of:

- **Preferred cleanup**:
  - remove the registry entry
  - delete `cv_generation_write_v1.md`
  - delete markdown-prompt-only tests

- **Safer transitional cleanup**:
  - keep the asset and registry entry temporarily
  - clearly classify it as legacy/internal only
  - ensure it no longer appears in active config/runtime/provenance

### Output

- explicit, non-ambiguous ownership status for the markdown prompt asset

### Task 5: Add Focused Regression Coverage

### Goal

Protect the contract cleanup with narrow tests around config, provenance, and live prompt usage.

### Test targets

- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_config.py)
- [test_prompts.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_prompts.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_cv_generator.py)

### Cases

- config defaults expose only `prompts.cv_generation.structured_write.prompt_id`
- `prompts_runtime.cv_generation` exposes `structured_write` and not `write`
- active `cv_generation` runtime code no longer depends on markdown prompt config
- if the markdown prompt asset remains, it is not treated as an active pipeline prompt

### Task 6: Sync Feature, Stage, and Generated Docs

### Goal

Update source-of-truth docs so they describe the real `cv_generation` prompt contract.

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

- document the structured prompt as the sole active `cv_generation` runtime prompt
- remove wording that implies the markdown prompt is a live pipeline dependency
- if the markdown prompt asset remains, document it as legacy/internal rather than active runtime contract

## Verification

Run at minimum:

```powershell
.\.venv\Scripts\python.exe -m pytest -q .worktrees\e2e-0\tests\test_config.py .worktrees\e2e-0\tests\test_prompts.py .worktrees\e2e-0\tests\test_cv_generator.py -k "prompt or structured or cv_generation"
.\.venv\Scripts\python.exe -m py_compile .worktrees\e2e-0\src\fitcv\config.py .worktrees\e2e-0\src\fitcv\cv_generator.py .worktrees\e2e-0\src\fitcv\prompts\registry.py
```

If prompt provenance is surfaced in pipeline/UI artifacts, include the narrow slice that asserts the updated runtime metadata.

## Risks

- a dormant internal helper or test may still rely on the markdown prompt asset
- deleting the file immediately may be noisier than first demoting it from the active contract
- prompt provenance snapshots may need coordinated test/doc updates

## Rollout Order

1. remove markdown prompt from active config
2. remove markdown prompt from active provenance
3. retire active runtime dependencies
4. decide asset disposition
5. add focused tests
6. sync docs and generated discovery

## Done Criteria

- `cv_generation.structured_write.v1` is the only active `cv_generation` prompt contract in config/runtime provenance
- the live `cv_generation` path behaves the same as before
- operators can no longer mistake `cv_generation.write.v1` for an active pipeline dependency
- the markdown prompt asset is either removed or clearly marked non-runtime legacy/internal
