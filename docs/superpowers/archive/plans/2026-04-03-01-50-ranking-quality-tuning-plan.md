---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Implement ranking-quality improvements by tightening the reranker rubric, upgrading title relevance to semantic role alignment, introducing weighted preference scoring, and exposing clearer contribution plus calibration surfaces."
---

# Ranking Quality Tuning Implementation Plan

## Scope

Implement the ranking-quality changes defined in [2026-04-03-01-35-ranking-quality-tuning-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/superpowers/specs/2026-04-03-01-35-ranking-quality-tuning-spec.md).

This plan keeps the work intentionally bounded:

- redesign the reranker rubric without changing the six-feature ranking contract
- keep `must_have_match` unchanged
- replace lexical `title_relevance` with semantic role alignment
- replace coarse `preference_fit` with a weighted domain or role-family or location model
- expose clearer per-feature contribution visibility in ranking inspection artifacts
- align settings copy and calibration surfaces with the new ranking semantics

## Source-of-Truth Alignment

Affected current-state docs:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/cv_system/cv_system.yaml)
- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/settings_system/settings_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/inspection_debugging/inspection_debugging.yaml)
- [ranking.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/stages/ranking.yaml)

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/settings_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/inspection_debugging/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/generated/feature_capabilities_index.yaml)

Primary code and tests:

- [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/ai_score.py)
- [ranking.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/ranking.py)
- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/pipeline.py)
- [candidate.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/candidate.py)
- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv_cp/settings_schema.py)
- [test_ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/tests/test_ai_score.py)
- [test_ranking.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/tests/test_ranking.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/tests/test_pipeline.py)
- [test_candidate.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/tests/test_candidate.py)

Generated refresh required:

- yes

## Invariants

- The runtime six-feature ranking contract remains `ai_score`, `must_have_match`, `vector_similarity`, `title_relevance`, `seniority_fit`, and `preference_fit`.
- `must_have_match` stays unchanged in both semantics and implementation in this rollout.
- Ranking remains the sole owner of authoritative post-filter fit labels and final ranked selection.
- Preference alignment remains a soft ranking signal and must not outrank major requirement gaps by default.
- Ranking artifacts remain bounded and explainable.

## Implementation Tasks

### Task 1: Redesign the Reranker Rubric

Update [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/ai_score.py) so the reranker prompt behaves like an explicit ranking policy rather than a broad instruction block.

Changes:

- rewrite the rubric to define factor priority clearly
- make evidence quality expectations explicit
- define what should cap `ai_score` and block `strong`
- keep the structured output shape stable unless implementation proves a minimal additive field is necessary
- keep prompt provenance compatible with the central prompt-registry direction if that code path already exists in this branch

Acceptance criteria:

- the reranker prompt explicitly prioritizes required-skill coverage and evidence quality
- preference signals are clearly secondary
- ambiguous evidence produces conservative scoring
- existing output fields remain stable or change only additively with corresponding test updates

### Task 2: Replace Lexical `title_relevance` With Semantic Role Alignment

Update [ranking.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/ranking.py) so `title_relevance` becomes semantic role alignment instead of token overlap.

Likely work:

- introduce a bounded semantic alignment helper for candidate target role vs job title
- use `job_family` only as a support signal or fallback, not as a replacement for title semantics
- preserve a normalized `[0.0, 1.0]` score contract

Acceptance criteria:

- semantically close titles score better than pure token-overlap logic would allow
- the feature remains distinct from `preference_fit`
- the exposed runtime field name remains `title_relevance`

### Task 3: Introduce Weighted `preference_fit`

Update the candidate preference contract and ranking logic so `preference_fit` becomes a weighted combination of:

- domain alignment
- role-family alignment
- location-type alignment

Primary targets:

- [candidate.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/candidate.py)
- [ranking.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/ranking.py)
- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv_cp/settings_schema.py) if settings are made configurable

Changes:

- add additive support for `preferences.role_families`
- keep profiles without `role_families` valid and neutral on that dimension
- define weighted sub-scores with clear match vs neutral vs mismatch semantics
- separate `domains` from `role_families` instead of overloading domain preferences for both

Acceptance criteria:

- `preference_fit` no longer treats all preference categories as equal by default
- `preferences.role_families` is additive and backward-compatible
- location, domain, and role family are scored independently before weighting

