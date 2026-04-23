---
layer: change
artifact_type: plan
status: completed
completed_at: 2026-04-23T11:19:53+02:00
change_id: 2026-04-23-run-lifecycle-stage-participation
affects:
  capabilities:
    - run_lifecycle_controls.cooperative-cancellation-at-safe-checkpoints-for-running-jobs
    - run_lifecycle_controls.direct-cancellation-of-paused-manual-runs-in-awaiting-continue
    - run_lifecycle_controls.stale-cancellation-repair-endpoint
    - run_lifecycle_controls.state-aware-max-runtime-timeout-handling-for-queued-running-cancelling-and-paused-manual-runs
    - run_lifecycle_controls.timeout-copy-now-distinguishes-queue-wait-active-runtime-and-stage-by-stage-manual-wait-time
    - run_lifecycle_controls.full-audit-trail-in-pipeline-run-events
verification:
  - python scripts/sync_architecture_docs.py --check
  - python scripts/validate_adoption_shape.py
  - python scripts/validate_repo_contracts.py --fast
outcome:
  summary: Run lifecycle controls now declare supporting stage participation across runtime stages.
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

# Run Lifecycle Stage Participation Implementation Plan

**Feature Source:** `docs/features/run_lifecycle_controls/feature.source.yaml`
**Feature Contract:** `docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml`
**Spec:** `docs/superpowers/specs/2026-04-23-02-05-run-lifecycle-stage-participation-spec.md`
**Type:** modify
**Plan Layer:** change
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` to implement task-by-task.

**Goal:** Replace empty `run_lifecycle_controls` stage participation with truthful supporting stage participation across runtime stages.

**Architecture:** The human-owned feature source is the canonical stage-participation source. The architecture sync script regenerates feature contracts, lineage, stage contracts, and aggregate discovery from that source.

**Key Invariants:**
- Product code and behavior do not change.
- `run_lifecycle_controls` remains supporting, not primary, for runtime stages.
- Queue-only and terminal archive/unarchive capabilities stay outside stage participation.
- Generated architecture files are refreshed only through `scripts/sync_architecture_docs.py`.

**Rollout / Revert:**
- rollback_trigger: generated contracts fail validation or overstate stage ownership
- rollback_method: restore `stage_participation: []`, rerun `python scripts/sync_architecture_docs.py`, and re-run validators

---

## Triage

Layer: change
Feature type: MODIFY
Summary: Backfill stage participation metadata for lifecycle controls.
Reasoning: The feature source currently under-reports runtime-stage support.
Invariants:
- lifecycle controls are supporting stage behavior only
- generated files are not hand-edited
Dependencies:
- `scripts/sync_architecture_docs.py`
Affected stages:
- normalize
- enrich
- rule_filter
- shortlist
- ranking
- cv_analysis
- cv_generation
Affected features:
- run_lifecycle_controls
Primary lens: mixed
Affected docs:
- feature_source: `docs/features/run_lifecycle_controls/feature.source.yaml`
- feature_yaml: `docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml`
- feature_lineage: `docs/features/run_lifecycle_controls/lineage.generated.yaml`
- feature_history: none
- stage_source: none
- stage_contract: `docs/stages/*.yaml`
- feature_docs: none
- cross_cutting_docs: none
- readme: none
- generated:
  - `docs/generated/architecture_dag.yaml`
  - `docs/generated/capability_lineage.yaml`
Generated refresh required: yes
Capability IDs:
- `run_lifecycle_controls.cooperative-cancellation-at-safe-checkpoints-for-running-jobs`
- `run_lifecycle_controls.direct-cancellation-of-paused-manual-runs-in-awaiting-continue`
- `run_lifecycle_controls.stale-cancellation-repair-endpoint`
- `run_lifecycle_controls.state-aware-max-runtime-timeout-handling-for-queued-running-cancelling-and-paused-manual-runs`
- `run_lifecycle_controls.timeout-copy-now-distinguishes-queue-wait-active-runtime-and-stage-by-stage-manual-wait-time`
- `run_lifecycle_controls.full-audit-trail-in-pipeline-run-events`
Invariant IDs:
- none
Spec needed: yes
Plan needed: yes
Risk level: low

## Doc Update Matrix

- Feature source: `docs/features/run_lifecycle_controls/feature.source.yaml`
- Feature contract: `docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml`
- Feature lineage: `docs/features/run_lifecycle_controls/lineage.generated.yaml`
- Stage source: none
- Stage contracts: `docs/stages/*.yaml`
- Feature history: none
- Feature-specific docs: none
- Cross-cutting docs: none
- Operating-system docs: none
- README: none
- Generated discovery: `docs/generated/architecture_dag.yaml`, `docs/generated/capability_lineage.yaml`

## Task 1: Backfill Feature Source Stage Participation

**Files:**
- Modify: `docs/features/run_lifecycle_controls/feature.source.yaml`

- [x] Step 1: Replace `stage_participation: []` with supporting entries for all seven runtime stages.
- [x] Step 2: Include only the lifecycle capabilities that affect running, paused, timed-out, repaired, or audited stage execution.
- [x] Step 3: Confirm queue-only and terminal archive/unarchive capabilities are not included.

## Task 2: Regenerate And Validate Architecture Outputs

**Files:**
- Generated: `docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml`
- Generated: `docs/features/run_lifecycle_controls/lineage.generated.yaml`
- Generated: `docs/stages/*.yaml`
- Generated: `docs/generated/architecture_dag.yaml`
- Generated: `docs/generated/capability_lineage.yaml`

- [x] Step 1: Run `python scripts/sync_architecture_docs.py`.
- [x] Step 2: Run `python scripts/sync_architecture_docs.py --check`.
- [x] Step 3: Run `python scripts/validate_adoption_shape.py`.
- [x] Step 4: Run `python scripts/validate_repo_contracts.py --fast`.
- [x] Step 5: Run `git diff --check`.
- [x] Step 6: Review the diff to confirm no product-code changes occurred.

## Completion Checklist

- intent docs updated? no
- operating-system docs updated? no
- stage sources updated? no
- stage contracts updated? yes, if regenerated
- feature sources updated? yes
- contract updated? yes, generated
- feature lineage updated? yes, if regenerated
- feature history updated? no
- other feature-specific docs updated? no
- cross-cutting docs updated? no
- agent memory updated or explicitly not needed? not needed
- README updated? no
- generated docs refreshed? yes
