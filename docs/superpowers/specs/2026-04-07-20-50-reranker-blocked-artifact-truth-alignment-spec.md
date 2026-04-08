---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Align operator-facing artifacts with the new `blocked_by_reranker_fit` runtime path so `results.json` and `cv-debug.json` tell one truthful story about ranked jobs blocked before CV analysis work."
invariants:
  - "A ranked job blocked before `cv_analysis` work must never be represented as a completed analyzed row."
  - "A ranked job blocked by authoritative reranker fit must produce one consistent outcome across `results.json`, `cv-debug.json`, and stage-owned artifacts."
  - "`blocked_by_reranker_fit` remains distinct from `skipped_fit_gate`; the former is pre-analysis, the latter is post-analysis."
  - "The fix must stay narrow: correct artifact truth and coverage accounting without redesigning `stage-artifacts.json`, `cv_analysis.json`, or the artifact bundle layout."
---

# Reranker-Blocked Artifact Truth Alignment

## Triage

Feature type: MODIFY  
Summary: Propagate the new reranker-blocked runtime path consistently into compact operator-facing artifacts so the pipeline no longer tells conflicting stories about ranked jobs stopped before CV analysis work.  
Reasoning: The runtime now short-circuits reranker `fit_label = skip` jobs before expensive `cv_analysis` work, but the artifact layer only partially adopted that new status. Stage-owned artifacts understand `blocked_by_reranker_fit`, while `results.json` compact decision chains and `cv-debug.json` coverage accounting still lag behind.  
Invariants:
- `blocked_by_reranker_fit` must mean ranking completed and the job was stopped before evidence retrieval, gap computation, and semantic alignment work
- `skipped_fit_gate` must remain reserved for jobs that completed real `cv_analysis` work and were then blocked before generation
- `results.json` must not mix row-level `blocked_by_reranker_fit` with `decision_chain.cv_analysis.status = not_run`
- `cv-debug.json` must account for every ranked job, including ranked jobs blocked before generation
- The fix must preserve compact ledger ownership and avoid reintroducing bulky debug payloads into `results.json`
Dependencies:
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/worker_job.py`
- `src/fitcv_cp/app.py`
- `inspection_debugging` run-detail and export consumers
Affected stages:
- `ranking`
- `cv_analysis`
- `cv_generation`
Affected features:
- `inspection_debugging`
- `cv_system`
- `pipeline_performance`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history: `docs/features/inspection_debugging/history.md`
  feature_docs:
    - `docs/features/cv_system/history.md`
    - `docs/features/pipeline_performance/history.md`
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_overview.md`
Generated refresh required: yes
Spec needed: yes
Plan needed: yes
Risk level: medium

## Problem

The runtime and the artifact layer are now out of sync for ranked jobs blocked by the reranker.

The pipeline behavior changed correctly:

- ranked jobs with authoritative reranker `fit_label = skip` no longer pay evidence retrieval, gap computation, or semantic-alignment cost inside `cv_analysis`
- those rows now carry the explicit runtime outcome `blocked_by_reranker_fit`

But the artifact layer only adopted that change partially:

1. `results.json` row-level `cv_analysis` blocks can say `blocked_by_reranker_fit`, while the same row's compact `decision_chain.cv_analysis` still says `not_run`
2. `cv-debug.json` still behaves as if only generation-attempted rows matter, so reranker-blocked ranked jobs disappear from coverage accounting

That means the run exports no longer provide one consistent answer to a simple operator question:

- "What happened to each ranked job after ranking?"

## Evidence

In run `998ea86f-b6b0-47f1-8a19-985f22d63859`, stage-local artifacts correctly show the new runtime path:

