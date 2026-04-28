---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-operator-surface
parent_spec: docs/superpowers/specs/2026-04-28-agentic-run-mode-and-synonym-proposal-observability-spec.md
targets:
  - docs/superpowers/specs/2026-04-28-agentic-run-mode-and-synonym-proposal-observability-spec.md
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/models.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_bq_store.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - inspection_debugging
  - trigger_run_management
  - cv_system
related_stages:
  - cv_analysis
  - cv_generation
---

# Agentic Run Mode And Synonym Proposal Observability Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/specs/2026-04-28-agentic-run-mode-and-synonym-proposal-observability-spec.md`  
**Implementation Execution Map:** `none`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Make late-stage agentic mode and synonym-proposal persistence explicit in exported run artifacts so operators can tell whether a run was non-agentic, agentic, degraded, or missing expected artifacts without inferring from absence.

**Architecture:** The runtime truth starts in `src/fitcv/pipeline.py`, where late-stage mode is resolved and stage artifacts are assembled, then flows through `src/fitcv_cp/worker_job.py` into run-owned snapshots and synonym proposal payloads. The control-plane and bundle surface in `src/fitcv_cp/app.py` should expose that truth through `results.json`, `settings-used.json`, stage artifact downloads, and `manifest.json`, while `src/fitcv_cp/bq_store.py` remains the durable-store seam that can degrade cleanly when the live BigQuery schema is behind.

**Key Invariants:**
- non-agentic runs must say they are non-agentic instead of looking incomplete
- optional agentic artifacts must distinguish `not_applicable`, `present`, `missing`, and `degraded`
- synonym proposal visibility must survive BigQuery column drift through run-scoped artifact fallback
- control-plane downloads and bundle manifest entries must stay aligned with actual artifact availability

**Rollout / Revert:**  
- rollback_trigger: run bundles or run-detail downloads start claiming agentic artifacts exist when they do not, or persistence degradation is misreported as a business-path failure  
- rollback_method: revert the bounded runtime, bundle, and persistence patch set together so mode truth and artifact-state vocabulary return to the prior consistent behavior

## Triage

Layer: `change`  
Feature type: `MODIFY`  
Summary: Implement explicit late-stage mode truth, bounded synonym-proposal bundle artifacts, and degraded persistence reporting across pipeline, worker, bundle, and control-plane surfaces.  
Reasoning:

- the design is already settled by the new detailed spec
- the work is cross-cutting across runtime and operator surfaces, with no single feature source owning the full slice
- implementation needs a dedicated plan because it touches snapshot generation, artifact bundling, persistence degradation, and multiple test suites

Invariants:

- visible artifacts must encode agentic applicability explicitly
- durable-store failures must not erase run-scoped operator evidence
- manifest and artifact downloads must reflect the same artifact-state contract

Dependencies:

- `docs/intent/workstreams/threads/workstream-agentic-observability/02-agentic-observability-operator-surface.md`
- `docs/intent/workstreams/threads/workstream-agentic-synonym-management/03-agentic-synonym-review-queue-and-approval.md`
- `docs/superpowers/specs/2026-04-28-agentic-run-mode-and-synonym-proposal-observability-spec.md`
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/worker_job.py`
- `src/fitcv_cp/bq_store.py`
- `src/fitcv_cp/app.py`

Affected stages:

- `cv_analysis`
- `cv_generation`

Affected features:

- `inspection_debugging`
- `trigger_run_management`
- `cv_system`

Primary lens: `mixed`

Affected docs:
  feature_source: `none`
  feature_yaml: `none`
  feature_lineage: `none`
  feature_history: `none`
  stage_source: `none`
  stage_contract: `none`
  feature_docs:
    - `none`
  cross_cutting_docs:
    - `none`
  operating_system_docs:
    - `none`
  readme: `none`
  generated:
    - `docs/generated/planning_lineage.yaml`

Generated refresh required: `yes`
Capability IDs:

- `inspection_debugging.run-owned-artifact-exports`
- `inspection_debugging.stage-artifact-downloads`
- `inspection_debugging.settings-used-export`
- `inspection_debugging.results-ledger-inspection`
- `inspection_debugging.cv-analysis-diagnostics`
- `inspection_debugging.cv-generation-diagnostics`
- `trigger_run_management.run-owned-artifact-exports`
- `trigger_run_management.stage-artifact-downloads`
- `trigger_run_management.run-results-export`
- `trigger_run_management.decision-chain-outcomes`
- `cv_system.stage-artifact-diagnostics`

Invariant IDs:

- `none`

Spec needed: `yes`  
Plan needed: `yes`

Rollback trigger:

- exports or bundles misclassify non-agentic runs as degraded, or synonym-proposal degradation hides otherwise successful late-stage outcomes

Rollback method:

- revert the runtime mode-truth helpers, bundle contract changes, and persistence-status patch as one slice

Migration needed: `no`  
Risk level: `medium`

## Doc Update Matrix

- Feature source: `none`
- Feature contract: `none`
- Feature lineage: `none`
- Stage source: `none`
- Stage contracts: `none`
- Feature history: `none`
- Feature-specific docs: `none`
- Cross-cutting docs: `none`
- Operating-system docs: `none`
- README: `none`
- Generated discovery:
  - `docs/generated/planning_lineage.yaml`

## File Structure First

Files to modify:

- `src/fitcv/pipeline.py`
- `src/fitcv_cp/worker_job.py`
- `src/fitcv_cp/bq_store.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/models.py` only if the artifact-state payload needs a model-level field or helper
- generated:
  - `docs/generated/planning_lineage.yaml`

Tests to update:

- `tests/test_pipeline_agentic_late_stage.py`
- `tests/test_fitcv_cp/test_worker_job.py`
- `tests/test_fitcv_cp/test_bq_store.py`
- `tests/test_fitcv_cp/test_app.py`

Files to create:

- `docs/superpowers/plans/2026-04-28-agentic-run-mode-and-synonym-proposal-observability-plan.md`

## Task 1: Add Failing Runtime And Snapshot Tests For Mode Truth

**Files:**
- Create: `none`
- Modify:
  - `tests/test_pipeline_agentic_late_stage.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
