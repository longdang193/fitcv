---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Implement analysis-aware evidence consumption in `cv_generation`, including prompt usage, validation grounding, debug provenance, and bounded upstream-analysis context in generation artifacts."
---

# CV Generation Analysis-Aware Evidence Consumption Implementation Plan

## Scope

Implement the `cv_generation` contract upgrade defined in [2026-04-03-18-20-cv-generation-analysis-aware-evidence-consumption-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/superpowers/specs/2026-04-03-18-20-cv-generation-analysis-aware-evidence-consumption-spec.md).

This rollout stays intentionally focused:

- keep `cv_analysis` as the sole owner of evidence retrieval, final evidence selection, and fit-gate decisions
- make `cv_generation` consume richer analysis-selected evidence semantics when available
- use evidence purpose to improve prompt construction and section-specific writing behavior
- preserve stronger generation-time grounding and provenance
- include bounded upstream `cv_analysis` inputs and evidence context in `cv_generation` artifacts for easier debugging
- keep backward compatibility with older `cv_analysis` records that only provide a flatter evidence contract

## Source-of-Truth Alignment

Affected current-state docs:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/inspection_debugging/inspection_debugging.yaml)
- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/trigger_run_management/trigger_run_management.yaml)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/stages/cv_analysis.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/stages/cv_generation.yaml)

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/inspection_debugging/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/trigger_run_management/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/generated/feature_capabilities_index.yaml)

Primary code and tests:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/pipeline.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/cv_generator.py)
- [validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/validator.py)
- [tracker.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/tracker.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_pipeline.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_cv_generator.py)
- [test_validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_validator.py)

Generated refresh required:

- yes

## Invariants

- `cv_analysis` remains the sole owner of evidence retrieval, merge/dedupe, final evidence selection, and fit-gate decisions.
- `cv_generation` consumes persisted `cv_analysis` outputs and does not silently recompute retrieval by default.
- Fit-gate skips remain analysis outcomes, not generation failures.
- CV claims remain grounded in the selected evidence bundle.
- `cv_generation` stage artifacts include bounded `cv_analysis`-derived inputs and selected evidence context for easier debugging.
- Existing persisted `cv_analysis` records without richer provenance remain consumable through a compatibility path.

## Implementation Tasks

### Task 1: Define the Analysis-Aware Generation Input Contract

Make the `cv_generation` stage consume a stable, explicit subset of the `cv_analysis` record schema rather than loosely reading ad hoc fields.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/pipeline.py)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/stages/cv_generation.yaml)

Changes:

- define the minimum generation-ready contract, including:
  - `job_snapshot`
  - `fit_classification`
  - `gap_summary`
  - `evidence_payload`
  - `evidence_used`
  - `evidence_selection_summary`
- add small helper normalization if needed so `cv_generation` consumes one consistent shape
- keep graceful fallback for older records that only include the flatter evidence contract

Acceptance criteria:

- `cv_generation` no longer relies on implicit field discovery across analysis records
- missing richer fields degrade gracefully rather than breaking generation
- the stage boundary is explicit and readable in code

### Task 2: Make Prompt Construction Use Evidence Intent

Update prompt-building so `cv_generation` uses analysis-selected evidence purpose, not only flat evidence order.

Primary targets:

- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/cv_generator.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_cv_generator.py)

Changes:

- present selected evidence with bounded purpose metadata such as:
  - `matched_channels`
  - `selection_reasons`
- update prompt structure so it can distinguish evidence use for:
  - summary / positioning
  - experience bullets
  - projects
  - domain familiarity statements
- keep the prompt bounded and backward-compatible when richer evidence tags are absent

Acceptance criteria:

- prompt construction explicitly reflects evidence purpose when available
- richer evidence semantics improve guidance without requiring prompt-time evidence recomputation
- legacy flat-evidence records still build a valid prompt

### Task 3: Tighten Analysis-Aware Grounding and Validation

Use the richer evidence bundle to improve grounding checks without turning validation into a second full analysis stage.

Primary targets:

- [validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/validator.py)
- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/pipeline.py)
- [test_validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_validator.py)

Changes:

- thread the bounded analysis-selected evidence context into validation where needed
- strengthen grounded-only checks so substantive claims are validated against the selected evidence bundle
- add bounded rules for domain or responsibility claims when analysis evidence explicitly supports those dimensions
- avoid making validation semantically heavy or unbounded in phase 1

