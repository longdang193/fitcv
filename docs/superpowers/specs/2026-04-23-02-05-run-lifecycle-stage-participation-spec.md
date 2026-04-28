---
layer: operating_system
artifact_type: spec
status: proposed
parent_workstream: none
targets:
  - docs/features/run_lifecycle_controls/feature.source.yaml
  - docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml
  - docs/features/run_lifecycle_controls/lineage.generated.yaml
  - docs/stages/*.yaml
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
related_features:
  - run_lifecycle_controls
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Run Lifecycle Stage Participation Metadata

## Summary

Backfill truthful stage participation for `run_lifecycle_controls` so the
managed architecture metadata reflects that lifecycle controls support runtime
stage execution without incorrectly making the feature a primary owner of any
pipeline stage.

This is a metadata correction phase. It should not change product behavior,
runtime logic, templates, or tests.

## Problem

`docs/features/run_lifecycle_controls/feature.source.yaml` currently has:

```yaml
stage_participation: []
```

That made the feature look completely stage-disconnected even though several
capabilities directly affect how runs behave while stages execute or pause
between stages:

- cooperative cancellation at safe checkpoints
- direct cancellation of paused `awaiting_continue` runs
- stale cancellation repair
- state-aware max-runtime timeout handling
- timeout copy that distinguishes queue wait, active runtime, and manual wait
- full audit trail in `pipeline_run_events`

The empty list is therefore too weak. At the same time, the feature should not
be promoted to a primary stage owner because stage business logic remains owned
by the actual pipeline features and stages.

## Goals

- Replace empty stage participation with supporting participation across the
  seven runtime stages.
- Include only lifecycle capabilities that truthfully apply to stage execution
  or stage-by-stage pauses.
- Leave pre-stage queue cancellation and terminal archive/unarchive capabilities
  out of stage participation unless a later phase introduces a non-stage
  lifecycle surface.
- Regenerate managed feature/stage/generated discovery outputs from source.
- Keep `admin_control_plane_core` and `ui_consistency_theming` unchanged; their
  empty stage participation remains intentional for now.

## Non-Goals

- Do not change run lifecycle code, routes, tests, or UI behavior.
- Do not add stage participation to every capability just to avoid an empty
  list.
- Do not edit generated feature contracts, stage contracts, lineage, or
  discovery files manually.
- Do not change stage source ownership lists unless the generated view proves
  feature-source participation is insufficient.

## Target State

`run_lifecycle_controls` participates as a supporting feature in:

- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`

Each entry should include these capability IDs:

- `run_lifecycle_controls.cooperative-cancellation-at-safe-checkpoints-for-running-jobs`
- `run_lifecycle_controls.direct-cancellation-of-paused-manual-runs-in-awaiting-continue`
- `run_lifecycle_controls.stale-cancellation-repair-endpoint`
- `run_lifecycle_controls.state-aware-max-runtime-timeout-handling-for-queued-running-cancelling-and-paused-manual-runs`
- `run_lifecycle_controls.timeout-copy-now-distinguishes-queue-wait-active-runtime-and-stage-by-stage-manual-wait-time`
- `run_lifecycle_controls.full-audit-trail-in-pipeline-run-events`

Excluded from stage participation for this phase:

- `run_lifecycle_controls.cancel-queued-runs-directly-from-the-queue-via-rq`
- `run_lifecycle_controls.archive-and-unarchive-terminal-runs`
- `run_lifecycle_controls.batch-cancel-archive-and-unarchive-endpoints-with-explicit-processed-skipped-summaries`

## Acceptance Criteria

- `docs/features/run_lifecycle_controls/feature.source.yaml` no longer has
  `stage_participation: []`.
- Generated `docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml`
  carries the same supporting stage participation.
- Generated stage contracts include `run_lifecycle_controls` as a supporting
  feature reference where the generator derives stage refs from feature
  participation.
- No product code changes are made.
- The following pass:
  - `python scripts/sync_architecture_docs.py`
  - `python scripts/sync_architecture_docs.py --check`
  - `python scripts/validate_adoption_shape.py`
  - `python scripts/validate_repo_contracts.py --fast`
  - `git diff --check`

## Risks

- Mapping too many capabilities to every stage could dilute stage ownership.
  This spec limits the mapping to capabilities that affect running, pausing,
  timing out, repairing, or auditing stage execution.
- Generated stage contracts may still omit related feature refs if the generator
  only uses stage source files for that view. If so, the feature source remains
  the canonical participation truth and a separate generator patch should be
  considered later.
