---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Enrich stage-transition artifacts with bounded pre-decision inputs, decision summaries, and post-decision outputs so each stage can be debugged without relying only on successful end results."
invariants:
  - "Richer stage artifacts must remain stage-scoped debugging surfaces rather than a new unified run-bundle export."
  - "Each stage artifact must capture live runtime context from that stage, not later reconstruction from final outputs."
  - "Every stage block must include enough input and output context to explain why rows changed state, not only what succeeded."
  - "Artifact growth must stay bounded with explicit sampling and truncation rules."
  - "Effective settings remain a separate run-scoped artifact and must not be duplicated wholesale into every stage block."
---

# Richer Stage Artifacts Design

## Affected Feature Contracts

- [`docs/features/inspection_debugging/inspection_debugging.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)
- [`docs/features/trigger_run_management/trigger_run_management.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/trigger_run_management/trigger_run_management.yaml)
- [`docs/features/cv_system/cv_system.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)

## Stage Contracts

- [`docs/stages/normalize.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/normalize.yaml)
- [`docs/stages/enrich.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/enrich.yaml)
- [`docs/stages/rule_filter.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/rule_filter.yaml)
- [`docs/stages/shortlist.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/shortlist.yaml)
- [`docs/stages/ranking.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/ranking.yaml)
- [`docs/stages/cv_generation.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/cv_generation.yaml)

## Triage

Feature type: MODIFY  
Summary: Enrich existing run-scoped stage-transition artifacts so each stage block captures bounded input, decision, and output context rather than only high-level successful results.  
Reasoning: Stage artifacts and timeline-linked downloads now exist, but several debugging failures still require inference because the artifact often shows only the output state that survived the stage. This is a direct extension of the existing inspection/debugging model, not a new artifact family and not a run-bundle design.  
Invariants:
- The richer artifact must continue using the existing stage-based model rather than introducing `run-bundle.json`.
- Each stage block must expose enough pre-decision and post-decision context to explain why jobs changed state.
- Sampled rows and heavy text fields must stay bounded by explicit limits.
- The dedicated `settings_used.json` remains the single full-settings surface for the run.
- `cv_generation` may be richer than other stages, but the other stage blocks must still become meaningfully diagnostic.
Dependencies:
- `inspection_debugging`
- `trigger_run_management`
- `cv_system`
- existing stage-transition artifact persistence
- existing settings-used snapshot
- existing timeline-linked stage-download routes
Affected stages:
- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_generation`
Affected features:
- `inspection_debugging`
- `trigger_run_management`
- `cv_system`
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
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
    - `docs/features/trigger_run_management/trigger_run_management.yaml`
    - `docs/features/cv_system/cv_system.yaml`
  feature_history:
    - `docs/features/inspection_debugging/history.md`
    - `docs/features/trigger_run_management/history.md`
    - `docs/features/cv_system/history.md`
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

## Why This Follow-Up Exists

The current stage-artifact rollout solved persistence and downloadability, but it still leaves a key debugging gap:

- artifacts can show what a stage produced
- without showing enough of what the stage received, changed, or dropped

That means an operator can still end up seeing only the working result rather than the problem.

Examples:

- `shortlist` may show the scoring shortlist, but without enough passed-job input sample it is harder to see why an eligible job missed raw retrieval
- `ranking` may show top-ranked jobs, but without enough scored-not-ranked context it is harder to see why a job disappeared before the final cut
- `rule_filter` may show reject counts, but without passed and rejected examples it is harder to validate whether deterministic rules are overfiring
- `cv_generation` is already the richest stage, but it still sits beside a separate CV debug surface that partially overlaps it

So the problem is no longer “there is no artifact.” The problem is:

- the artifacts are still too result-heavy and too transition-light

## Problem Statement

The current stage-transition artifacts are useful, but not yet sufficient for full stage-by-stage debugging because they do not consistently preserve:

1. enough pre-decision input context
2. enough change-state context
3. enough representative examples of rows that were dropped, rejected, skipped, or backfilled

This creates a failure mode where the artifact only confirms the stage’s successful output rather than explaining the stage’s actual transformation.

The missing capability is:

- every stage block should capture a bounded, structured picture of:
  - what came in
  - what settings mattered
  - what decisions were applied
  - what changed state
  - what went out

## Design Goal

Upgrade the existing stage-transition artifact model so each stage block becomes a bounded debugging contract for that stage’s transition, not just a summary of its final output.

This rollout should:

- keep the current run-scoped `stage-artifacts.json`
- enrich each stage block with both input-side and output-side context
- preserve `settings-used.json` as the separate full-settings artifact
- avoid introducing `run-bundle.json`
- keep per-stage downloads and timeline-linked downloads working against the same persisted artifact

## Non-Goal

This spec does **not** introduce:

- `run-bundle.json`
- a new all-payloads export combining every artifact in one file
- an in-page artifact viewer
- unbounded full row dumps for every stage

Those may be discussed later, but they are intentionally out of scope here.

## Proposed Artifact Enrichment Model

Keep the existing top-level run-scoped stage-artifacts JSON, but enrich the shape of each `stages.<stage_id>` block.

Recommended per-stage contract:

```json
{
  "stage_id": "shortlist",
  "status": "completed",
  "input_counts": { "...": 0 },
  "output_counts": { "...": 0 },
  "settings_refs": ["pipeline.vector_search_top_n"],
  "decision_summary": { "...": "..." },
  "inputs_sample": [],
  "outputs_sample": [],
  "dropped_or_changed_sample": [],
  "notes": []
}
```

### Required Stage Block Concepts

Every reachable stage block should provide:

- `stage_id`
- `status`
- `input_counts`
- `output_counts`
- `decision_summary`
- `inputs_sample`
- `outputs_sample`
- `dropped_or_changed_sample`

Optional but recommended:

- `settings_refs`
- `notes`
- `warnings`
- `errors`

Nullability rule:

- required keys should exist even when empty
- use empty arrays / empty objects rather than omitting the field
- unreachable later stages may still use the existing `not_reached` status with minimal empty structures

## Sampling and Boundedness Policy

### Default sample limit

Use a first-rollout default:

- `sample_limit = 20`

This should apply to row-oriented samples such as:

- `inputs_sample`
- `outputs_sample`
- `dropped_or_changed_sample`

### Truncation policy

Heavy fields should remain bounded.

Preferred order:

1. keep identifiers, statuses, reasons, and compact summaries intact
2. truncate long free-text fields
3. trim oversized nested text payloads before dropping rows
4. only reduce the sample row count if necessary after field truncation

Examples of fields that may need truncation:

- long cleaned job descriptions
- large markdown CV outputs
- oversized evidence text snippets

## Stage-by-Stage Guidance

### Normalize

Should capture:

- raw input count
- normalized count
- deduplicated count
- pre-enrichment rejected count
- sample raw/normalized job identifiers
- dedupe summary and sample removed rows

Recommended samples:

- `inputs_sample`: raw input job identifiers with title/company/url where available
- `outputs_sample`: normalized surviving jobs
- `dropped_or_changed_sample`: deduplicated and malformed rows

### Enrich

Should capture:

- jobs entering enrichment
- successfully enriched jobs
- candidate profile snapshot summary actually used downstream
- sample enriched rows with canonical downstream fields

Recommended samples:

- `inputs_sample`: jobs entering enrichment
- `outputs_sample`: enriched rows with title, seniority, family, required skills, years fields
- `dropped_or_changed_sample`: jobs that failed enrichment or were not enriched

### Rule Filter

Should capture:

- enriched input count
- passed count
- rejected count
- grouped reject reasons
- sample passed and rejected rows

Recommended samples:

- `inputs_sample`: jobs entering rule filter
- `outputs_sample`: passed rows
- `dropped_or_changed_sample`: rejected rows with reject reasons

### Shortlist

Should capture:

- passed input count
- raw vector-hit count
- scoring shortlist count
- backfilled count
- candidate query summary
- jobs not returned by vector search

Recommended samples:

- `inputs_sample`: passed jobs entering retrieval
- `outputs_sample`: scoring shortlist rows with similarity, rank, origin
- `dropped_or_changed_sample`: jobs missed by raw retrieval and jobs later backfilled

### Ranking

Should capture:

- scoring-input count
- ranked count
- authoritative `ranking_fit_label` distribution
- active weights and defaults summary
- sample ranked and scored-not-ranked rows

Recommended samples:

- `inputs_sample`: scoring inputs with active ranking fields
- `outputs_sample`: ranked rows with scores and primary fit label
- `dropped_or_changed_sample`: scored-but-not-ranked rows

### CV Generation

This stage may be richer than the others.

It should capture:

- ranked input count
- attempted, accepted, skipped, failed counts
- decision-chain context
- evidence used
- gap explanation
- validation state
- repair metadata
- final artifact status

Recommended samples:

- `inputs_sample`: ranked rows entering CV generation
- `outputs_sample`: accepted/generated CV records
- `dropped_or_changed_sample`: skipped, validation-failed, or generation-failed rows

## Relationship to CV Debug JSON

This rollout should not immediately remove `cv-debug.json`, but it should move the system toward convergence.

Recommended direction:

- keep `cv-debug.json` for compatibility in this rollout
- enrich `stages.cv_generation` so it can cover the same debugging needs over time
- treat `cv_generation` as the canonical rich stage block in future follow-up work

That keeps the current admin workflow stable while reducing long-term overlap.

## Relationship to Settings Used JSON

The dedicated run-scoped settings snapshot remains the single full-settings artifact for the run.

Stage artifacts should therefore:

- reference the stage-relevant setting keys via `settings_refs`
- include compact stage-local settings summaries only when necessary
- avoid embedding the full effective settings object into each stage block

This keeps artifacts useful without repeating the same full config payload six times.

## UI and Download Model

The current download-first model should stay intact.

This rollout should continue to support:

- `Download Settings Used JSON`
- `Download Stage Artifacts JSON`
- per-stage JSON downloads from the timeline

No new viewer is required.

The improvement is in artifact content quality, not in adding a new inspection surface.

## Operational Rules

### No recomputation

Every enriched field in a stage block must be captured from the live stage path where it existed.

Not allowed:

- reconstructing stage samples later from final results export
- rebuilding stage-local changed-state rows from a later stage artifact
- inferring dropped rows only from the final surviving set

### Visibility does not imply authority

Richer stage artifacts may expose:

- inputs
- outputs
- rejects
- skipped rows
- diagnostic summaries

without changing which stage is authoritative for downstream decisions.

### Partial run behavior

If a run aborts early:

- reached stages should still preserve the richer structure
- later stages should remain `not_reached`
- partial artifacts should still be interpretable from the persisted run-scoped JSON

## Acceptance Criteria

This design is successful when:

1. each major stage artifact contains enough bounded context to explain both successful outputs and representative rows that changed state
2. default row-oriented samples are capped at 20 unless a smaller stage-specific cap is justified
3. the richer artifacts do not introduce `run-bundle.json` or a second all-in-one export surface
4. the full effective run settings remain available once via `settings-used.json`, not duplicated into each stage block
5. stage-specific downloads and the combined stage-artifacts download continue to work against one persisted run-scoped artifact
6. `cv_generation` may remain the richest stage, but `normalize`, `enrich`, `rule_filter`, `shortlist`, and `ranking` all become materially more diagnostic than simple output summaries
7. an operator can inspect a failed or confusing run and see not only what each stage produced, but also representative examples of what the stage received and what it changed

## Recommended Follow-Up Plan Scope

The implementation plan should focus on:

1. defining the richer per-stage JSON contract precisely
2. enriching live stage capture in `pipeline.py`
3. preserving boundedness and truncation rules
4. updating stage-download routes only as needed to reflect the richer schema
5. updating feature contracts and stage contracts to describe the richer artifact semantics

The implementation plan should explicitly defer:

- `run-bundle.json`
- artifact viewer UX
- full CV debug deprecation
