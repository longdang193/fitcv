---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md
targets:
  - docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md
  - docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md
  - docs/superpowers/execution_maps/2026-04-28-fitcv-first-wave-implementation-execution-map.md
  - docs/stages/ranking.source.yaml
  - docs/stages/ranking.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_analysis.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/stages/cv_generation.yaml
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/app.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - cv_system
  - inspection_debugging
  - trigger_run_management
related_stages:
  - ranking
  - cv_analysis
  - cv_generation
---

# FitCV Wave 1 Semantic Runtime Core Implementation Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `multiple`
- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md`
**Implementation Execution Map:** `docs/superpowers/execution_maps/2026-04-28-fitcv-first-wave-implementation-execution-map.md`  
**Type:** add  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Align late-stage runtime, export, and operator surfaces around one stage-owned vocabulary and one deterministic outcome model before any broader first-wave implementation begins.

**Architecture:** This plan first stabilizes stage-owned semantics in the runtime and stage docs, then applies deterministic outcome mapping across pipeline exports, stage-transition artifacts, worker persistence, and control-plane outcome surfaces. The code center of gravity is `src/fitcv/pipeline.py`, with bounded follow-on alignment in `src/fitcv/agentic_cv_analysis.py`, `src/fitcv_cp/worker_job.py`, and `src/fitcv_cp/app.py`.

**Key Invariants:**
- `ranking` remains the authority for post-filter fit labels.
- `cv_analysis` remains the authority for `blocked_by_reranker_fit`, `ready_for_generation`, `skipped_fit_gate`, and `analysis_failed`.
- `cv_generation` remains the authority for `accepted`, `validation_failed`, `generation_failed`, and `persistence_failed`.
- Pipeline-facing and operator-facing labels remain derived views over stage-owned truth.
- Checkpoint and continue semantics preserve stage-owned state instead of reinterpreting it.

**Rollout / Revert:**  
- rollback_trigger: stage-owned statuses, export rows, or run-detail labels diverge from existing accepted test expectations without a clear deterministic replacement  
- rollback_method: revert the Wave 1 runtime-truth patches together so pipeline status mapping, stage artifact summaries, and control-plane label logic move back in one bounded change

## Triage

Layer: `change`  
Feature type: `ADD`  
Summary: Implement the Wave 1 semantic and deterministic truth core across pipeline, worker, stage-doc, and control-plane surfaces.  
Reasoning:

- the approved detailed specs and implementation execution map already exist
- this is the first bounded implementation plan for the first buildable subset
- the work is stage-heavy and cross-cutting across runtime and operator surfaces

Invariants:

- stage-owned statuses stay canonical
- deterministic outcomes derive from stage-owned statuses
- UI and export labels remain secondary projections

Dependencies:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md`
- `docs/superpowers/execution_maps/2026-04-28-fitcv-first-wave-implementation-execution-map.md`

Affected stages:

- `ranking`
- `cv_analysis`
- `cv_generation`

Affected features:

- `cv_system`
- `inspection_debugging`
- `trigger_run_management`

Primary lens: `stage`

Affected docs:
  feature_source: `none`
  feature_yaml: `none`
  feature_lineage: `none`
  feature_history: `none`
  stage_source:
    - `docs/stages/ranking.source.yaml`
    - `docs/stages/cv_analysis.source.yaml`
    - `docs/stages/cv_generation.source.yaml`
  stage_contract:
    - `docs/stages/ranking.yaml`
    - `docs/stages/cv_analysis.yaml`
    - `docs/stages/cv_generation.yaml`
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

- `none`

Invariant IDs:

- `none`

Spec needed: `yes`  
Plan needed: `yes`

Rollback trigger:

- deterministic outcome mapping causes pipeline exports, stage-artifact summaries,
  or run-detail labels to disagree with tested stage-owned status behavior

Rollback method:

- revert all Wave 1 runtime-truth patches in one bounded change and restore the
  previous status-to-surface mapping until the contract is corrected

Migration needed: `no`  
Risk level: `medium`

## Doc Update Matrix

- Feature source: `none`
- Feature contract: `none`
- Feature lineage: `none`
- Stage source:
  - `docs/stages/ranking.source.yaml`
  - `docs/stages/cv_analysis.source.yaml`
  - `docs/stages/cv_generation.source.yaml`