- Test:
  - `tests/test_pipeline_agentic_late_stage.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
- Docs:
  - `none`

- [ ] Step 1: Add failing pipeline tests that prove:
  - non-agentic late-stage runs expose explicit mode truth instead of silent omission
  - agentic late-stage runs expose explicit mode truth when `cv.agentic_late_stage.enabled` is true
  - `cv_analysis` and `cv_generation` stage payloads carry bounded mode metadata when the stage is reached
- [ ] Step 2: Add failing worker snapshot tests that prove:
  - `settings-used` and results snapshot builders include the late-stage mode summary
  - synonym proposal payloads can encode `not_applicable`, `not_attempted`, `persisted`, `bundle_only_degraded`, and `failed`
  - degraded synonym persistence can still retain a run-scoped payload that is bundle-safe
- [ ] Step 3: Run the targeted failing tests:
  - `python -m pytest tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_worker_job.py`
- [ ] Step 4: Commit the failing-test baseline once the intended failures are confirmed.

## Task 2: Inject Late-Stage Mode Truth Into Runtime And Snapshot Builders

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv/pipeline.py`
  - `src/fitcv_cp/worker_job.py`
- Test:
  - `tests/test_pipeline_agentic_late_stage.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
- Docs:
  - `none`

- [ ] Step 1: Add or refactor a small bounded helper in `src/fitcv/pipeline.py` so late-stage mode truth is derived once from resolved runtime config and stage reachability rather than rebuilt ad hoc in each stage payload.
- [ ] Step 2: Update the `cv_analysis` and `cv_generation` artifact assembly paths in `src/fitcv/pipeline.py` so reached stages include:
  - `late_stage_mode`
  - `agentic_late_stage_enabled`
  - `mode_source`
  - `agentic_status`
- [ ] Step 3: Update `src/fitcv_cp/worker_job.py` snapshot builders so:
  - `settings-used.json` preserves the resolved late-stage mode truth
  - compact results exports include a bounded projection of the same mode truth
  - synonym proposal payload builders can carry bounded persistence state and degradation reason fields without leaking raw storage exceptions into the operator surface
- [ ] Step 4: Re-run the targeted tests and confirm pass:
  - `python -m pytest tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_worker_job.py`
- [ ] Step 5: Commit the runtime and snapshot mode-truth implementation.

## Task 3: Add Failing Bundle, Download, And Persistence-Degradation Tests

**Files:**
- Create: `none`
- Modify:
  - `tests/test_fitcv_cp/test_bq_store.py`
  - `tests/test_fitcv_cp/test_app.py`
- Test:
  - `tests/test_fitcv_cp/test_bq_store.py`
  - `tests/test_fitcv_cp/test_app.py`
- Docs:
  - `none`

- [ ] Step 1: Add failing storage tests that prove missing `synonym_proposals_json` column behavior is surfaced as degraded persistence state instead of silent success.
- [ ] Step 2: Add failing control-plane and artifact-bundle tests that prove:
  - `manifest.json` records late-stage mode truth
  - optional agentic artifacts expose `present`, `not_applicable`, `missing`, or `degraded`
  - `synonym-proposals.json` is included when proposal generation is applicable
  - non-agentic runs show explicit non-agentic truth in the bundle rather than just missing agentic sections
- [ ] Step 3: Run the targeted failing tests:
  - `python -m pytest tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_app.py -k "synonym or manifest or bundle or settings_used"`
- [ ] Step 4: Commit the failing control-plane and persistence-degradation test baseline once the intended failures are confirmed.

## Task 4: Implement Bundle Manifest And Persistence-Degradation Contract

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv_cp/bq_store.py`
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/models.py` if the run record or helper payload needs a stable typed accessor
  - `src/fitcv_cp/worker_job.py` if final persistence-status fields need last-mile assembly there
- Test:
  - `tests/test_fitcv_cp/test_bq_store.py`
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
- Docs:
  - `none`

- [ ] Step 1: Update `src/fitcv_cp/bq_store.py` so missing-column handling stays non-fatal but produces a status that downstream surfaces can map to `bundle_only_degraded` rather than treating the write as fully successful.
- [ ] Step 2: Update `src/fitcv_cp/app.py` bundle generation and artifact helpers so:
  - `BUNDLE_ARTIFACT_FILENAMES` and manifest assembly support `synonym-proposals.json`
  - `manifest.json` includes run-level mode truth and per-artifact state summaries
  - bundle inclusion rules distinguish `not_applicable` from `missing`
  - stage artifact download and bundle logic remain aligned on the same availability contract
- [ ] Step 3: Add any minimal helper in `src/fitcv_cp/app.py` or `src/fitcv_cp/models.py` needed to load run-scoped synonym proposal payloads and expose degradation metadata safely.
- [ ] Step 4: Re-run the focused tests and confirm pass:
  - `python -m pytest tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -k "synonym or manifest or bundle or settings_used"`
- [ ] Step 5: Commit the bundle manifest and persistence-degradation implementation.

## Task 5: Run End-To-End Validation And Refresh Discovery

**Files:**
- Create: `none`
- Modify:
  - `docs/generated/planning_lineage.yaml`
- Test:
  - `tests/test_pipeline_agentic_late_stage.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
  - `tests/test_fitcv_cp/test_bq_store.py`
  - `tests/test_fitcv_cp/test_app.py`