### Task 4: Add Per-Feature Contribution Visibility

Update ranking artifacts and run inspection payloads in [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/pipeline.py) so operators can see how the final score was built.

Changes:

- add per-feature weighted contribution values for scored ranking rows
- include those contributions in ranking `inputs_sample`, `outputs_sample`, and scored-not-ranked samples
- keep artifact payloads bounded and readable
- ensure comparison-friendly fields are available for nearby ranked jobs

Acceptance criteria:

- a sampled ranking row exposes raw feature values, weighted contributions, and `final_score`
- operators can tell which features most influenced a ranking decision
- artifact payload size remains bounded and consistent with existing artifact policies

### Task 5: Add Weight and Threshold Calibration Surfaces

Update settings and docs so ranking calibration is explicit rather than implicit.

Primary targets:

- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv_cp/settings_schema.py)
- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/cv_system/cv_system.yaml)
- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/settings_system/settings_system.yaml)
- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/FitCV-pipeline.md)

Changes:

- align admin-facing weight descriptions with the new semantics of `title_relevance` and `preference_fit`
- document how fit-label thresholds should be interpreted after the reranker rubric update
- keep threshold ownership explicit and local to ranking-time behavior

Acceptance criteria:

- settings descriptions match runtime behavior
- docs explain how weights and fit labels should be tuned together
- no stale lexical-overlap description remains for `title_relevance`

### Task 6: Sync Feature, Stage, History, and Generated Docs

Update the affected current-state and history docs, then refresh generated discovery outputs.

Targets:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/cv_system/cv_system.yaml)
- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/settings_system/settings_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/inspection_debugging/inspection_debugging.yaml)
- [ranking.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/stages/ranking.yaml)
- feature history docs listed above
- generated outputs listed above

Acceptance criteria:

- source-of-truth docs match implemented runtime semantics
- history entries capture this as a ranking-quality follow-up rather than a new feature family
- generated discovery reflects the updated feature and stage contracts

## Verification Plan

Run targeted verification after implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_ai_score.py
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_ranking.py
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py -k "ranking or title_relevance or preference_fit"
```

If candidate profile contract tests are added or changed, run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_candidate.py
```

Manual verification checklist:

- inspect a ranking-stage artifact and confirm contribution fields are present and bounded
- confirm `must_have_match` behavior is unchanged on representative cases
- compare a few semantically close titles and confirm `title_relevance` is no longer only lexical
- confirm `preference_fit` distinguishes domain, role-family, and location effects
- inspect the reranker prompt or prompt provenance surface and confirm the stricter rubric is in effect

## Risks and Mitigations

### Reranker Overcorrection Risk

Risk:

- the new rubric could become too strict and suppress good borderline jobs

Mitigation:

- keep fit-label threshold tuning in the same rollout
- test representative strong vs stretch vs skip comparisons

### Feature Overlap Risk

Risk:

- semantic `title_relevance` and richer `preference_fit` could start encoding the same idea twice

Mitigation:

- keep `title_relevance` focused on role-title alignment
- keep `preference_fit` focused on explicit candidate preferences only

### Backward-Compatibility Risk

Risk:

- candidate profiles may not yet provide `role_families`

Mitigation:

- make `role_families` additive and optional
- treat missing values as neutral for that sub-dimension

## Done Definition

The work is complete when:

- the reranker rubric is materially stricter and more grounded
- `title_relevance` is semantic role alignment rather than pure token overlap
- `preference_fit` uses separate weighted dimensions for domain, role family, and location type
- ranking artifacts expose per-feature contribution visibility
- settings and docs explain calibration surfaces accurately
- targeted ranking tests pass
- affected docs and generated outputs are updated in the same rollout

## Task Status

Status: completed

- [x] Task 1: Redesign the reranker rubric
- [x] Task 2: Replace lexical `title_relevance` with semantic role alignment
- [x] Task 3: Introduce weighted `preference_fit`
- [x] Task 4: Add per-feature contribution visibility
- [x] Task 5: Add weight and threshold calibration surfaces
- [x] Task 6: Sync feature, stage, history, and generated docs
- [x] Run targeted verification
- [x] Update plan status after implementation
