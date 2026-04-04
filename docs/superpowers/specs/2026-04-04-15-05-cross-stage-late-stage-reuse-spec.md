---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Add strict stage-owned reuse for ranking AI-score outputs and cv_analysis results so expensive late-stage reruns can skip unchanged work safely."
invariants:
  - "Reuse must be stage-owned: `ranking` owns AI-score reuse and `cv_analysis` owns analysis-result reuse."
  - "A reuse miss is acceptable; a stale reuse hit is not."
  - "Reuse must be decided per job record, not only per whole run."
  - "Artifacts and run detail must make fresh vs reused outcomes visible."
  - "`cv_generation` remains out of scope for this spec."
---

# Cross-Stage Late-Stage Reuse Spec

## Triage

Feature type: MODIFY  
Summary: Add safe, fingerprint-based reuse for `ranking` AI-score outputs and `cv_analysis` outputs so repeated late-stage runs avoid recomputing unchanged expensive work.  
Reasoning: This changes existing `cv_system` runtime behavior in two already-owned late stages. The work is stage-heavy because it alters the execution contract and artifact/debug semantics of `ranking` and `cv_analysis`, while also affecting inspection surfaces because operators must be able to see when reuse happened and why.  
Invariants:
- `ranking` remains the sole owner of ranking-time AI-score reuse decisions.
- `cv_analysis` remains the sole owner of analysis-result reuse decisions.
- Reuse decisions must be driven by strict stage input fingerprints, not loose heuristics.
- Fresh computation remains the safe fallback when any contract input is missing or unclear.
- `cv_generation` is not part of this reuse rollout.
Dependencies:
- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/pipeline.py)
- [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/ai_score.py)
- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/evidence.py)
- stage artifact/debug exporters in the control-plane layer
Affected stages:
- `ranking`
- `cv_analysis`
Affected features:
- `cv_system`
- `inspection_debugging`
Primary lens: mixed
Affected docs:
  feature_yaml: [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/cv_system.yaml)
  feature_history: [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/cv_system/history.md)
  feature_docs:
  - [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
  - [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/history.md)
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
Risk level: medium

## Why

The pipeline already reuses expensive early and middle-stage work well:

- enrich reuse via raw-job fingerprint
- shortlist job-embedding reuse
- shortlist candidate-query embedding reuse

The expensive late stages still recompute more often than they should:

- `ranking` reruns AI scoring even when the ranking input contract is unchanged
- `cv_analysis` reruns evidence retrieval, semantic alignment, gap analysis, and fit-gate preparation even when the ranked-job analysis contract is unchanged

These are also the stages most likely to be rerun during tuning:

- changing `cv_generation` behavior without changing `cv_analysis`
- adjusting reporting, artifacts, or admin surfaces
- rerunning the same ranked jobs for debugging or manual staged flow

That makes late-stage reuse a high-value next optimization.

## Problem

Today, a rerun of the same candidate and same ranked job can still trigger:

- fresh reranker / AI-score evaluation in `ranking`
- fresh evidence selection and semantic alignment in `cv_analysis`

even when all meaningful stage inputs are identical.

This causes:

- unnecessary LLM cost in `ranking`
- unnecessary embedding/scoring cost in `cv_analysis`
- slower manual staged iteration
- less predictable operator expectations when “nothing changed” but expensive stages rerun anyway

## Goals

1. Add per-job reuse for `ranking` AI-score outputs.
2. Add per-job reuse for `cv_analysis` outputs.
3. Keep reuse logic stage-owned and stage-local.
4. Make reuse exact and fingerprint-based, not fuzzy.
5. Surface reuse clearly in stage artifacts and run detail/debug outputs.
6. Preserve fresh recomputation as the default safe fallback.

## Non-Goals

- `cv_generation` reuse
- whole-run reuse that skips multiple stages at once
- fuzzy reuse based on “close enough” heuristics
- UI settings for reuse tuning in this first rollout
- retroactively rewriting old run artifacts

## Design Options Considered

### Option A: Whole-run late-stage reuse

Reuse all outputs from `ranking` onward when candidate and job set look similar.

Pros:

- conceptually simple

Cons:

- poor invalidation safety
- hard to explain
- one small downstream contract change can invalidate too much or too little

Not recommended.

### Option B: Stage-owned per-job reuse

Each expensive stage owns its own fingerprint and decides whether a given job record can be reused.

Pros:

- safer invalidation
- fits current stage boundaries
- easier debug visibility

Cons:

- more implementation detail

Recommended.

### Option C: Reuse `cv_generation` too in the same rollout

Pros:

- highest theoretical cost savings

Cons:

- highest correctness risk
- most complex invalidation contract

Not recommended for this spec.

## Recommended Design

Use **stage-owned, per-job, strict-fingerprint reuse** for:

- `ranking` AI-score outputs
- `cv_analysis` records

Keep reuse decisions independent per stage.

## Stage 1: `ranking` AI-Score Reuse

### Reuse unit

One scored ranking input / job row.

### What is being reused

The AI-score output produced before final weighted ranking selection, including:

- `ai_score`
- `fit_label`
- prompt/rubric-derived rationale fields already stored in the stage output

This does **not** mean reusing the final ranked top-N list directly. Final ranking still runs on the current scored inputs.

### Ranking reuse fingerprint

The fingerprint should include:

- stable job snapshot hash
- candidate profile fingerprint
- ranking prompt/rubric fingerprint
- ranking AI-score contract version
- relevant ranking config fingerprint

Recommended ingredients:

1. Job snapshot fingerprint
- based on the fields that the reranker truly consumes, such as:
  - title
  - domain
  - job_family
  - location_type
  - seniority
  - responsibilities
  - canonical required/preferred skills

2. Candidate fingerprint
- based on candidate facts/preferences the reranker consumes, such as:
  - flattened/canonical skills
  - target role / role families
  - seniority target
  - preference domains / locations
  - headline / recent role context if used by the reranker input contract

3. Prompt/runtime fingerprint
- reranker prompt version
- reranker model
- prompt template/runtime contract version

4. Ranking config fingerprint
- weights are **not** part of the AI-score itself and do not invalidate the AI-score reuse
- but thresholds or prompt-affecting config that changes the AI-score prompt contract **should** invalidate reuse

### Ranking reuse behavior

For each ranking input:

1. compute fingerprint
2. look up latest stored AI-score output for the same `job_url` + same fingerprint
3. if exact match exists:
- reuse the AI-score output
4. otherwise:
- recompute AI score normally

### Ranking artifact/debug expectations

Expose:

- `ai_score_reuse_status`
  - `reused_exact_match`
  - `fresh_compute`
  - `recomputed_contract_change`
- `ai_score_input_fingerprint`
- bounded summary counts:
  - reused
  - fresh

## Stage 2: `cv_analysis` Reuse

### Reuse unit

One analyzed ranked job record.

### What is being reused

The persisted `cv_analysis` output for a ranked job, including:

- selected evidence bundle
- evidence selection summary
- gap summary
- fit classification / fit-gate result
- analysis input summary used downstream by `cv_generation`

### `cv_analysis` reuse fingerprint

The fingerprint should include:

- ranked job snapshot fingerprint
- candidate profile fingerprint
- evidence retrieval contract fingerprint
- semantic alignment contract fingerprint
- gap-analysis / fit-gate contract fingerprint

Recommended ingredients:

1. Ranked-job fingerprint
- job snapshot fields used by analysis:
  - title
  - domain
  - job_family
  - responsibilities
  - canonical required/preferred skills
  - ranking fit label
  - ranking final score only if fit-gate logic depends on it

2. Candidate fingerprint
- candidate profile information analysis consumes:
  - evidence-bearing experiences / projects / achievements
  - candidate role/domain metadata
  - flattened/canonical skills
  - explicit preferences that affect fit gate

3. Evidence-selection contract fingerprint
- evidence retrieval channel contract version
- evidence-top-k
- channel pool size
- evidence scoring weights / selection rules

4. Semantic-alignment contract fingerprint
- semantic alignment enabled/disabled
- lexical/semantic weights
- embedding model / method
- semantic contract version

5. Gap / fit-gate contract fingerprint
- gap-analysis version
- fit-gate version / threshold contract

### `cv_analysis` reuse behavior

For each ranked job:

1. compute analysis fingerprint
2. look up latest stored `cv_analysis` record for the same `job_url` + same fingerprint
3. if exact match exists:
- reuse the persisted analysis record
4. otherwise:
- rerun analysis normally

### `cv_analysis` artifact/debug expectations

Expose:

- `analysis_reuse_status`
  - `reused_exact_match`
  - `fresh_compute`
  - `recomputed_contract_change`
- `analysis_input_fingerprint`
- bounded summary counts:
  - reused
  - fresh

## Storage / Persistence Model

Reuse lookup should be based on stage-owned persisted outputs that already exist in the pipeline’s inspection/export path or can be safely persisted alongside them.

Principles:

- each stage owns its own reuse record shape
- lookups should be by:
  - `job_url`
  - stage fingerprint
  - stage contract version
- latest exact match wins

This rollout does **not** require a shared generic cross-stage cache abstraction first.

Stage-local persistence is preferred for rollout safety.

## Artifact and UI Visibility

This spec requires clear operator visibility.

### Ranking

Artifacts / debug should show:

- total scored rows reused
- total scored rows freshly computed
- bounded sample of reused rows
- bounded sample of fresh rows

### `cv_analysis`

Artifacts / debug should show:

- total analysis rows reused
- total analysis rows freshly computed
- bounded sample of reused records
- bounded sample of fresh records

### Run-level visibility

Run summaries should expose stage-level reuse counts, for example:

```json
{
  "reuse_metrics": {
    "ranking": {
      "ai_score_reused": 2,
      "ai_score_fresh": 1
    },
    "cv_analysis": {
      "analysis_reused": 1,
      "analysis_fresh": 2
    }
  }
}
```

This keeps reuse observable without requiring operators to diff artifacts manually.

## Example

### Scenario

Run 1:

- `shortlist` returns 3 jobs
- `ranking` scores them
- `cv_analysis` analyzes the top 3 ranked jobs

Run 2:

- same candidate
- same shortlist/ranked-job contract
- only `cv_generation` prompt wording changed

### Desired behavior

`ranking`:

- all 3 AI-score rows reuse exact matches

`cv_analysis`:

- all 3 analysis records reuse exact matches

`cv_generation`:

- reruns fresh because this spec does not include CV-generation reuse

### Why this is good

- expensive late-stage recomputation is avoided
- downstream experimentation remains possible
- stage ownership stays clear

## Risks

- weak fingerprints could allow stale reuse
- overly broad invalidation could erase most reuse value
- persisted output lookup may need careful stage schema versioning

## Rollout Notes

Rollout order should be:

1. `ranking` AI-score reuse
2. `cv_analysis` reuse
3. shared run-detail reuse visibility

This keeps the first step smaller and helps validate the fingerprint design before reusing richer `cv_analysis` records.

## Acceptance Criteria

1. `ranking` can reuse AI-score outputs per job when the exact ranking-stage fingerprint matches.
2. `cv_analysis` can reuse analysis records per job when the exact analysis-stage fingerprint matches.
3. Fresh recomputation occurs automatically when any fingerprinted contract input changes.
4. Reuse visibility is present in stage artifacts and run-level inspection/debug outputs.
5. `cv_generation` remains fresh in this rollout.
6. A new run can mix reused and fresh rows within the same stage depending on exact-match availability.
