---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Version the post-fix artifact family explicitly, export run-mode metadata in run-scoped artifacts, and make `cv_analysis` reuse metrics describe executed analysis work instead of mixing analyzed and pre-analysis-blocked rows."
invariants:
  - "Run-scoped artifacts must make their contract era explicit when runtime behavior changes in ways that affect operator interpretation."
  - "A run artifact bundle must export execution-policy metadata so `Run All` and `Stage by Stage` can be distinguished without control-plane lookup."
  - "`cv_analysis` reuse metrics must describe actual analysis execution, not silently mix executed analysis with pre-analysis reranker blocks."
  - "The fix should preserve compact operator-facing artifact ownership and avoid broad artifact redesign."
---

# Artifact Versioning, Run-Mode Metadata, and CV-Analysis Reuse Contract

## Triage

Feature type: MODIFY  
Summary: Tighten the run-artifact contract by versioning the post-fix artifact family explicitly, exporting execution mode in run-scoped bundles, and relabeling `cv_analysis` reuse semantics so performance debugging remains trustworthy after the reranker short-circuit rollout.  
Reasoning: Current artifacts reveal three related contract gaps: older and newer runs can share the same schema label while telling different reranker-blocked stories, exported bundles do not record whether the run was `Run All` or `Stage by Stage`, and `cv_analysis` reuse metrics still use totals that include pre-analysis blocked rows, making reuse math harder to trust.  
Invariants:
- Artifact versions must change when operator-facing semantics change materially
- Run-scoped exports must state execution mode explicitly
- `blocked_by_reranker_fit` rows remain distinct from `skipped_fit_gate`
- `cv_analysis` reuse counters must reflect analyzed rows, not all ranked rows
- The change remains a contract clarification, not a redesign of the entire artifact bundle
Dependencies:
- `src/fitcv_cp/worker_job.py`
- `src/fitcv_cp/app.py`
- `src/fitcv/pipeline.py`
- generated discovery surfaces
Affected stages:
- `ranking`
- `cv_analysis`
- `cv_generation`
Affected features:
- `inspection_debugging`
- `trigger_run_management`
- `cv_system`
- `pipeline_performance`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history: `docs/features/inspection_debugging/history.md`
  feature_docs:
    - `docs/features/trigger_run_management/history.md`
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

The current artifact family has three truth gaps that make run-to-run comparison harder than it should be.

### 1. Contract-era ambiguity

Saved runs from different code eras can claim the same schema family while exposing different semantics for reranker-blocked jobs.

For example:

- older artifact bundles can still pair row-level `blocked_by_reranker_fit` with compact `decision_chain.cv_analysis.status = not_run`
- newer bundles correctly propagate `blocked_by_reranker_fit` into compact decision chains and CV-debug omission accounting

Without an explicit version bump, an operator cannot tell from the artifact header alone whether a run is pre-fix or post-fix.

### 2. Missing run-mode metadata

The control plane stores `run_mode`, but run-scoped artifact bundles do not export it.

That means a downloaded bundle does not answer a basic operational question:

- Was this run executed as `Run All` or `Stage by Stage`?

This is especially limiting when auditing stage progress, pauses, timeout semantics, or artifact availability behavior after the fact.

### 3. Misleading `cv_analysis` reuse semantics

The current `cv_analysis` reuse metrics still use:

- `reused_analysis_records`
- `fresh_analysis_records`
- `total_analysis_records`

where `total_analysis_records` can include rows blocked before analysis work, while `fresh` and `reused` only count rows that actually executed analysis.

That makes the ratio mathematically ambiguous once reranker-blocked rows exist.

## Evidence

### Artifact-era drift

Historical runs already show the split:

