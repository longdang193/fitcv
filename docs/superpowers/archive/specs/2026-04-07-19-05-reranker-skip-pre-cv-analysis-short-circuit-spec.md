---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Short-circuit reranker `fit_label = skip` jobs before expensive `cv_analysis` evidence retrieval so ranking remains the sole post-filter fit authority without paying late-stage analysis cost."
invariants:
  - "Jobs with authoritative reranker `fit_label = skip` must not perform full `cv_analysis` evidence retrieval, gap computation, or semantic alignment work."
  - "The pipeline must preserve an explicit operator-facing outcome for ranked jobs that are blocked before CV generation."
  - "Stage-local artifacts must stay honest about whether a job was blocked before analysis work or after completed `cv_analysis` gate evaluation."
  - "`cv_generation` remains unattempted for both pre-analysis reranker blocks and completed-analysis fit-gate skips."
---

# Reranker Skip Pre-CV-Analysis Short-Circuit

## Triage

Feature type: MODIFY  
Summary: Stop reranker-`skip` jobs from paying full `cv_analysis` cost by short-circuiting them before evidence retrieval while keeping artifacts explicit about where they were blocked.  
Reasoning: The current runtime lets jobs already labeled `skip` by the authoritative reranker enter `cv_analysis`, where they still incur evidence retrieval, gap computation, and fit-gate evaluation before being rejected. That is both wasted work and a contract drift against the stated rule that reranker fit is the sole post-filter authority for CV eligibility.  
Invariants:
- The reranker remains the sole post-filter authority for ranking-time fit and CV-generation eligibility
- Jobs already labeled `skip` by ranking do not perform full `cv_analysis` work
- Artifact and UI surfaces must clearly distinguish "blocked before analysis work" from "analyzed and then skipped at the fit gate"
- Compact results-ledger ownership stays intact; deep debug remains stage-owned
Dependencies:
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/worker_job.py`
- `src/fitcv_cp/app.py`
- `inspection_debugging` consumers of final-stage statuses
Affected stages:
- `ranking`
- `cv_analysis`
- `cv_generation`
Affected features:
- `cv_system`
- `pipeline_performance`
- `inspection_debugging`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/cv_system/cv_system.yaml`
  feature_history: `docs/features/cv_system/history.md`
  feature_docs:
    - `docs/features/pipeline_performance/history.md`
    - `docs/features/inspection_debugging/history.md`
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

Today, a ranked job with authoritative reranker `fit_label = "skip"` still enters the `cv_analysis` stage loop and pays most of the expensive late-stage cost before being stopped.

That means the pipeline currently does all of this for jobs already known to be ineligible for CV generation:

- evidence retrieval
- evidence-pool merge/dedupe
- gap computation
- semantic alignment scoring
- fit-gate evaluation

Only after that work does the stage record `skipped_fit_gate` and prevent `cv_generation`.

This is wasteful, and it also blurs two different meanings:

1. jobs blocked because the reranker already decided `skip`
2. jobs that needed full `cv_analysis` and were then skipped by the later fit gate

## Evidence

In code, every ranked job enters the `cv_analysis` loop:

- [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L2783)

For each ranked job, the pipeline still does:

- evidence retrieval via `retrieve_evidence_bundle(...)` at [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L2838)
- fallback `retrieve_evidence(...)` at [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L2860)
- gap computation at [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L2885)
- fit-gate resolution at [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L2894)

Only then does a `skip` job get recorded as:

- `status = "skipped_fit_gate"` at [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L2897)

In run `b447fba4-4877-42c5-ac60-d554445bf1f8`, the pattern is visible:

