---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Implement hybrid analysis-grounded validation in `cv_generation` by combining deterministic selected-evidence checks for hard facts with bounded semantic validation for softer responsibility/domain claims."
---

# CV Generation Hybrid Analysis-Grounded Validation Plan

## Scope

Implement the validation upgrade defined in [2026-04-03-19-10-cv-generation-hybrid-analysis-grounding-validation-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/superpowers/specs/2026-04-03-19-10-cv-generation-hybrid-analysis-grounding-validation-spec.md).

This rollout stays intentionally focused:

- keep `cv_analysis` as the sole owner of evidence retrieval, final evidence selection, and fit-gate decisions
- keep `cv_generation` bounded and avoid rerunning retrieval
- add deterministic selected-evidence grounding for hard facts
- add bounded semantic validation only for softer responsibility/domain/role claims
- preserve backward compatibility with older `cv_analysis` records
- expose validation provenance clearly in `cv_generation` debug and artifact surfaces

## Source-of-Truth Alignment

Affected current-state docs:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/inspection_debugging/inspection_debugging.yaml)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/stages/cv_analysis.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/stages/cv_generation.yaml)

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/inspection_debugging/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/generated/feature_capabilities_index.yaml)

Primary code and tests:

- [validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/validator.py)
- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/pipeline.py)
- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/cv_generator.py)
- [tracker.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/tracker.py)
- [test_validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_validator.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_pipeline.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_cv_generator.py)

Generated refresh required:

- yes

## Invariants

- `cv_analysis` remains the sole owner of evidence retrieval, merge/dedupe, final evidence selection, and fit-gate decisions.
- `cv_generation` validation must stay bounded and must not silently rerun evidence retrieval.
- Hard facts must be validated deterministically against the selected evidence bundle whenever possible.
- Semantic validation is limited to soft claims such as responsibility alignment, domain familiarity, and role-positioning language.
- Existing persisted `cv_analysis` records without richer evidence metadata remain consumable through a compatibility path.

## Implementation Tasks

### Task 1: Define the Validator Input Contract for Analysis-Grounded Checks

Make the validator consume one explicit analysis-grounding payload rather than inferring support from the full profile alone.

Primary targets:

- [validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/validator.py)
- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/pipeline.py)

Changes:

- define a bounded validation input contract that includes:
  - selected evidence payload
  - `evidence_used`
  - `evidence_selection_summary`
  - compact `analysis_input_summary`
- add helper normalization so validator code sees one consistent shape
- keep graceful fallback when older `cv_analysis` records only expose flatter evidence data

Acceptance criteria:

- validator no longer depends only on the full candidate profile for support checks
- selected-evidence grounding inputs are explicit in code
- older records still reach a compatibility path instead of breaking

### Task 2: Implement Deterministic Selected-Evidence Grounding for Hard Facts

Add deterministic analysis-grounded checks for facts that should not require semantic interpretation.

Primary targets:

- [validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/validator.py)
- [test_validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_validator.py)

Changes:

- derive allowed facts from selected evidence, including:
  - employers
  - project names
  - canonical skills
  - selected evidence identities
- add deterministic selected-evidence checks for:
  - employer claims
  - project claims
  - explicit skill claims
- distinguish:
  - selected-evidence grounded
  - profile-grounded but not selected-evidence grounded
  - unsupported entirely

Acceptance criteria:

- a hard fact can fail validation even if it is true somewhere in the candidate profile when it is not supported by the selected evidence bundle
- deterministic checks remain explainable and bounded
- output clearly reports which selected-evidence grounding rule failed

### Task 3: Add Bounded Semantic Validation for Soft Claims

Introduce a second, narrow validation path for softer claims where deterministic lexical matching is too brittle.

Primary targets:

- [validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/validator.py)
- supporting runtime helper in [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/pipeline.py) if needed
- [test_validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_validator.py)

Changes:

- support a semantic validation path for:
  - responsibility alignment claims
  - domain familiarity claims
  - role-positioning phrases
- deterministic alias/theme matching should run first
- if deterministic matching is insufficient, run bounded semantic comparison against:
  - selected evidence bullet/highlight text
  - selected `responsibility_themes`
  - selected `domain_tags`
  - selected role-family context
