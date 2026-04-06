---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Add stage-level quality metrics so runs expose shortlist, ranking, cv_analysis, and cv_generation bottlenecks without requiring job-by-job artifact inspection."
invariants:
  - "Stage-level quality metrics must be derived from existing stage outputs and must not change stage decisions or ranking/generation behavior."
  - "Metric formulas must be explicit, bounded, and stable across run artifacts, exports, and admin UI surfaces."
  - "Metrics must distinguish stage bottlenecks from expected downstream filtering rather than implying every drop is a bug."
  - "Runs without enough denominator data must emit explicit zero-or-null-safe metrics rather than divide-by-zero failures or misleading percentages."
  - "Stage-level quality metrics are observability signals, not new fit authorities or filtering rules."
---

# Stage-Level Quality Metrics Spec

## Triage

Feature type: MODIFY  
Summary: Add run-level stage quality metrics for shortlist, ranking, `cv_analysis`, and `cv_generation` so operators can identify the real funnel bottleneck before tuning retrieval, ranking, analysis, or writing quality.  
Reasoning: This primarily extends existing inspection/debugging surfaces with new derived metrics, but it also modifies stage-owned runtime summaries because the metrics must be emitted from live stage outputs and preserved in stage artifacts. The work is stage-heavy because each metric is owned by a specific stage boundary and depends on stage-local counts.  
Invariants:
- Metrics must be derived from live stage outputs already produced by the pipeline.
- Metrics must not change pipeline decisions, thresholds, or fit labels.
- Every metric must declare its numerator, denominator, and zero-denominator behavior.
- Metrics must be available in both run-level inspection and stage-level artifacts.
- Metrics must be safe for succeeded runs and manual staged runs paused at intermediate stages.
Dependencies:
- pipeline run summary assembly in [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/pipeline.py)
- stage artifact builders in [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/pipeline.py)
- run detail rendering in [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- inspection templates in [run_detail.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/run_detail.html)
Affected stages:
- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`
Affected features:
- `inspection_debugging`
- `cv_system`
Primary lens: mixed
Affected docs:
  feature_yaml: [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
  feature_history: [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/history.md)
  feature_docs:
  - [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
  - [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)
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

The pipeline now exposes strong stage-local detail:

- shortlist raw-hit facts, backfill reasons, and candidate-query provenance
- ranking feature contributions and fit-label decisions
- `cv_analysis` evidence-selection and fit-gate outcomes
- `cv_generation` validation and repair outcomes

But there is still a monitoring gap:

- operators can inspect *what happened* job by job
- they cannot quickly see *where the bottleneck is* for a run

That means optimization work can still happen blind:

- is shortlist recall weak?
- is ranking too harsh?
- is `cv_analysis` skipping too many jobs after ranking approved them?
- is `cv_generation` the real failure point because validation is rejecting too many outputs?

Stage-level quality metrics solve that by adding a small, explicit funnel-health layer above the detailed artifacts.

## Goals

1. Add a small set of stage-level quality metrics that reveal the dominant bottleneck for a run.
2. Define formulas explicitly so the same metric means the same thing in artifacts, exports, and UI.
3. Surface metrics in a compact run-level view without forcing the operator to open every stage JSON.
4. Preserve the same metrics in stage artifacts so deeper debugging can connect a bad rate to the underlying records.
5. Keep the metrics safe for partial/manual-staged runs where later stages have not executed yet.

## Non-Goals

- adding a new scoring or filtering system
- replacing detailed stage artifacts with high-level metrics
- creating a historical analytics dashboard in this rollout
- introducing new user-configurable thresholds or alerts
- treating a high drop rate as automatically bad without stage context

## Proposed Metrics

### 1. Shortlist Backfill Rate

Purpose:

- show whether shortlist retrieval is relying on backfill too often instead of real vector hits

Definition:

```text
shortlist_backfill_rate =
  backfilled_jobs_total / scoring_shortlisted_jobs_total
```

Numerator:

- `backfilled_jobs_total`

Denominator:

- `scoring_shortlisted_jobs_total`

Zero-denominator behavior:

- emit `0.0` when no shortlist jobs exist

Interpretation:

- high rate suggests shortlist recall weakness or insufficient raw-hit quality
- low rate suggests shortlist is mostly driven by real retrieval

### 2. Ranking Label Distribution

Purpose:

- show whether ranking is collapsing too many jobs into one label bucket

Primary definition:

- compute authoritative ranking-fit label counts and rates over **scored ranking inputs**, not only final top-ranked survivors

Required outputs:

- `strong_count`
- `stretch_count`
- `skip_count`
- `strong_rate`
- `stretch_rate`
- `skip_rate`
- `total_scored`

Formula example:

```text
strong_rate = strong_count / total_scored
```

Zero-denominator behavior:

- counts `0`
- rates `0.0`

Interpretation:

- very high `skip_rate` may indicate harsh ranking calibration or weak shortlist quality
- very high `strong_rate` may indicate loose ranking thresholds or an overly easy candidate pool
- nearly all `stretch` can indicate poor threshold separation

### 3. CV Analysis Skip Rate

Purpose:

- show how often jobs that reached `cv_analysis` are being rejected before writing

Definition:

```text
cv_analysis_skip_rate =
  skipped_fit_gate / total_cv_analysis_processed
```

Numerator:

- `skipped_fit_gate`

Denominator:

- `generation_ready + skipped_fit_gate + analysis_failed`

Zero-denominator behavior:

- emit `0.0` when `cv_analysis` did not process any jobs yet

Interpretation:

- high skip rate suggests a mismatch between ranking approval and final fit-gate behavior, or a genuinely low-quality ranked pool

Companion outputs:

- `generation_ready_rate`
- `analysis_failed_rate`

### 4. CV Generation Validation-Fail Rate

Purpose:

- show whether the writing/validation layer is the bottleneck after `cv_analysis` handed off generation-ready jobs

Definition:

```text
cv_generation_validation_fail_rate =
  validation_failed / total_cv_generation_attempted
```

Numerator:

- `validation_failed`

Denominator:

- `accepted + validation_failed + generation_failed + persistence_failed`

Zero-denominator behavior:

- emit `0.0` when `cv_generation` has not attempted any jobs yet

Interpretation:

- high validation-fail rate suggests prompt grounding, section planning, or validator mismatch problems
- high generation/persistence failure with low validation-fail rate points to infrastructure/runtime issues instead

Companion outputs:

- `accepted_rate`
- `generation_failed_rate`
- `persistence_failed_rate`

## Metric Placement

### Run-Level Summary

Add a new bounded block in the run summary/results payload:

```json
"stage_quality_metrics": {
  "shortlist": {
    "backfill_rate": 0.33,
    "backfilled_jobs_total": 1,
    "scoring_shortlisted_jobs_total": 3
  },
  "ranking": {
    "label_distribution": {
      "strong_count": 0,
      "stretch_count": 2,
      "skip_count": 1,
      "strong_rate": 0.0,
      "stretch_rate": 0.67,
      "skip_rate": 0.33,
      "total_scored": 3
    }
  },
  "cv_analysis": {
    "skip_rate": 0.67,
    "generation_ready_rate": 0.33,
    "analysis_failed_rate": 0.0,
    "total_processed": 3
  },
  "cv_generation": {
    "validation_fail_rate": 0.5,
    "accepted_rate": 0.5,
    "generation_failed_rate": 0.0,
    "persistence_failed_rate": 0.0,
    "total_attempted": 2
  }
}
```

### Stage Artifacts

Each affected stage should also expose its own metric block inside its stage decision summary:

- `stage_transition_artifacts.shortlist.decision_summary.quality_metrics`
- `stage_transition_artifacts.ranking.decision_summary.quality_metrics`
- `stage_transition_artifacts.cv_analysis.decision_summary.quality_metrics`
- `stage_transition_artifacts.cv_generation.decision_summary.quality_metrics`

This keeps ownership local and avoids making the run-level block the only place the metric exists.

### Admin UI

Run detail should gain a compact **Stage Quality Metrics** section near the run summary, showing:

- metric name
- rate
- numerator / denominator
- short interpretation hint

This should be compact and flat, not a new full-screen dashboard.

## Current Bottleneck Interpretation Model

The UI and artifacts should make it easy to reason like this:

- high shortlist backfill rate
  - shortlist retrieval quality issue
- high ranking `skip_rate`
  - ranking calibration issue or weak scored pool
- low ranking skip rate but high `cv_analysis` skip rate
  - post-ranking handoff/fit-gate issue
- low upstream drop rates but high `cv_generation` validation-fail rate
  - prompt, grounding, or validation issue

This interpretation guidance belongs in the spec and feature docs, not as a hard-coded alert engine.

## Partial-Run Behavior

Manual staged runs may stop before all stages complete.

Rules:

- completed stages emit full metrics
- not-yet-run stages emit either:
  - no metric block, or
  - a bounded `"status": "not_available_yet"` wrapper

Recommended default:

- omit unavailable stage metric blocks from stage artifacts
- include them in run-level summary only when the stage has executed

This avoids confusing zeros that look like real outcomes.

## Example

Suppose one run shows:

- shortlist backfill rate: `0.50`
- ranking skip rate: `0.10`
- `cv_analysis` skip rate: `0.15`
- `cv_generation` validation-fail rate: `0.60`

Interpretation:

- shortlist has some recall weakness, but ranking and `cv_analysis` are not the main bottleneck
- the dominant bottleneck is `cv_generation`, because more than half of attempted outputs fail validation

Another run:

- shortlist backfill rate: `0.70`
- ranking skip rate: `0.55`
- `cv_analysis` skip rate: `0.10`
- `cv_generation` validation-fail rate: `0.00`

Interpretation:

- the main problem is upstream candidate-job matching and ranking calibration
- CV generation is not the bottleneck here

## Implementation Notes

### Derived, Not Stored As Source Of Truth

These metrics should be computed from existing counts in memory during run summary/stage artifact assembly.

Do not create a second independent persistence model for them.

### Explicit Formula Ownership

Each metric should be computed in the stage that owns its numerator/denominator inputs:

- shortlist backfill rate: shortlist summary builder
- ranking label distribution: ranking summary builder
- `cv_analysis` skip rate: `cv_analysis` summary builder
- `cv_generation` validation-fail rate: `cv_generation` summary builder

Then the run-level summary can aggregate these stage-owned metric blocks.

### Boundedness

Metrics should remain compact:

- counts
- rates
- denominator totals

Do not attach raw record arrays or long interpretation prose to the metric block itself.

## Risks

- Operators may over-interpret a high drop rate as automatically bad.
- Ranking label distribution can mislead if it is calculated over final top-N only instead of scored inputs.
- Zero values from not-yet-run stages can be mistaken for good outcomes if partial-run behavior is unclear.

## Mitigations

- document each metric’s denominator
- keep interpretation hints qualitative, not prescriptive
- only emit metrics for stages that actually executed
- preserve the underlying detailed artifacts so operators can drill down when a rate looks suspicious

## Acceptance Criteria

1. Run results include a bounded `stage_quality_metrics` block for completed stages.
2. `shortlist` artifacts expose `backfill_rate` with explicit numerator and denominator counts.
3. `ranking` artifacts expose authoritative fit-label counts and rates over scored inputs.
4. `cv_analysis` artifacts expose skip/ready/failure rates over all processed ranked jobs.
5. `cv_generation` artifacts expose validation-fail, accepted, generation-fail, and persistence-fail rates over attempted generation jobs.
6. Manual staged runs do not emit misleading zeros for stages that have not executed yet.
7. Admin run detail can show the compact stage-quality metric summary without opening stage JSON files.
