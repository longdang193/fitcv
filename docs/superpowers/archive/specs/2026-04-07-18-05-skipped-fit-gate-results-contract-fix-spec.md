---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Fix the `results.json` contract so skipped-fit-gate rows report one consistent final-stage outcome instead of conflicting `cv_analysis` states."
invariants:
  - "A single job row in `results.json` must not report conflicting final-stage outcomes for the same run."
  - "A `skipped_fit_gate` outcome is an explicit completed `cv_analysis` result, not a `not_run` placeholder."
  - "Jobs with reranker `fit_label = skip` may still enter `cv_analysis`, but they must stop at the fit gate before `cv_generation`."
  - "The compact job ledger must stay compact; this fix corrects semantics, not by reintroducing bulky row payloads."
  - "Stage-local diagnostics in `cv_analysis.json`, `cv_generation.json`, and `stage-artifacts.json` remain the deeper debug source."
---

# Skipped Fit-Gate Results Contract Fix

## Triage

Feature type: MODIFY  
Summary: Correct `results.json` so jobs skipped at the CV fit gate report a single consistent final-stage story across `cv_analysis` and `decision_chain`.  
Reasoning: The behavior already exists, but the exported ledger contradicts itself for skipped-fit-gate rows, which makes operator-facing outcomes untrustworthy.  
Invariants:
- A row that says `cv_analysis.status = skipped_fit_gate` must not also say `decision_chain.cv_analysis.status = not_run`
- `skipped_fit_gate` remains a valid completed `cv_analysis` outcome
- `cv_generation` remains unattempted for skipped-fit-gate rows
- The fix must preserve current compact ledger ownership and avoid reintroducing rich per-row debug payloads
Dependencies:
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/worker_job.py`
- `inspection_debugging` run-detail and export consumers
Affected stages:
- `cv_analysis`
- `cv_generation`
Affected features:
- `inspection_debugging`
- `cv_system`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history: `docs/features/inspection_debugging/history.md`
  feature_docs:
    - `docs/features/cv_system/history.md`
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

## Stage Execution Clarification

This fix is grounded in the actual stage behavior:

- ranked jobs do enter the `cv_analysis` loop
- `cv_analysis` still performs evidence retrieval, gap computation, and fit-gate evaluation
- jobs resolved as `skip` stop there with `status = "skipped_fit_gate"`
- those jobs do **not** proceed into actual `cv_generation`

So the contract bug is not that skipped jobs somehow bypass `cv_analysis`.

The bug is that the compact ledger later understates that completed gate decision as:

- `decision_chain.cv_analysis.status = "not_run"`

even though stage-local artifacts and row-level fields correctly show:

- `cv_analysis.status = "skipped_fit_gate"`

## Problem

`results.json` currently tells two different stories for the same skipped-fit-gate job.

For skipped rows, the compact ledger row correctly reports:

- `cv_analysis.status = "skipped_fit_gate"`

But the same row's `decision_chain` still says:

- `cv_analysis.status = "not_run"`
- `cv_analysis.completed = false`

That contradiction makes the operator-facing ledger unreliable, especially in run detail where the pipeline outcome text is derived from `decision_chain`.

## Evidence

In the run artifacts for `b447fba4-4877-42c5-ac60-d554445bf1f8`:

### Example 1: `Business & Data Analyst - B2B2C`

- [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-b447fba4-4877-42c5-ac60-d554445bf1f8-artifacts/results.json#L95) reports:
  - `cv_analysis.status = "skipped_fit_gate"`
- [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-b447fba4-4877-42c5-ac60-d554445bf1f8-artifacts/results.json#L109) reports inside `decision_chain`:
  - `cv_analysis.status = "not_run"`
  - `completed = false`

### Example 2: `Freelance Data Scientist (Python & SQL) - AI Trainer`

- [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-b447fba4-4877-42c5-ac60-d554445bf1f8-artifacts/results.json#L143) reports:
  - `cv_analysis.status = "skipped_fit_gate"`
- [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-b447fba4-4877-42c5-ac60-d554445bf1f8-artifacts/results.json#L157) reports inside `decision_chain`:
  - `cv_analysis.status = "not_run"`
  - `completed = false`

The stage-local artifacts do not support the `not_run` interpretation:

- [cv_analysis.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-b447fba4-4877-42c5-ac60-d554445bf1f8-artifacts/cv_analysis.json#L14) shows:
  - `generation_ready: 1`
  - `skipped_fit_gate: 2`
  - `analysis_failed: 0`

So the stage contract already treats skipped-fit-gate as a real completed `cv_analysis` outcome.

The code path also confirms this execution model:

- ranked jobs enter the `cv_analysis` loop in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L2783)
- evidence retrieval happens before the fit gate in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L2838)
- gap computation happens before the fit gate in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L2885)
- skipped jobs are recorded as `skipped_fit_gate` in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L2897)
- only `ready_for_generation` records continue into actual CV writing in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L3037)

## Root Cause

The root cause is a contract handoff mismatch between the `cv_analysis` outcome model and the compact row `decision_chain`.

- The row-level `cv_analysis` block preserves the real analysis outcome.
- The `decision_chain` builder still uses a `not_run` placeholder on the skipped-fit-gate path.

That means the ledger row mixes:

- one stage-aware truth (`cv_analysis.status = skipped_fit_gate`)
- one stale fallback model (`decision_chain.cv_analysis.status = not_run`)

This is not a stage algorithm bug. It is an export-contract bug.

## Design Goals

1. Make every skipped-fit-gate row internally consistent.
2. Keep `results.json` compact and job-ledger-focused.
3. Preserve the stage-local debug split:
   - `cv_analysis.json` owns analysis details
   - `cv_generation.json` owns writing/validation/persistence details
4. Keep the meaning of `skipped_fit_gate` explicit for run-detail UI and downstream consumers.
5. Keep the artifact scope narrow: fix the contradictory ledger/export semantics without redesigning the broader artifact set.

## Proposed Contract

### Correct meaning of `skipped_fit_gate`

`skipped_fit_gate` means:

- `cv_analysis` ran far enough to make a completed gate decision
- evidence retrieval and gap analysis already happened inside `cv_analysis`
- the job was not eligible to proceed into CV writing
- `cv_generation` was not attempted

It does **not** mean:

- final-stage processing never started
- `cv_analysis` was absent
- the job was simply `not_run`

### Required `results.json` row shape semantics

For a skipped-fit-gate row:

- `cv_analysis.status = "skipped_fit_gate"`
- `cv_analysis.completed = true` in `decision_chain`
- `cv_generation.status = "skipped_fit_gate"` or `not_attempted`, but it must remain explicitly unattempted
- `validation.status = "not_run"`

Preferred consistent representation:

```json
{
  "cv_analysis": {
    "status": "skipped_fit_gate",
    "analysis_reuse_status": "...",
    "analysis_input_fingerprint": "..."
  },
  "decision_chain": {
    "cv_analysis": {
      "status": "skipped_fit_gate",
      "completed": true
    },
    "cv_generation": {
      "status": "skipped_fit_gate",
      "attempted": false
    },
    "validation": {
      "status": "not_run"
    }
  }
}
```

### UI expectations

Any control-plane surface derived from `results.json` must treat skipped-fit-gate as:

- a completed CV-analysis outcome
- a non-attempted CV-generation outcome

This includes:

- run detail pipeline outcome text
- any future results-ledger table or bundle manifest summaries

### Artifact scope clarification

This is an artifact-contract correction, but it is intentionally narrow.

It should change:

- `results.json`
- any UI or export-consumer logic that reads the compact `decision_chain`

It should **not** broadly redesign:

- `cv_analysis.json`
- `cv_generation.json`
- `stage-artifacts.json`
- the stage-artifact bundle zip layout

Those artifacts already reflect the stage split more accurately than the compact ledger. The problem is that the ledger understates what already happened.

## Non-Goals

- redesigning the full run-artifact set
- changing the fit-gate thresholding logic
- changing ranking labels
- changing `cv_analysis` evidence selection
- changing `cv_generation` validation behavior
- reintroducing full per-row stage payloads into `results.json`

## Acceptance Criteria

- A skipped-fit-gate row in `results.json` no longer contains contradictory `cv_analysis` states.
- `decision_chain.cv_analysis.status` matches the row-level `cv_analysis.status` for skipped-fit-gate jobs.
- `decision_chain.cv_analysis.completed` is `true` for skipped-fit-gate jobs.
- `cv_generation` remains explicitly unattempted for skipped-fit-gate jobs.
- Focused regression tests lock this contract for at least one skipped-fit-gate result row.