- Stage contracts:
  - `docs/stages/ranking.yaml`
  - `docs/stages/cv_analysis.yaml`
  - `docs/stages/cv_generation.yaml`
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
- `src/fitcv/agentic_cv_analysis.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/worker_job.py`
- `docs/stages/ranking.source.yaml`
- `docs/stages/cv_analysis.source.yaml`
- `docs/stages/cv_generation.source.yaml`
- generated:
  - `docs/stages/ranking.yaml`
  - `docs/stages/cv_analysis.yaml`
  - `docs/stages/cv_generation.yaml`
  - `docs/generated/planning_lineage.yaml`

Tests to update:

- `tests/test_pipeline.py`
- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_worker_job.py`

Files to create:

- none

## Task 1: Lock Stage-Owned Status Semantics In Runtime Helpers

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv/pipeline.py`
  - `src/fitcv/agentic_cv_analysis.py`
- Test:
  - `tests/test_pipeline.py`
- Docs:
  - `docs/stages/ranking.source.yaml`
  - `docs/stages/cv_analysis.source.yaml`
  - `docs/stages/cv_generation.source.yaml`

- [ ] Step 1: Add or tighten failing runtime tests in `tests/test_pipeline.py` for:
  - ranking fit as upstream authority
  - `blocked_by_reranker_fit`
  - `ready_for_generation`
  - `skipped_fit_gate`
  - generation terminal statuses remaining stage-owned
- [ ] Step 2: Run the targeted failing tests:
  - `python -m pytest tests/test_pipeline.py -k "blocked_by_reranker_fit or skipped_fit_gate or ready_for_generation or stage_transition_artifacts"`
- [ ] Step 3: Update `src/fitcv/pipeline.py` and `src/fitcv/agentic_cv_analysis.py` so status helpers, decision-chain builders, and stage-transition summaries consistently reflect the stage-authority spec.
- [ ] Step 4: Re-run the targeted tests and confirm pass:
  - `python -m pytest tests/test_pipeline.py -k "blocked_by_reranker_fit or skipped_fit_gate or ready_for_generation or stage_transition_artifacts"`
- [ ] Step 5: Update the relevant stage source docs:
  - `docs/stages/ranking.source.yaml`
  - `docs/stages/cv_analysis.source.yaml`
  - `docs/stages/cv_generation.source.yaml`
- [ ] Step 6: Regenerate stage contracts with the canonical sync workflow:
  - `python scripts/sync_architecture_docs.py`
  - `python scripts/sync_architecture_docs.py --check`
- [ ] Step 7: Commit the bounded semantic-runtime-core change.

## Task 2: Apply Deterministic Outcome Mapping To Pipeline Exports And Artifacts

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv/pipeline.py`
  - `src/fitcv_cp/worker_job.py`
- Test:
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
- Docs:
  - `docs/stages/cv_analysis.source.yaml`
  - `docs/stages/cv_generation.source.yaml`

- [ ] Step 1: Add failing tests for deterministic outcome mapping in:
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
  covering:
  - export rows
  - stage-transition artifact summaries
  - worker-persisted artifact payloads
- [ ] Step 2: Run the targeted failing tests:
  - `python -m pytest tests/test_pipeline.py tests/test_fitcv_cp/test_worker_job.py -k "blocked_by_reranker_fit or skipped_fit_gate or validation_failed or persistence_failed"`
- [ ] Step 3: Update `src/fitcv/pipeline.py` so deterministic outcomes and preserved stage-owned subreasons are exposed consistently in export and artifact-building helpers.
- [ ] Step 4: Update `src/fitcv_cp/worker_job.py` so persisted run snapshots preserve the deterministic-outcome-aligned payload shape expected by the control plane.
- [ ] Step 5: Re-run the targeted tests and confirm pass:
  - `python -m pytest tests/test_pipeline.py tests/test_fitcv_cp/test_worker_job.py -k "blocked_by_reranker_fit or skipped_fit_gate or validation_failed or persistence_failed"`
- [ ] Step 6: Update stage-source wording if implementation tightened outcome-family wording in:
  - `docs/stages/cv_analysis.source.yaml`
  - `docs/stages/cv_generation.source.yaml`
- [ ] Step 7: Regenerate stage contracts with:
  - `python scripts/sync_architecture_docs.py`
  - `python scripts/sync_architecture_docs.py --check`
- [ ] Step 8: Commit the deterministic-outcome runtime and worker change.

## Task 3: Align Control-Plane Labels And Run-Detail Truth

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv_cp/app.py`
- Test:
  - `tests/test_fitcv_cp/test_app.py`
