---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Persist bounded structured artifacts at major pipeline stage boundaries so each transition can be inspected without reconstructing runtime state."
invariants:
  - "Each major pipeline stage must expose one explicit output artifact contract."
  - "Stage artifacts must be captured from the live runtime path, not recomputed later from final outputs."
  - "Artifacts are debugging and inspection surfaces, not new systems of record."
  - "Artifact payloads must remain bounded and stage-focused rather than dumping full raw state by default."
  - "Adding stage artifacts must not introduce a second hidden decision system."
---

# Stage Transition Artifacts Design

## Affected Feature Contracts

- [`docs/features/cv_system/cv_system.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)
- [`docs/features/trigger_run_management/trigger_run_management.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/trigger_run_management/trigger_run_management.yaml)
- [`docs/features/inspection_debugging/inspection_debugging.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)

## Stage Contracts

- [`docs/stages/normalize.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/normalize.yaml)
- [`docs/stages/enrich.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/enrich.yaml)
- [`docs/stages/rule_filter.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/rule_filter.yaml)
- [`docs/stages/shortlist.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/shortlist.yaml)
- [`docs/stages/ranking.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/ranking.yaml)
- [`docs/stages/cv_generation.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/cv_generation.yaml)

## Triage

Feature type: MODIFY  
Summary: Add structured run-scoped artifacts at major pipeline stage boundaries so operators can inspect each stage output directly.  
Reasoning: The system already has run exports, CV debug snapshots, stage events, and some stage tables, but it still requires inference to understand what happened between major stages. This is an incremental inspection/debugging improvement for an existing pipeline, not a new end-user feature.  
Invariants:
- Stage artifacts must reflect actual runtime outputs at the moment each stage completed.
- Artifacts must improve inspection/debuggability without becoming the canonical storage model for all stage data.
- The design must preserve clear stage ownership rather than mixing multiple stages into one ambiguous blob.
- Storage must stay bounded and practical for routine runs.
- Existing run exports and CV debug snapshots must remain supported during rollout.
Dependencies:
- `cv_system`
- `trigger_run_management`
- `inspection_debugging`
- stage-aware pipeline stage contracts
- existing run export and CV debug snapshot infrastructure
Affected stages:
- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_generation`
Affected features:
- `cv_system`
- `trigger_run_management`
- `inspection_debugging`
Primary lens: stage
Affected docs:
  stage_contracts:
    - `docs/stages/normalize.yaml`
    - `docs/stages/enrich.yaml`
    - `docs/stages/rule_filter.yaml`
    - `docs/stages/shortlist.yaml`
    - `docs/stages/ranking.yaml`
    - `docs/stages/cv_generation.yaml`
  feature_yaml:
    - `docs/features/cv_system/cv_system.yaml`
    - `docs/features/trigger_run_management/trigger_run_management.yaml`
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history:
    - `docs/features/cv_system/history.md`
    - `docs/features/trigger_run_management/history.md`
    - `docs/features/inspection_debugging/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - none
  readme: none
  generated:
    - `docs/generated/*`
Generated refresh required: yes  
Spec needed: yes  
Plan needed: yes  
Risk level: medium

## Why This Spec Exists

The current pipeline is much easier to inspect than before, but debugging still becomes harder than it should be once a job falls between stage boundaries.

Examples from recent work:

- a job can show `not_shortlisted`, but without deeper stage-local data it is hard to tell whether:
  - retrieval never returned it
  - it was backfilled later for scoring
  - it was scored but lost ranking
- a ranked job can now show a decision chain, but we still do not persist compact stage outputs for:
  - normalized and deduplicated job shape
  - enriched job shape used downstream
  - actual shortlist rows handed into scoring
  - exact ranking inputs handed into final ranking
- CV generation now has a dedicated debug snapshot, but earlier stages still require reconstruction from scattered tables, events, and the final run export

So the problem is not that the pipeline lacks any debugging. The problem is that the major transition points still do not produce first-class, bounded, run-scoped artifacts of their own.

## Problem Statement

The pipeline currently has recognizable stage boundaries, but only some of them persist an inspectable structured output artifact.

This creates three problems:

1. debugging requires reconstruction instead of inspection
2. stage-local contracts are harder to verify than they should be
3. later-stage outcomes are easier to see than the actual transition that produced them

The most valuable missing capability is:

- each major stage should emit a bounded structured artifact that captures what it handed to the next stage

That would let us debug incrementally:

1. verify Stage N output
2. verify Stage N+1 consumed the expected shape
3. stop guessing where drift occurred

## Design Goal

Introduce bounded run-scoped **stage transition artifacts** at major pipeline boundaries so operators can inspect the concrete handoff between stages without recomputation.

The design should:

- make stage boundaries explicit
- make each artifact easy to interpret in isolation
- keep artifacts small enough for routine persistence
- preserve the distinction between:
  - authoritative runtime data
  - convenience inspection/debug surfaces

The design should also align each runtime artifact block to one documented stage contract so the inspection surface and the documentation boundary model do not drift apart.

## Major Transition Points

Phase 1 should treat the following as the major pipeline stage groups.

These now align directly with the stage contracts in `docs/stages/*.yaml`, which should be treated as the boundary truth for stage identity and ownership while this spec defines the bounded runtime artifact captured at each boundary.

### 1. Ingest + Normalize

Primary output:

- normalized jobs
- deduplication results
- pre-enrichment global rejects

Why this boundary matters:

- it defines the candidate job pool that enrichment actually sees
- it explains why some raw inputs disappear before enrichment

### 2. Enrich + Candidate Load

Primary output:

- enriched jobs
- candidate profile snapshot actually used in runtime
- canonical enriched fields that downstream stages depend on

Why this boundary matters:

- it defines the stable downstream job contract
- it is where fields like `required_skills`, `job_family`, and canonical years fields become usable

### 3. Rule Filter

Primary output:

- passed jobs
- rejected jobs
- reject reasons

Why this boundary matters:

- it is the deterministic pre-retrieval gate
- it defines the eligible set for retrieval and ranking

### 4. Retrieval + Shortlist

Primary output:

- raw vector-search hits
- scoring shortlist after any backfill
- shortlist transition reasons per passed job

Why this boundary matters:

- it explains the gap between passed jobs and scored jobs
- it is where retrieval recall issues become visible

### 5. AI Scoring + Ranking

Primary output:

- reranker scores
- authoritative `ranking_fit_label`
- runtime ranking inputs actually used to compute `final_score`
- final ranked jobs

Why this boundary matters:

- it is the primary post-filter fit and ranking authority
- it determines which jobs are eligible for CV generation

### 6. CV Generation + Validation

Primary output:

- evidence used
- gap explanation
- structured CV initial/final
- validation state
- CV generation status

Why this boundary matters:

- it explains final artifact acceptance or rejection
- it already has the strongest existing debug surface and should remain the model for later stage-local inspection

## Proposed Artifact Model

### Recommendation

Persist a **single run-scoped stage artifact JSON** with one bounded block per major stage.

Recommended top-level shape:

```json
{
  "run_id": "...",
  "artifact_schema_version": "stage_transition_artifacts_v1",
  "created_at": "...",
  "snapshot_complete": true,
  "stages": {
    "normalize": {...},
    "enrich": {...},
    "rule_filter": {...},
    "shortlist": {...},
    "ranking": {...},
    "cv_generation": {...}
  }
}
```

Why this is the best first rollout:

- one run-scoped fetch
- simple admin download story
- keeps stage artifacts grouped without requiring new multi-table joins
- easier to evolve than six separate first-pass persistence features

### Why not one table per stage first

That would improve queryability, but it is too large a first move because it would:

- add more schema coordination
- add more partial-write complexity
- push us toward a broader storage redesign before the contracts are proven

So the first rollout should prefer:

- one bounded run-scoped JSON
- clearly separated stage blocks inside it

## Artifact Contract

### Top-Level Required Fields

- `run_id`
- `artifact_schema_version`
- `created_at`
- `snapshot_complete`
- `stages`

Optional but recommended:

- `stage_count`
- `captured_stage_count`
- `truncation_applied`

### Stage Block Contract

Each stage block should use this general shape:

```json
{
  "status": "captured",
  "summary": {...},
  "samples": [...],
  "counts": {...},
  "truncated": false,
  "error": null
}
```

Required per stage block:

- `status`
- `summary`
- `counts`
- `truncated`
- `error`

Optional:

- `samples`
- `output_refs`

Nullability rules:

- every declared stage key should exist
- if a stage was not reached, it should still be present with:
  - `status: "not_reached"`
  - empty or null content

That keeps the artifact interpretable when runs fail early.

## Stage-by-Stage Contract

### Normalize Artifact

Should capture:

- `counts.total_input_jobs`
- `counts.normalized_jobs`
- `counts.deduplicated_jobs`
- `counts.pre_enrichment_rejects`
- compact samples of:
  - normalized rows
  - dedupe reasons
  - pre-enrichment reject reasons

Should not capture:

- full raw job descriptions for every row by default

### Enrich Artifact

Should capture:

- `counts.enriched_jobs`
- candidate-profile source summary
- compact samples of enriched rows with key downstream fields only:
  - `job_url`
  - `title`
  - `required_skills`
  - `job_family`
  - `years_experience_min`
  - `years_experience_max`

Should not capture:

- the full candidate profile again if another run-scoped snapshot already stores it

### Rule Filter Artifact

Should capture:

- passed count
- rejected count
- grouped reject reasons
- compact samples of passed/rejected rows

### Shortlist Artifact

Should capture:

- raw vector hit count
- scoring shortlist count
- backfilled job count
- candidate query text or bounded query summary
- compact per-job shortlist transition samples:
  - `job_url`
  - `shortlist_status`
  - `vector_similarity`
  - `vector_rank`

### Ranking Artifact

Should capture:

- ranking input count
- ranked count
- active runtime ranking feature set
- compact samples of ranking inputs and ranked outputs:
  - `job_url`
  - `ai_score`
  - `vector_similarity`
  - `final_score`
  - `ranking_fit_label`
  - `fit_label_source`

Important:

- this stage owns the authoritative post-filter fit label
- the artifact must not imply that gap analysis is another primary fit owner

### CV Generation Artifact

Should capture:

- the existing bounded per-job CV-generation debug records
- preferably by embedding or referencing the same runtime-captured record shape already used by `cv_generation_debug_json`

First-rollout recommendation:

- keep the dedicated `cv_generation_debug_json`
- also include a small `cv_generation` stage block in the stage-artifacts JSON summarizing:
  - how many ranked jobs reached CV generation
  - how many were accepted
  - how many were skipped
  - how many failed validation
  - how many failed generation/persistence

This avoids duplicating the entire heavy Layer 4 payload twice.

## Boundedness Rules

This feature is only safe if the artifacts stay bounded.

### Phase 1 boundedness policy

- keep compact counts and summaries for all stages
- keep bounded samples rather than every row in full
- keep only the key fields needed to understand the handoff
- truncate large text fields before dropping records
- never trim:
  - `run_id`
  - stage names
  - counts
  - per-sample identifiers like `job_url`
  - stage status
  - error metadata

Preferred trimming order:

1. long text/debug strings
2. oversized sample payload fields
3. sample list length

Least preferred:

- dropping whole stage blocks

## No-Recomputation Rule

Every field in the stage artifact must be captured from the live runtime path at the moment that stage completed.

Not allowed:

- rebuilding normalize output later from final export rows
- recreating shortlist transitions from ranking outputs
- reconstructing stage counts from downstream tables after the fact

This artifact is valuable only if it reflects the real handoff, not a later approximation.

## Relationship To Existing Artifacts

## Relationship To Stage Contracts

The stage contracts and the stage transition artifacts should have different responsibilities:

- `docs/stages/*.yaml`
  - define stage identity, boundaries, inputs, outputs, and stage-to-feature relationships
- the stage transition artifact
  - captures the runtime handoff snapshot produced at that documented boundary

This spec should not redefine stage boundaries that already live in the stage contracts. It should reuse them.

### Existing run-results export

Keep it.

Purpose:

- user/admin-facing summary of overall run outcomes

Not its job:

- full stage-by-stage handoff inspection

### Existing CV-generation debug snapshot

Keep it.

Purpose:

- deep Layer 4 inspection

The new stage transition artifact should complement it, not replace it.

### Existing stage tables

Keep them as system-of-record or operational stores where they already exist.

The new artifact is a:

- debugging convenience surface
- run-scoped inspection snapshot

not a replacement canonical model for every stage fact.

## UI / Inspection Scope

First rollout should stay small.

Recommended UI scope:

- add one admin download action for the new stage transition artifact
- optionally add a minimal summary card in run detail showing:
  - stage blocks captured
  - whether the snapshot is complete

Do not make the first rollout a full in-page stage explorer.

## Acceptance Criteria

1. A completed run can persist a bounded run-scoped stage transition artifact with explicit blocks for:
   - normalize
   - enrich
   - rule_filter
   - shortlist
   - ranking
   - cv_generation

2. Each stage block is interpretable on its own and includes:
   - status
   - counts
   - compact summaries
   - bounded samples when available

3. The artifact makes it possible to determine, for a problem run:
   - what left normalize
   - what left rule filter
   - what raw retrieval returned
   - what advanced to scoring
   - what ranking used and selected
   - what happened at CV generation

4. Artifact fields are captured from the live runtime path and are not reconstructed later from final outputs.

5. The artifact stays bounded under normal runs through sample caps and truncation policy.

6. Existing run-results export and CV-generation debug snapshot remain supported and keep their current roles.

7. Partial runs remain interpretable:
   - unreached stage blocks are present
   - `snapshot_complete` explains whether the artifact is complete

## Recommended Next Step

Write an implementation plan that:

1. defines the exact runtime capture seam for each stage block
2. chooses the concrete persistence location for the run-scoped artifact
3. reuses existing CV debug capture where appropriate instead of duplicating Layer 4 payloads
4. adds bounded regression coverage for:
   - partial runs
   - truncation behavior
   - shortlist/ranking handoff visibility
