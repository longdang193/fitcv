---
feature_type: modify
feature_name: settings_system
status: draft
summary: "Re-enable all six ranking features end-to-end, make zero-weight semantics explicit, and ensure ranking stage artifacts report the full six-feature ranking contract."
invariants:
  - "Ranking runtime must support the full six-feature contract end-to-end rather than filtering down to a hidden two-feature subset."
  - "A ranking feature is disabled only by an explicit configured weight of 0.0, not by hardcoded runtime exclusion."
  - "The ranking stage artifact must report the same six-feature contract the runtime actually used for scoring."
  - "Configured ranking weights must continue to sum to 1.0 (plus or minus 0.01) across all six features."
  - "Run-scoped artifacts must reflect the effective settings snapshot used by that run, not current repository defaults."
---

# Six-Feature Ranking Reactivation Design

## Affected Feature Contracts

- [docs/features/settings_system/settings_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/settings_system/settings_system.yaml)
- [docs/features/inspection_debugging/inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)

## Stage Contracts

- [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/ranking.yaml)

## Triage

Feature type: MODIFY  
Summary: Replace the hidden two-feature ranking runtime with a true six-feature ranking contract and update the ranking stage artifact to expose the exact six-feature inputs and weights used by each run.  
Reasoning: Ranking settings, ranking runtime, and ranking artifacts currently disagree. The admin/settings layer exposes six weights, runtime scoring only uses two features, and the ranking artifact reports a partial weight map that can sum to less than 1.0. This is a modification of existing settings and inspection features, centered on the ranking stage.  
Invariants:
- The six ranking features remain `ai_score`, `must_have_match`, `vector_similarity`, `title_relevance`, `seniority_fit`, and `preference_fit`.
- Zero weight means "supported but non-contributing", not "unsupported by runtime".
- `final_score` must always be explainable from the feature values and weights recorded for the run.
- The ranking artifact must expose enough data to recompute `final_score` from the artifact payload for sampled rows.
- Runs triggered before this change remain historically valid and need no migration rewrite.
Dependencies:
- `settings_system`
- `inspection_debugging`
- `ranking` stage contract
- candidate profile loading
- enrichment outputs
- reranker outputs
Affected stages:
- `ranking`
Affected features:
- `settings_system`
- `inspection_debugging`
Primary lens: mixed
Affected docs:
  feature_yaml:
    - `docs/features/settings_system/settings_system.yaml`
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history:
    - `docs/features/settings_system/history.md`
    - `docs/features/inspection_debugging/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - none
  readme: none
  generated:
    - none
Generated refresh required: no  
Spec needed: yes  
Plan needed: yes  
Risk level: medium

## Problem Statement

The current ranking system has three inconsistent contracts:

1. The admin/settings model exposes six ranking weights.
2. Runtime ranking only uses `ai_score` and `vector_similarity`.
3. The ranking stage artifact reports only those two runtime-selected weights.

That creates several user-visible problems:

- the UI implies that six ranking features influence `final_score`
- the runtime silently ignores four of them
- the ranking artifact can show `active_ranking_weights` that do not sum to 1.0
- operators cannot tell from the artifact whether a feature was unsupported or merely set to zero

This is especially confusing when a run records:

```json
{
  "active_ranking_weights": {
    "ai_score": 0.4,
    "vector_similarity": 0.2
  }
}
```

because that payload suggests an incomplete or broken ranking policy rather than a deliberate six-feature policy.

## Goal

Adopt one ranking contract everywhere:

- all six ranking features are computed and available end-to-end
- all six ranking weights are part of the runtime contract
- any feature may be made non-contributing by setting its weight to `0.0`
- the ranking stage artifact reports the complete six-feature contract used by the run

This lets operators distinguish:

- "feature supported but intentionally unused right now"
- "feature contributing to score"
- "feature value unavailable for a specific job and therefore defaulted"

without hidden runtime filtering.

## Non-Goals

This design does not:

- introduce a new ranking feature beyond the current six
- change the admin UI grouping model for ranking settings
- remove `fit_label` logic or alter fit-threshold semantics
- rewrite historical run artifacts
- redesign the run detail page beyond consuming richer ranking artifact content

## Current Behavior Summary

### Settings Layer

The settings schema treats all six ranking weights as editable and validates sum-to-one across the six-key set.

### Runtime Layer

The ranking runtime currently uses a hardcoded active-feature list with only two entries:

- `ai_score`
- `vector_similarity`

The other four features may exist in upstream data, but runtime scoring does not depend on them.

### Artifact Layer

The ranking stage artifact reports the same partial runtime-selected weight map, so the artifact mirrors the hidden runtime contract rather than the user-facing six-feature contract.

## Desired Contract

### Six Supported Ranking Features

The runtime contract must always include exactly these six features:

1. `ai_score`
2. `must_have_match`
3. `vector_similarity`
4. `title_relevance`
5. `seniority_fit`
6. `preference_fit`

### Zero-Weight Semantics

A feature is considered:

- supported when it is part of the six-feature contract
- contributing when its configured weight is greater than `0.0`
- non-contributing when its configured weight is exactly `0.0`

This replaces the current concept of "unsupported configured features are intentionally ignored".

### Weight Sum Rule

The configured six weights must still sum to `1.0` within tolerance.

Valid examples:

```yaml
ranking_weights:
  ai_score: 0.40
  must_have_match: 0.20
  vector_similarity: 0.15
  title_relevance: 0.10
  seniority_fit: 0.10
  preference_fit: 0.05
