---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Fix `cv_analysis` embedding counter semantics so stage artifacts report trustworthy fresh/reused totals instead of inflated cumulative sums."
invariants:
  - "The `cv_analysis` stage must continue to expose evidence-selection diagnostics for every analyzed ranked job."
  - "Per-record evidence-selection summaries must remain available for deep debugging."
  - "Stage-level rollups must never sum cumulative per-record counters as if they were disjoint totals."
  - "Any fresh/reused counter surfaced to operators must have one unambiguous scope: per-record delta, per-run aggregate, or cumulative snapshot."
---

# CV Analysis Embedding Counter Contract Fix

## Summary

The current `cv_analysis` artifact contract reports embedding counters that look contradictory because the stage rollup sums per-record cumulative cache counters. This spec fixes the contract so artifact consumers can trust what "fresh" and "reused" mean at both the per-record and per-stage levels.

## Problem

The root cause is a scope mismatch between record-level counters and stage-level aggregation.

- In [evidence.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/evidence.py), `retrieve_evidence_bundle(...)` creates one `runtime_state` per analyzed job and stores cumulative `embedding_counts` from that runtime state into the record's `evidence_selection_summary`.
- In [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py), the `cv_analysis` stage summary then sums those record-level cumulative snapshots across all analysis records.

That creates inflated stage totals such as:

- `candidate_evidence_embeddings_fresh: 65`
- `candidate_evidence_embeddings_reused: 65`
- `merged_candidate_pool_total: 65`

for the same run artifact at [cv_analysis.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-d4a4ea1f-4292-4d47-bcc8-38f503f6c5e8-artifacts/cv_analysis.json).

These numbers are not trustworthy as stage-level performance diagnostics because they are sums of cumulative snapshots, not clean per-run totals or clean per-record deltas.

## Evidence

- [evidence.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/evidence.py) creates one runtime cache per record and exposes cumulative `embedding_counts` in the returned evidence bundle.
- [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py) builds `cv_analysis.decision_summary` by summing record-level `embedding_counts`.
- The run artifact at [cv_analysis.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-d4a4ea1f-4292-4d47-bcc8-38f503f6c5e8-artifacts/cv_analysis.json) shows repeated per-record `embedding_counts` snapshots such as:
  - `candidate_evidence: fresh=13, reused=13`
  - `job_context: fresh=7, reused=84`
  - later records: `job_context: fresh=11, reused=132`
  - later records: `job_context: fresh=13, reused=156`

Those repeated cumulative snapshots explain the inflated stage rollup.

## Design

### Contract separation

The artifact contract must clearly separate three scopes:

1. `per_record_snapshot`
- Diagnostic view of one analyzed job.
- May show the cumulative cache activity observed while retrieving evidence for that single job.

2. `per_record_delta`
- Fresh/reused counts attributable to that record's retrieval work only.
- This is the correct unit if stage-level totals are later summed.

3. `per_run_aggregate`
- One true aggregate for the whole `cv_analysis` stage in the run.
- Must be derived from one consistent scope, not from summed cumulative snapshots.

### Required contract change

The stage-level `cv_analysis.decision_summary` must stop reporting these fields using summed cumulative per-record snapshots:

- `candidate_evidence_embeddings_fresh`
- `candidate_evidence_embeddings_reused`
- `job_context_embeddings_fresh`
- `job_context_embeddings_reused`

Instead, the contract must adopt one of these valid models:

#### Preferred model

Stage-level fields become true per-run aggregate counts:

- `candidate_evidence_embedding_lookups_fresh`
- `candidate_evidence_embedding_lookups_reused`
- `job_context_embedding_lookups_fresh`
- `job_context_embedding_lookups_reused`

These must be computed from per-record deltas or a run-scoped aggregate, never from summed cumulative snapshots.

Per-record `evidence_selection_summary.semantic_alignment.embedding_counts` may remain, but it must be explicitly documented as a record-local snapshot.

#### Acceptable fallback model

If true per-run aggregate counting is not yet easy to produce, remove the four stage-level counters from `decision_summary` entirely and keep embedding counts only in each record's `evidence_selection_summary`.

This is better than keeping misleading stage totals.

### Naming clarification

The contract should avoid bare names like `fresh` and `reused` at stage level unless the counted unit is obvious.

Preferred naming:

- `*_embedding_lookups_fresh`
- `*_embedding_lookups_reused`

If the values represent unique embedded texts instead, the names must say `unique_texts`.

### UI and export expectations

Affected operator surfaces must treat the corrected counters as diagnostics, not health scores.

This includes:

- `cv_analysis.json`
- `stage-artifacts.json`
- run detail `Run Health` and any reuse/embedding diagnostics derived from stage artifacts

If stage-level embedding counters are removed temporarily, the UI must not substitute invented totals.

## Non-Goals

- Changing the semantic-alignment algorithm itself
- Disabling semantic alignment
- Reworking `ranking` or earlier shortlist thresholds
- Changing `selected_evidence_total` or `merged_candidate_pool_total`

## Affected Stages

- `cv_analysis`
- `cv_generation` as a downstream consumer of `cv_analysis` artifacts only if any reused artifact shape assumptions exist

## Feature and Stage Alignment

Feature type: MODIFY  
Summary: Fix `cv_analysis` embedding counter semantics so operator artifacts stop reporting inflated fresh/reused totals.  
Reasoning: Existing behavior is active but misleading; this is a contract correction, not a new feature.  
Invariants:
- Per-record evidence-selection diagnostics remain available
- Stage-level counters must reflect one valid counting scope only
- No operator-facing artifact may present summed cumulative snapshots as totals
Dependencies:
- `cv_analysis` evidence selection runtime state
- `inspection_debugging` run-artifact surfaces
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

## Acceptance Criteria

- `cv_analysis.json` no longer reports stage-level fresh/reused totals derived from summed cumulative record snapshots.
- If stage-level embedding counters remain, their counted unit and scope are explicit and internally consistent.
- At least one focused regression test proves that multiple `cv_analysis` records do not inflate stage totals by summing cumulative per-record snapshots.
- Run-detail diagnostics remain functional when reading the corrected stage artifact shape.