- [cv_analysis.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-998ea86f-b6b0-47f1-8a19-985f22d63859-artifacts/cv_analysis.json#L14) reports `blocked_by_reranker_fit: 2`
- [cv_analysis.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-998ea86f-b6b0-47f1-8a19-985f22d63859-artifacts/cv_analysis.json#L15) reports `generation_ready: 1`

But the compact ledger is internally contradictory.

### Example 1: `Business & Data Analyst - B2B2C`

- [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-998ea86f-b6b0-47f1-8a19-985f22d63859-artifacts/results.json#L95) says:
  - `cv_analysis.status = "blocked_by_reranker_fit"`
- [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-998ea86f-b6b0-47f1-8a19-985f22d63859-artifacts/results.json#L109) says inside `decision_chain`:
  - `cv_analysis.status = "not_run"`
  - `completed = false`

### Example 2: `Freelance Data Scientist (Python & SQL) - AI Trainer`

- [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-998ea86f-b6b0-47f1-8a19-985f22d63859-artifacts/results.json#L143) says:
  - `cv_analysis.status = "blocked_by_reranker_fit"`
- [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-998ea86f-b6b0-47f1-8a19-985f22d63859-artifacts/results.json#L157) says inside `decision_chain`:
  - `cv_analysis.status = "not_run"`
  - `completed = false`

`cv-debug.json` also lags behind the new path:

- [cv-debug.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-998ea86f-b6b0-47f1-8a19-985f22d63859-artifacts/cv-debug.json#L6) says `ranked_jobs_total = 3`
- [cv-debug.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-998ea86f-b6b0-47f1-8a19-985f22d63859-artifacts/cv-debug.json#L7) says `debug_records_captured = 1`
- [cv-debug.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-998ea86f-b6b0-47f1-8a19-985f22d63859-artifacts/cv-debug.json#L8) says `attempted_generation_jobs_total = 1`
- [cv-debug.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-998ea86f-b6b0-47f1-8a19-985f22d63859-artifacts/cv-debug.json#L9) says `non_attempted_ranked_jobs_total = 0`
- [cv-debug.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-998ea86f-b6b0-47f1-8a19-985f22d63859-artifacts/cv-debug.json#L10) says `omission_reason_counts = {}`

That is incompatible with the stage-owned truth that two ranked jobs were blocked before generation.

## Root Cause

The reranker short-circuit introduced a new truthful runtime status:

- `blocked_by_reranker_fit`

But only the stage-owned artifact path was updated end to end.

Two downstream contract surfaces still reflect older assumptions:

1. the compact results-ledger `decision_chain` still treats the row like a generic `not_run`
2. the CV-debug coverage snapshot still assumes non-attempted ranked jobs only matter when they were analyzed and then skipped later

This is not a stage algorithm bug. It is a status-propagation and accounting bug in operator-facing artifacts.

## Design Goals

1. Make reranker-blocked rows internally consistent in `results.json`.
2. Make `cv-debug.json` coverage accounting complete for ranked jobs blocked before generation.
3. Preserve the distinct meaning of:
   - `blocked_by_reranker_fit`
   - `skipped_fit_gate`
4. Keep the scope narrow:
   - no broad artifact redesign
   - no stage-runtime redesign
   - no new heavy per-row payloads

## Proposed Design

### 1. Treat `blocked_by_reranker_fit` as a first-class compact ledger outcome

For reranker-blocked rows, `results.json` must keep all compact row surfaces aligned.

Required semantics:

- row-level `cv_analysis.status = "blocked_by_reranker_fit"`
- `decision_chain.cv_analysis.status = "blocked_by_reranker_fit"`
- `decision_chain.cv_analysis.completed = false`
- `decision_chain.primary_fit.source = "reranker"`
- `decision_chain.primary_fit.label = "skip"`
- `decision_chain.cv_generation.status = "not_attempted"`
- `decision_chain.cv_generation.attempted = false`
- `decision_chain.validation.status = "not_run"`

This keeps the row compact while still truthful.

### 2. Count reranker-blocked rows in `cv-debug.json`

`cv-debug.json` should become a complete ranked-job coverage summary again.

For reranker-blocked rows:

- increment `non_attempted_ranked_jobs_total`
- record an omission reason such as `blocked_by_reranker_fit`
- keep `attempted_generation_jobs_total` unchanged
- keep `debug_records_captured` scoped to rows with real generation debug payloads

That gives one honest summary:

- how many ranked jobs existed
- how many attempted generation
- how many did not
- why they did not

### 3. Preserve stage-owned artifact authority

This spec does not move ownership away from stage-local artifacts.

The truth split remains:

- `results.json` owns the compact job ledger
- `cv-debug.json` owns coverage of generation-attempted vs non-attempted ranked jobs
- `cv_analysis.json` owns stage-local outcome counts and analysis details
- `stage-artifacts.json` remains the bundled diagnostics export

The fix is only about making those surfaces agree on the reranker-blocked path.

### 4. Clarify reuse/accounting semantics where needed

This spec does not redesign `cv_analysis` reuse metrics, but any counters that are affected by reranker-blocked rows must avoid implying those rows were analyzed.

At minimum:

- blocked-before-analysis rows must not be counted as fresh analysis work
- blocked-before-analysis rows must not silently disappear from totals without explanation

If a full reuse-metrics relabel is needed later, that can be a follow-on cleanup.

## Expected Artifact Semantics

### `results.json`

For reranker-blocked rows:

```json
{
  "cv_analysis": {
    "status": "blocked_by_reranker_fit",
    "analysis_reuse_status": "not_run_reranker_skip",
    "analysis_input_fingerprint": null
  },
  "decision_chain": {
    "primary_fit": {
      "source": "reranker",
      "label": "skip"
    },
    "cv_analysis": {
      "status": "blocked_by_reranker_fit",
      "completed": false
    },
    "cv_generation": {
      "status": "not_attempted",
      "attempted": false
    },
    "validation": {
      "status": "not_run"
    }
  }
}
```

### `cv-debug.json`

For a run with:

- `3` ranked jobs
- `1` attempted generation
- `2` reranker-blocked rows

the summary should look conceptually like:

```json
{
  "ranked_jobs_total": 3,
  "debug_records_captured": 1,
  "attempted_generation_jobs_total": 1,
  "non_attempted_ranked_jobs_total": 2,
  "omission_reason_counts": {
    "blocked_by_reranker_fit": 2
  },
  "snapshot_complete": false
}
```

## UI Expectations

Any UI surface derived from compact results should render reranker-blocked jobs explicitly, not as a vague not-run state.

Examples:

- `Blocked by reranker fit`
- not:
  - `Not run`
  - `No CV attempted` without reason

This matters because the operator action implied by the outcome is different:

- reranker-blocked rows point upstream toward ranking/rule-filter tuning
- skipped-fit-gate rows point downstream toward analysis/gating behavior

## Non-Goals

- redesigning `stage-artifacts.json`
- redesigning `cv_analysis.json`
- redesigning the artifact bundle zip format
- changing reranker scoring thresholds
- changing rule-filter behavior
- changing the runtime short-circuit itself

## Acceptance Criteria

- A reranker-blocked row in `results.json` no longer mixes `blocked_by_reranker_fit` with `decision_chain.cv_analysis.status = not_run`
- `cv-debug.json` counts reranker-blocked ranked jobs as non-attempted ranked jobs with an explicit omission reason
- Stage-owned artifacts remain unchanged except where narrow truth-propagation needs a matching label/accounting update
- Focused regression tests prove:
  - reranker-blocked rows are internally consistent in `results.json`
  - `cv-debug.json` coverage accounting includes reranker-blocked jobs