```

```yaml
ranking_weights:
  ai_score: 0.73
  must_have_match: 0.00
  vector_similarity: 0.27
  title_relevance: 0.00
  seniority_fit: 0.00
  preference_fit: 0.00
```

The second example is now valid and explicit rather than being simulated by runtime exclusion.

## Source of Each Ranking Feature

The pipeline must compute or carry all six features before final ranking.

### Job-side Inputs

Expected job-side sources:

- `required_skills`: enriched structured job
- `title` or `job_title`: normalized or enriched structured job
- `seniority`: enriched structured job
- `job_family`: enriched structured job
- `domain`: enriched structured job
- `location_type`: normalized or enriched structured job
- `vector_similarity`: shortlist row
- `ai_score`: reranker output

### Candidate-side Inputs

Expected candidate-side sources:

- candidate skills from the candidate profile
- `preferences.target_role`
- `preferences.seniority_target`
- `preferences.domains`
- `preferences.location_types`

### Computation Ownership

The ranking pipeline should own feature construction explicitly rather than depending on upstream `ai_scores` rows to happen to carry ranking side-data.

Recommended ownership:

- `build_ranking_features()` becomes the canonical place that assembles all six feature values
- `run_ai_scoring()` remains responsible for `ai_score` and `fit_label`
- ranking helper functions in `ranking.py` become the canonical computations for the four currently sidelined features

This keeps the ranking contract local to ranking rather than spread ambiguously across reranking.

## Proposed Runtime Changes

### 1. Replace Hidden Two-Feature Contract

Remove the notion of "active runtime ranking features" as a subset.

Replace it with:

- `SUPPORTED_RANKING_FEATURES = (...)` containing all six features
- defaults and missing-value defaults defined for all six features

Recommended default weights:

```yaml
ranking_weights:
  ai_score: 0.40
  must_have_match: 0.20
  vector_similarity: 0.15
  title_relevance: 0.10
  seniority_fit: 0.10
  preference_fit: 0.05
```

Recommended fallback defaults:

```yaml
missing_value_defaults:
  ai_score: 0.0
  must_have_match: 0.5
  vector_similarity: 0.0
  title_relevance: 0.5
  seniority_fit: 0.5
  preference_fit: 0.5