Acceptance criteria:

- validation can use richer evidence context when present
- no new requirement to rerun evidence retrieval inside `cv_generation`
- validation remains bounded and deterministic enough for existing runtime expectations

### Task 4: Preserve Better Generation-Time Provenance

Expand generation-time debug and persistence surfaces so they capture what `cv_generation` actually saw from `cv_analysis`.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/pipeline.py)
- [tracker.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/tracker.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_pipeline.py)

Changes:

- add bounded `evidence_selection_summary` into generation debug records
- add a compact evidence-purpose summary when richer semantics are present
- evaluate whether accepted CV persistence should carry a compact analysis-bundle provenance field or hash
- keep fit-gate skips clearly separate from generation failures

Acceptance criteria:

- generation debug records preserve enough analysis-aware provenance to explain outputs and failures
- accepted outputs remain traceable to the selected evidence bundle
- expected skips are still represented as non-attempted generation outcomes

### Task 5: Include Upstream Analysis Inputs in `cv_generation` Artifacts

Make the `cv_generation` stage artifact self-sufficient for debugging by including the bounded upstream analysis context it consumed.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/pipeline.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_pipeline.py)

Changes:

- extend generation input/output/changed-state artifact samples to include bounded fields such as:
  - `job_url`
  - `job_title`
  - `fit_classification`
  - `ranking_fit_label`
  - `evidence_selection_summary`
  - bounded `evidence_used`
  - bounded `gap_summary`
- keep artifacts bounded and reviewer-friendly rather than duplicating raw checkpoint payloads

Acceptance criteria:

- reviewers can understand what `cv_generation` received from `cv_analysis` without opening the previous stage artifact first
- failed and accepted rows show bounded upstream analysis context
- artifact size and readability remain acceptable

### Task 6: Keep Backward Compatibility With Older `cv_analysis` Records

Ensure the rollout works for runs or test fixtures that do not yet contain richer evidence semantics.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/pipeline.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/cv_generator.py)
- relevant tests in [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_pipeline.py)

Changes:

- add compatibility fallbacks for missing:
  - `matched_channels`
  - `selection_reasons`
  - `evidence_selection_summary`
- preserve old flat-evidence behavior as a bounded fallback path
- keep older fixtures and staged resumes working

Acceptance criteria:

- older `cv_analysis` records still generate successfully
- new richer records take the improved path automatically
- compatibility logic is explicit rather than accidental

### Task 7: Sync Feature, Stage, History, and Generated Docs

Update the source-of-truth docs once runtime behavior is in place.

Targets:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/inspection_debugging/inspection_debugging.yaml)
- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/trigger_run_management/trigger_run_management.yaml)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/stages/cv_analysis.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/stages/cv_generation.yaml)
- history files listed above
- generated outputs listed above

Acceptance criteria:

- source-of-truth docs match the analysis-aware `cv_generation` behavior
- artifact/debug expectations are documented consistently
- generated discovery reflects the updated capability set

## Verification Plan

Run targeted verification after implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_cv_generator.py tests\test_validator.py tests\test_pipeline.py -k "cv_generation or cv_analysis or evidence"
```

Also run a lightweight syntax check on touched Python modules:

```powershell
python -m py_compile src\fitcv\cv_generator.py src\fitcv\pipeline.py src\fitcv\validator.py tests\test_cv_generator.py tests\test_validator.py tests\test_pipeline.py
```

## Task Status

Status: completed

- [x] Task 1: Define the analysis-aware generation input contract
- [x] Task 2: Make prompt construction use evidence intent
- [x] Task 3: Tighten analysis-aware grounding and validation
- [x] Task 4: Preserve better generation-time provenance
- [x] Task 5: Include upstream analysis inputs in `cv_generation` artifacts
- [x] Task 6: Keep backward compatibility with older `cv_analysis` records
- [x] Task 7: Sync feature, stage, history, and generated docs
- [x] Run targeted verification
- [x] Update plan status after implementation

- [ ] Task 1: Define the analysis-aware generation input contract
- [ ] Task 2: Make prompt construction use evidence intent
- [ ] Task 3: Tighten analysis-aware grounding and validation
- [ ] Task 4: Preserve better generation-time provenance
- [ ] Task 5: Include upstream analysis inputs in `cv_generation` artifacts
- [ ] Task 6: Keep backward compatibility with older `cv_analysis` records
- [ ] Task 7: Sync feature, stage, history, and generated docs