- keep the semantic validator narrow:
  - selected evidence only
  - compact structured outputs
  - no free-form whole-CV critique

Acceptance criteria:

- semantically supported but lexically different soft claims can pass
- unsupported soft claims fail when both deterministic and semantic checks fail
- semantic validation stays bounded to selected evidence and does not inspect the whole profile as a fallback oracle

### Task 4: Surface Hybrid Validation Provenance in Debug and Artifacts

Make accepted and rejected `cv_generation` records explain whether support came from deterministic or semantic validation.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/pipeline.py)
- [tracker.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/tracker.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_pipeline.py)

Changes:

- extend validation result snapshots and generation debug records with compact fields such as:
  - deterministic grounding violations
  - semantic grounding violations
  - support source summary
  - matched evidence IDs / themes when available
- evaluate whether accepted CV persistence should include a compact validation provenance payload or hash
- keep skip outcomes separate from generation failures

Acceptance criteria:

- final-stage artifacts can explain why a CV was accepted or rejected under the hybrid validator
- debugging can distinguish deterministic failures from semantic-support failures
- accepted outputs remain traceable to the selected evidence bundle

### Task 5: Keep Prompt and Validator Contracts Aligned

Ensure `cv_generation` prompt usage and validation usage are aligned rather than pulling in incompatible directions.

Primary targets:

- [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/cv_generator.py)
- [validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/validator.py)
- [test_cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_cv_generator.py)

Changes:

- verify that prompt guidance still encourages the same evidence-purpose distinctions that validation later expects
- ensure prompt-side evidence channel semantics are compatible with validator-side soft-claim categories
- avoid validation rules that contradict prompt instructions or require evidence semantics the prompt never uses

Acceptance criteria:

- prompt and validator use compatible evidence-purpose categories
- generation is not pushed toward wording patterns the validator will systematically reject

### Task 6: Preserve Backward Compatibility With Older `cv_analysis` Records

Keep the rollout safe for old runs and fixtures with flatter evidence contracts.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/pipeline.py)
- [validator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/validator.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/tests/test_pipeline.py)

Changes:

- add compatibility fallbacks for missing:
  - `matched_channels`
  - `selection_reasons`
  - `responsibility_themes`
  - `domain_tags`
  - richer `analysis_input_summary`
- preserve deterministic profile-grounded behavior as a bounded fallback when selected-evidence metadata is too thin
- make fallback behavior explicit in code and tests

Acceptance criteria:

- older `cv_analysis` records still validate successfully through a compatibility path
- new richer records automatically take the hybrid path
- compatibility behavior is explicit rather than accidental

### Task 7: Sync Feature, Stage, History, and Generated Docs

Update source-of-truth docs once runtime behavior is in place.

Targets:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/inspection_debugging/inspection_debugging.yaml)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/stages/cv_analysis.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/stages/cv_generation.yaml)
- history files listed above
- generated outputs listed above

Acceptance criteria:

- source-of-truth docs describe the hybrid validation model accurately
- debugging surfaces and validation provenance are documented consistently
- generated discovery reflects the updated capability set

## Verification Plan

Run targeted verification after implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_validator.py tests\test_pipeline.py tests\test_cv_generator.py -k "cv_generation or cv_analysis or validation or evidence"
```

Also run a lightweight syntax check on touched modules:

```powershell
python -m py_compile src\fitcv\validator.py src\fitcv\pipeline.py src\fitcv\cv_generator.py tests\test_validator.py tests\test_pipeline.py tests\test_cv_generator.py
```

## Task Status

Status: completed

- [x] Task 1: Define the validator input contract for analysis-grounded checks
- [x] Task 2: Implement deterministic selected-evidence grounding for hard facts
- [x] Task 3: Add bounded semantic validation for soft claims
- [x] Task 4: Surface hybrid validation provenance in debug and artifacts
- [x] Task 5: Keep prompt and validator contracts aligned
- [x] Task 6: Preserve backward compatibility with older `cv_analysis` records
- [x] Task 7: Sync feature, stage, history, and generated docs