- Docs:
  - exact entries from the Doc Update Matrix

- [ ] Step 1: Run the focused regression suite for this slice:
  - `python -m pytest tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_app.py`
- [ ] Step 2: If failures expose cross-surface drift, fix the smallest owning runtime or control-plane seam and re-run the affected tests before broad validation.
- [ ] Step 3: Refresh generated discovery:
  - `python scripts/generate_planning_lineage.py`
- [ ] Step 4: Run managed-doc validation and capture whether pre-existing stale generated feature contracts still block a fully green pass:
  - `python scripts/sync_architecture_docs.py --check`
  - `python scripts/validate_repo_contracts.py --fast`
- [ ] Step 5: Confirm the worktree only contains intended observability-plan execution changes plus unrelated pre-existing files.
- [ ] Step 6: Commit the final validation and planning-lineage refresh.

## Shared-Surface Risks

- `src/fitcv/pipeline.py`
  - late-stage mode helpers can sprawl into another status system if the implementation duplicates outcome logic instead of only reporting agentic applicability and status
- `src/fitcv_cp/worker_job.py`
  - snapshot-building logic can diverge between `settings-used`, results exports, and synonym proposal payloads if one shared mode-truth vocabulary is not reused
- `src/fitcv_cp/app.py`
  - bundle inclusion logic can silently drift from manifest state reporting unless both are derived from the same artifact-state helper
- `src/fitcv_cp/bq_store.py`
  - fallback handling must stay bounded and non-fatal; storage-layer exceptions should not become the operator-facing schema

## Sequencing Notes

- land runtime mode truth before bundle-surface assertions, so manifest and export tests can rely on stable upstream fields
- keep BigQuery degradation handling bounded to status mapping and fallback preservation, not a broad storage refactor
- treat `synonym-proposals.json` as a run-scoped truth surface first and a review-queue precursor second

## Acceptance Criteria

- a non-agentic run artifact bundle explicitly says the late-stage path was non-agentic
- an agentic run artifact bundle explicitly says the late-stage path was agentic and whether expected agentic artifacts are present
- `synonym-proposals.json` is available whenever the synonym proposal flow is applicable or degraded with bundle-visible fallback
- missing `synonym_proposals_json` BigQuery schema support becomes `bundle_only_degraded` instead of silent ambiguity
- `settings-used.json`, `results.json`, stage artifact downloads, and `manifest.json` tell the same late-stage mode truth story

## Next Artifact

After this plan is approved or executed, the likely next bounded artifact is a follow-on plan for the synonym review queue only if the proposal-engine and artifact-truth surfaces still need separate product work beyond this observability slice.