- Docs:
  - `docs/stages/ranking.source.yaml`
  - `docs/stages/cv_analysis.source.yaml`
  - `docs/stages/cv_generation.source.yaml`

- [ ] Step 1: Add failing control-plane tests in `tests/test_fitcv_cp/test_app.py` for:
  - outcome badges and labels
  - decision-chain label rendering
  - timeline summaries for blocked, skipped, validation-failed, and persistence-failed paths
  - artifact availability and stage-truth alignment where relevant
- [ ] Step 2: Run the targeted failing tests:
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "blocked_by_reranker_fit or skipped_fit_gate or validation_failed or persistence_failed or stage_artifacts"`
- [ ] Step 3: Update `src/fitcv_cp/app.py` so `PIPELINE_OUTCOME_META`, `DECISION_CHAIN_LABELS`, timeline summaries, stage quality surfaces, and run-detail projections remain faithful to the Wave 1 stage-owned and deterministic truth model.
- [ ] Step 4: Re-run the targeted tests and confirm pass:
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "blocked_by_reranker_fit or skipped_fit_gate or validation_failed or persistence_failed or stage_artifacts"`
- [ ] Step 5: Update stage-source wording only if operator-facing truth expectations require clearer stage-boundary prose in:
  - `docs/stages/ranking.source.yaml`
  - `docs/stages/cv_analysis.source.yaml`
  - `docs/stages/cv_generation.source.yaml`
- [ ] Step 6: Regenerate stage contracts with:
  - `python scripts/sync_architecture_docs.py`
  - `python scripts/sync_architecture_docs.py --check`
- [ ] Step 7: Commit the control-plane truth-alignment change.

## Task 4: Run End-To-End Validation And Refresh Generated Discovery

**Files:**
- Create: `none`
- Modify:
  - `docs/generated/planning_lineage.yaml`
  - generated stage contracts if changed
- Test:
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
- Docs:
  - exact entries from the Doc Update Matrix

- [ ] Step 1: Run the focused regression suite for the Wave 1 subset:
  - `python -m pytest tests/test_pipeline.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py`
- [ ] Step 2: If failures reveal cross-surface drift, make the smallest bounded fix in the owning runtime or control-plane file and re-run the affected tests.
- [ ] Step 3: Refresh generated discovery and managed-doc outputs:
  - `python scripts/generate_planning_lineage.py`
  - `python scripts/sync_architecture_docs.py`
  - `python scripts/sync_architecture_docs.py --check`
- [ ] Step 4: Run repo contract validation if the doc sync touched managed outputs:
  - `python scripts/validate_adoption_shape.py`
  - `python scripts/validate_repo_contracts.py --fast`
- [ ] Step 5: Confirm the worktree only contains intended Wave 1 changes plus any unrelated pre-existing files.
- [ ] Step 6: Commit the validation and generated-output refresh.

## Shared-Surface Risks

- `src/fitcv/pipeline.py`
  - too many status, export, and stage-artifact changes can drift together unless
    semantic authority lands before deterministic outcome cleanup
- `src/fitcv_cp/app.py`
  - operator-friendly labels can accidentally become a second truth system if
    they are updated before deterministic mapping is locked
- stage source and generated stage contracts
  - wording drift between runtime and stage docs will confuse later Wave 2 and
    Wave 3 work if not refreshed immediately

## Sequencing Notes

- finish runtime semantic authority before changing deterministic outcome
  projections
- finish deterministic outcome runtime mapping before changing control-plane
  label logic
- run the focused runtime and control-plane regression suites before broad doc
  validation so logic failures are easier to localize

## Acceptance Criteria

- stage-owned late-stage statuses are consistent across runtime helpers,
  stage-transition artifacts, and exports
- deterministic outcomes and preserved stage-owned subreasons are visible in the
  bounded Wave 1 surfaces
- control-plane run detail and timeline views remain faithful to runtime truth
- stage docs and generated stage contracts stay aligned with the implemented
  vocabulary

## Next Artifact

After this plan, the next plan should cover Wave 2 from the execution map:

- `agentic-observability-event-contract-spec`
- `operator-control-plane-run-detail-truth-spec`