- ranking processes `3` jobs and labels `2` as `skip` at [ranking.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-b447fba4-4877-42c5-ac60-d554445bf1f8-artifacts/ranking.json#L16)
- `cv_analysis` still processes all `3`, but only `1` is `generation_ready` and `2` become `skipped_fit_gate` at [cv_analysis.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-b447fba4-4877-42c5-ac60-d554445bf1f8-artifacts/cv_analysis.json#L14)

Example rows:

- `Business & Data Analyst - B2B2C` is ranked with `fit_label: "skip"` in [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-b447fba4-4877-42c5-ac60-d554445bf1f8-artifacts/results.json#L87) and still ends up with a `cv_analysis` record
- `Freelance Data Scientist (Python & SQL) - AI Trainer` follows the same path at [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-b447fba4-4877-42c5-ac60-d554445bf1f8-artifacts/results.json#L135)

## Root Cause

The runtime currently treats `ranking.fit_label` as informative for downstream reporting, but not as a hard short-circuit before `cv_analysis` work begins.

That creates two drifts:

1. performance drift
   - the pipeline spends late-stage analysis on jobs the reranker already decided should not reach CV generation

2. semantic drift
   - the same `skipped_fit_gate` status ends up covering both:
     - "blocked before meaningful analysis work"
     - "blocked after completed analysis work"

## Design Goals

1. Avoid expensive `cv_analysis` work for reranker-`skip` jobs.
2. Preserve a clear operator-facing explanation of why a ranked job got no CV.
3. Distinguish:
   - blocked-before-analysis
   - analyzed-then-skipped
4. Keep stage ownership honest:
   - `ranking` owns reranker fit
   - `cv_analysis` owns evidence retrieval and later fit-gate work only when analysis actually runs

## Proposed Design

### 1. Add a pre-analysis short-circuit at the start of the `cv_analysis` loop

Before evidence retrieval, inspect the authoritative ranking fit label already attached to the ranked job.

If:

- `fit_label == "skip"`

then:

- do not call `retrieve_evidence_bundle(...)`
- do not call `retrieve_evidence(...)`
- do not call `compute_gap(...)`
- do not perform semantic-alignment work

Instead, emit a synthetic final-stage outcome and continue.

### 2. Introduce a distinct status for reranker-blocked jobs

Do **not** reuse `skipped_fit_gate` for this short-circuit path.

Recommended new status:

- `blocked_by_reranker_fit`

Why:

- `skipped_fit_gate` should remain reserved for jobs that actually completed analysis and were then blocked by the fit gate
- overloading one status would keep artifact interpretation muddy

### 3. New status semantics

#### `blocked_by_reranker_fit`

Means:

- ranking completed
- authoritative reranker fit label was `skip`
- `cv_analysis` did not perform evidence retrieval or gap analysis
- `cv_generation` was not attempted

#### `skipped_fit_gate`

Means:

- `cv_analysis` did perform its real analysis work
- the later fit gate still blocked the job before generation

This distinction is the heart of the fix.

### 4. Expected compact ledger shape

For a reranker-blocked row:

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

### 5. Stage-artifact expectations

`cv_analysis.json` and `stage-artifacts.json` should now distinguish:

- `blocked_by_reranker_fit`
- `generation_ready`
- `skipped_fit_gate`
- `analysis_failed`

That makes the run-health story much clearer:

- jobs stopped before analysis cost
- jobs analyzed and approved
- jobs analyzed and rejected
- jobs analysis failed

### 6. UI expectations

Run detail and any job-ledger table should show reranker-blocked rows differently from fit-gate-skipped rows.

Example:

- `Blocked by reranker fit`
- `Skipped after CV analysis`

This is a meaningful operator distinction:

- one suggests filtering/ranking tightening upstream
- the other suggests analysis/gating behavior downstream

## Non-Goals

- changing reranker scoring itself
- changing fit-label thresholds in this spec
- redesigning the full artifact bundle
- changing CV-generation validation behavior
- redesigning the broader run-detail IA

## Acceptance Criteria

- Ranked jobs with `fit_label = skip` no longer perform evidence retrieval, gap computation, or semantic alignment inside `cv_analysis`
- A distinct status exists so reranker-blocked rows are not conflated with true analyzed-and-skipped rows
- `results.json`, `cv_analysis.json`, and `stage-artifacts.json` clearly distinguish the two paths
- `cv_generation` remains unattempted for both paths
- Focused regression tests prove the short-circuit happens before expensive analysis calls