```

These defaults preserve the existing neutral-vs-conservative behavior of each feature family.

### 2. Make `build_ranking_features()` Compute the Full Feature Dict

For each shortlisted job with an AI score row, the feature builder should explicitly populate:

- `ai_score`
- `must_have_match`
- `vector_similarity`
- `title_relevance`
- `seniority_fit`
- `preference_fit`

It should also preserve supporting context needed for debugging and downstream display:

- `job_url`
- `title` and or `job_title`
- `required_skills`
- `seniority`
- `job_family`
- `domain`
- `location_type`
- `vector_rank`
- `fit_label`
- `fit_label_source`

### 3. Compute Final Score Across the Full Six-Feature Weight Map

`compute_final_score()` can keep the same weighted-sum structure, but its `weights` input must now always be the six-feature resolved map.

No renormalization step is needed if the six configured weights are already required to sum to `1.0`.

### 4. Preserve Zero Weights in Runtime and Artifacts

Zero-weight features must remain in:

- resolved runtime weights
- stage artifact decision summaries
- sampled ranking rows

They must not be removed from payloads just because they do not contribute to `final_score`.

## Proposed Ranking Artifact Changes

The ranking stage artifact should stop using a partial `active_ranking_weights` meaning "features runtime chose to keep".

Instead it should expose the full six-feature contract used by the run.

### Decision Summary Shape

Current decision summary fields should evolve to:

```json
{
  "ranking_fit_label_counts": {
    "skip": 1,
    "stretch": 2
  },
  "configured_ranking_weights": {
    "ai_score": 0.40,
    "must_have_match": 0.20,
    "vector_similarity": 0.15,
    "title_relevance": 0.10,
    "seniority_fit": 0.10,
    "preference_fit": 0.05
  },
  "configured_missing_value_defaults": {
    "ai_score": 0.0,
    "must_have_match": 0.5,
    "vector_similarity": 0.0,
    "title_relevance": 0.5,
    "seniority_fit": 0.5,
    "preference_fit": 0.5
  },
  "zero_weight_features": [],
  "contributing_features": [
    "ai_score",
    "must_have_match",
    "vector_similarity",
    "title_relevance",
    "seniority_fit",
    "preference_fit"
  ]
}
```

If the effective run settings intentionally disable some features:

```json
{
  "configured_ranking_weights": {
    "ai_score": 0.73,
    "must_have_match": 0.0,
    "vector_similarity": 0.27,
    "title_relevance": 0.0,
    "seniority_fit": 0.0,
    "preference_fit": 0.0
  },
  "zero_weight_features": [
    "must_have_match",
    "title_relevance",
    "seniority_fit",
    "preference_fit"
  ],
  "contributing_features": [
    "ai_score",
    "vector_similarity"
  ]
}
```

This makes the artifact self-explanatory.

### Inputs Sample Shape

Each row in `inputs_sample` should include all six ranking feature values so the final score can be audited:

```json
{
  "job_url": "https://example.com/job/1",
  "job_title": "Data Engineer",
  "ai_score": 0.85,
  "must_have_match": 1.0,
  "vector_similarity": 0.90,
  "title_relevance": 1.0,
  "seniority_fit": 0.5,
  "preference_fit": 1.0,
  "final_score": 0.89,
  "ranking_fit_label": "strong",
  "shortlist_origin": "vector_search"
}
```

### Outputs Sample Shape

`outputs_sample` should likewise carry the six features plus rank outcome.

### Changed-State Sample Shape

For `dropped_or_changed_sample`, ranking should include scored-but-not-ranked rows with the same six feature values and final score, so the cut line is explainable.

## Settings and UI Implications

The settings layer already exposes six weights. This rollout should align the defaults and copy with the real runtime.

Recommended behavior:

- keep all six weight inputs visible
- keep the sum indicator across all six
- add helper text or tooltips clarifying that `0.0` means the feature is enabled but contributes nothing to score

This is optional for the first code rollout but recommended so the UI matches the new semantics.

## Compatibility Considerations

### Historical Runs

Older runs may still have ranking artifacts with:

- two-feature `active_ranking_weights`
- no six-feature row samples

These artifacts remain valid historical records. The new contract applies only to newly triggered runs.

### Downstream Consumers

Any code or tests that assert ranking artifact keys must be updated to expect:

- full six-feature weight maps
- explicit zero-weight reporting
- six-feature row samples

If compatibility is needed temporarily, the artifact may include deprecated aliases for one release, but the preferred direction is to update tests and UI consumers together.

## Acceptance Criteria

This design is successful when:

1. `final_score` is computed from all six supported ranking features for newly triggered runs.
2. A feature contributes nothing only when its configured weight is `0.0`.
3. Runtime no longer silently drops four ranking features from the resolved weight map.
4. `build_ranking_features()` explicitly computes or assembles all six ranking feature values.
5. The ranking stage artifact reports the effective six-feature weight map and six-feature missing-value defaults used by the run.
6. The ranking stage artifact explicitly identifies zero-weight features and contributing features.
7. Ranking `inputs_sample`, `outputs_sample`, and ranked-vs-not-ranked debug samples include all six ranking feature values plus `final_score`.
8. A user can inspect the ranking JSON and understand whether a feature was active, zero-weighted, or defaulted for a row.
9. Existing settings validation still enforces six-weight sum-to-one semantics.

## Recommended Implementation Plan Scope

The implementation plan should cover:

1. Replace the two-feature runtime contract in [src/fitcv/ranking.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/ranking.py).
2. Update [config/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/config/ranking.yaml) to the intended six-feature baseline.
3. Move full six-feature assembly into [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py) `build_ranking_features()`.
4. Update ranking-stage artifact generation to emit the new six-feature decision summary and row samples.
5. Add or update tests for:
   - six-feature score computation
   - zero-weight semantics
   - ranking artifact payload shape
   - run-scoped effective settings propagation into ranking artifacts
6. Update affected feature and stage docs after implementation.

## Open Implementation Choices

Two implementation approaches are acceptable:

### Approach A

Compute the four non-LLM ranking features inside `build_ranking_features()` using the helper functions from `ranking.py`.

Why this is recommended:

- ranking feature ownership stays local to ranking
- stage artifacts can capture canonical feature values from one place
- reranker payloads stay focused on `ai_score` and `fit_label`

### Approach B

Continue populating those four values upstream in AI scoring and merely preserve them in ranking.

Why this is weaker:

- feature computation remains split across layers
- debugging ownership stays ambiguous
- stage artifact correctness depends on reranker row shape

Recommendation: Approach A.