- older run `e148d3e5-d028-4079-915c-3d555a0b8ec5` still mixes `blocked_by_reranker_fit` with `decision_chain.cv_analysis.status = not_run` in [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e148d3e5-d028-4079-915c-3d555a0b8ec5-artifacts/results.json#L95) and [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e148d3e5-d028-4079-915c-3d555a0b8ec5-artifacts/results.json#L109)
- newer run `e94182bb-d99d-40e6-bf4b-90f70dde011b` correctly aligns the same path in [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e94182bb-d99d-40e6-bf4b-90f70dde011b-artifacts/results.json#L95) and [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e94182bb-d99d-40e6-bf4b-90f70dde011b-artifacts/results.json#L109)

Yet both still present the same high-level artifact family shape:

- `results_schema_version = "results_job_ledger_v2"`
- `debug_schema_version = "cv_generation_debug_v2"`
- `bundle_schema_version = "run_artifact_bundle_v1"`

### Missing run-mode metadata

The bundle manifests for both runs:

- [e148 manifest.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e148d3e5-d028-4079-915c-3d555a0b8ec5-artifacts/manifest.json#L1)
- [e941 manifest.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e94182bb-d99d-40e6-bf4b-90f70dde011b-artifacts/manifest.json#L1)

list included files and status, but do not include:

- `run_mode`
- execution policy
- staged checkpoint policy

### CV-analysis reuse ambiguity

In `e148`:

- [cv_analysis.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e148d3e5-d028-4079-915c-3d555a0b8ec5-artifacts/cv_analysis.json#L22) shows `blocked_by_reranker_fit_rate = 0.8`
- [cv_analysis.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e148d3e5-d028-4079-915c-3d555a0b8ec5-artifacts/cv_analysis.json#L33) to [cv_analysis.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e148d3e5-d028-4079-915c-3d555a0b8ec5-artifacts/cv_analysis.json#L35) show:
  - `reused_analysis_records = 0`
  - `fresh_analysis_records = 1`
  - `total_analysis_records = 5`

In `e941`:

- [cv_analysis.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e94182bb-d99d-40e6-bf4b-90f70dde011b-artifacts/cv_analysis.json#L22) shows `blocked_by_reranker_fit_rate = 0.666...`
- [cv_analysis.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e94182bb-d99d-40e6-bf4b-90f70dde011b-artifacts/cv_analysis.json#L33) to [cv_analysis.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e94182bb-d99d-40e6-bf4b-90f70dde011b-artifacts/cv_analysis.json#L35) show:
  - `reused_analysis_records = 1`
  - `fresh_analysis_records = 0`
  - `total_analysis_records = 3`

Those totals are no longer self-explanatory because blocked-before-analysis rows are included in total processed rows but not in reused/fresh execution counts.

## Root Cause

The artifact contract has evolved incrementally as the pipeline gained:

- reranker short-circuiting
- reranker-blocked status propagation
- richer run-mode-aware control-plane behavior

But the exported schemas were not versioned or expanded consistently when those operator-facing semantics changed.

At the same time, `cv_analysis` reuse metrics retained names from the older “every ranked row is analyzed” era, even though the runtime now has a distinct pre-analysis blocked path.

## Design Goals

1. Make artifact contract eras explicit when operator-facing semantics change.
2. Make run-scoped artifact bundles self-describing about execution mode.
3. Make `cv_analysis` reuse metrics understandable without needing code knowledge.
4. Preserve the compact ledger/bundle model and avoid broad export redesign.

## Proposed Design

### 1. Bump artifact versions for the reranker-blocked truth family

Introduce explicit post-fix contract versions for the run-scoped artifact family.

Recommended bumps:

- `results_job_ledger_v2` → `results_job_ledger_v3`
- `cv_generation_debug_v2` → `cv_generation_debug_v3`
- `run_artifact_bundle_v1` → `run_artifact_bundle_v2`

The version bump should mark that the following are guaranteed:

- reranker-blocked rows are propagated truthfully in compact decision chains
- CV-debug coverage accounting includes reranker-blocked ranked jobs
- run-mode metadata is present in the run-scoped artifact family

This makes old bundles clearly historical instead of ambiguously “same schema, different truth.”

### 2. Export run-mode metadata in run-scoped artifacts

Add explicit execution metadata to at least:

- `manifest.json`
- `results.json`
- optionally `cv-debug.json` and `stage-artifacts.json` headers for consistency

Recommended fields:

```json
{
  "run_mode": "run_all",
  "run_mode_label": "Run All"
}
```

Optional secondary field if helpful:

```json
{
  "execution_policy": "continuous"
}
```

or

```json
{
  "execution_policy": "manual_staged"
}
```

The goal is not to invent a large lifecycle schema, only to make exported bundles auditable by mode.

### 3. Reframe `cv_analysis` reuse metrics around executed analysis

Retire or de-emphasize the ambiguous trio:

- `reused_analysis_records`
- `fresh_analysis_records`
- `total_analysis_records`

Replace with execution-aware metrics such as:

```json
{
  "analysis_rows_executed": 1,
  "reused_analysis_rows": 1,
  "fresh_analysis_rows": 0,
  "blocked_before_analysis_rows": 2,
  "analysis_reuse_rate": 1.0
}
```

Rules:

- `analysis_rows_executed = reused_analysis_rows + fresh_analysis_rows`
- `blocked_before_analysis_rows` is kept explicit
- the reuse rate denominator is `analysis_rows_executed`, not all ranked rows

This keeps the metric family truthful to what actually happened.

### 4. Preserve stage-owned truth while improving headers and summaries

This spec does not redesign:

- per-stage detailed payloads
- `stage-artifacts.json` sample structure
- `results.json` row compactness

The change is a header/summary contract cleanup:

- explicit artifact era
- explicit run mode
- explicit reuse semantics

## Expected Contract Shape

### `results.json`

Header example:

```json
{
  "results_schema_version": "results_job_ledger_v3",
  "run_mode": "manual_staged",
  "run_mode_label": "Stage by Stage"
}
```

### `cv-debug.json`

Header example:

```json
{
  "debug_schema_version": "cv_generation_debug_v3",
  "run_mode": "run_all",
  "run_mode_label": "Run All"
}
```

### `manifest.json`

Header example:

```json
{
  "bundle_schema_version": "run_artifact_bundle_v2",
  "run_mode": "run_all",
  "run_mode_label": "Run All"
}
```

### `cv_analysis.json`

Decision-summary example:

```json
{
  "reuse_metrics": {
    "analysis_rows_executed": 1,
    "reused_analysis_rows": 1,
    "fresh_analysis_rows": 0,
    "blocked_before_analysis_rows": 2,
    "analysis_reuse_rate": 1.0
  }
}
```

## Migration / Compatibility

Older artifacts should remain readable as historical exports.

The system should not attempt to rewrite old log folders.
Instead:

- old bundles remain on older schema versions
- new bundles use the bumped versions
- any UI that reads bundles should tolerate older versions gracefully

If helpful, the run detail UI can later display a small note when a downloaded artifact bundle predates the latest contract.

## Non-Goals

- redesigning the entire artifact bundle structure
- redesigning stage artifact samples
- changing reranker or rule-filter behavior
- changing the runtime short-circuit logic
- backfilling old log folders in place

## Acceptance Criteria

- New run-scoped artifacts carry bumped schema versions for the post-fix contract family
- New bundles export `run_mode` explicitly
- `cv_analysis` reuse metrics no longer require code knowledge to interpret
- Old bundles remain readable and clearly distinguishable from new ones by version
