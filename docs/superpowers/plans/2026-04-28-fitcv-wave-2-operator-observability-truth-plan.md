---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-event-contract
parent_spec: docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md
targets:
  - docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md
  - docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md
  - docs/superpowers/execution_maps/2026-04-28-fitcv-first-wave-implementation-execution-map.md
  - src/fitcv/pipeline.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/app.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - inspection_debugging
  - trigger_run_management
  - cv_system
related_stages:
  - cv_analysis
  - cv_generation
---

# FitCV Wave 2 Operator And Observability Truth Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `multiple`
- `docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md`
**Implementation Execution Map:** `docs/superpowers/execution_maps/2026-04-28-fitcv-first-wave-implementation-execution-map.md`  
**Type:** add  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Make persisted late-stage event records and control-plane run-detail surfaces faithful to the Wave 1 truth model, so timeline rows, badges, downloads, and diagnostics stop inferring meaning from ad hoc event copy.

**Architecture:** This plan first stabilizes the bounded event contract emitted from pipeline late-stage seams, then aligns the control-plane timeline and run-detail readers to consume stage-owned truth and deterministic outcome fields instead of reconstructing them from message strings alone. The code center of gravity is split between `src/fitcv/pipeline.py` and `src/fitcv_cp/app.py`, with `src/fitcv_cp/reporter.py` remaining the shared persistence seam.

**Key Invariants:**
- event records remain derived from stage-owned runtime truth
- deterministic outcomes and stage-owned subreasons stay inspectable in bounded event payloads
- timeline summaries are derived views over event facts and stage artifact counts
- stage artifact downloads appear only when the underlying stage artifact is actually available
- run-detail labels stay subordinate to runtime truth instead of becoming a parallel status system

**Rollout / Revert:**  
- rollback_trigger: event payloads, timeline summaries, or run-detail surfaces disagree with accepted Wave 1 stage-owned and deterministic truth behavior  
- rollback_method: revert the Wave 2 event and run-detail patches together so event emission and control-plane consumption move back to the prior bounded surface in one change

## Triage

Layer: `change`  
Feature type: `ADD`  
Summary: Implement the Wave 2 event-contract and run-detail-truth subset across pipeline reporter emission and control-plane inspection surfaces.  
Reasoning:

- the execution map explicitly groups these two specs into one bounded Wave 2 plan
- both specs share event names, timeline summaries, artifact-link gating, and operator-facing outcome projection
- the work is cross-surface but still bounded to observability and control-plane truth, not broader product expansion

Invariants:

- event facts stay machine-stable and bounded
- control-plane labels remain derived views
- run-detail truth hierarchy stays runtime first, UI second

Dependencies:

- `docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md`
- `docs/superpowers/execution_maps/2026-04-28-fitcv-first-wave-implementation-execution-map.md`
- Wave 1 merged runtime-truth work on `main`

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

- `none`

Invariant IDs:

- `none`

Spec needed: `yes`  
Plan needed: `yes`

Rollback trigger:

- bounded event payloads stop matching accepted late-stage runtime truth or the
  run detail page starts overstating success or artifact availability

Rollback method:

- revert the combined Wave 2 event-emission and control-plane-consumption
  changes until the event contract and run-detail readers are corrected together

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
- `src/fitcv_cp/reporter.py`
- `src/fitcv_cp/app.py`
- generated:
  - `docs/generated/planning_lineage.yaml`

Tests to update:

- `tests/test_pipeline.py`
- `tests/test_fitcv_cp/test_app.py`

Files to create:

- none

## Task 1: Define And Emit Bounded Late-Stage Event Facts

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv/pipeline.py`
  - `src/fitcv_cp/reporter.py`
- Test:
  - `tests/test_pipeline.py`
- Docs:
  - `none`

- [ ] Step 1: Add or tighten failing runtime tests in `tests/test_pipeline.py` for:
  - bounded `cv_analysis` event payload emission
  - bounded `cv_generation` event payload emission
  - deterministic outcome and stage-owned subreason presence on decision events
  - pipeline-complete events continuing to omit heavy export payloads
- [ ] Step 2: Run the targeted failing tests:
  - `python -m pytest tests/test_pipeline.py -k "pipeline_complete_event or reporter or layer4_cv_analysis or validation_failed"`
- [ ] Step 3: Update `src/fitcv/pipeline.py` so late-stage reporter emits bounded payloads with:
  - `event_name`
  - `event_family`
  - `source_stage`
  - `job_url` where job-scoped
  - `deterministic_outcome`
  - `stage_owned_subreason`
  - bounded provenance, input, output, and artifact-ref fields where relevant
- [ ] Step 4: Update `src/fitcv_cp/reporter.py` only as needed so payload persistence remains a thin shared adapter instead of reinterpreting event truth.
- [ ] Step 5: Re-run the targeted tests and confirm pass:
  - `python -m pytest tests/test_pipeline.py -k "pipeline_complete_event or reporter or layer4_cv_analysis or validation_failed"`
- [ ] Step 6: Commit the bounded event-contract emission change.

## Task 2: Align Timeline Summaries And Run-Detail Truth Consumption

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv_cp/app.py`
- Test:
  - `tests/test_fitcv_cp/test_app.py`
- Docs:
  - `none`

- [ ] Step 1: Add failing control-plane tests in `tests/test_fitcv_cp/test_app.py` for:
  - timeline summary messages reading the new event and stage-artifact truth
  - run-detail pipeline outcome labels preserving deterministic outcome and stage-owned subreason distinctions
  - artifact download links appearing only when the corresponding stage artifact is actually available
  - "ready for generation" staying distinct from blocked, skipped, and rejected outcomes
- [ ] Step 2: Run the targeted failing tests:
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "timeline or validation_failed_job or ready_job or reranker_blocked_job or stage_download"`
- [ ] Step 3: Update `src/fitcv_cp/app.py` so:
  - timeline summaries prefer stage artifact counts and bounded event payload facts
  - run-detail outcome badges and detail text read deterministic outcome plus stage-owned subreason where available
  - artifact-link gating stays faithful to actual stage reachability and stored artifact presence
  - "friendly" labels do not flatten blocked, skipped, analysis-failed, validation-failed, generation-failed, and persistence-failed paths into one bucket
- [ ] Step 4: Re-run the targeted tests and confirm pass:
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "timeline or validation_failed_job or ready_job or reranker_blocked_job or stage_download"`
- [ ] Step 5: Commit the run-detail and timeline truth-alignment change.

## Task 3: Run Wave 2 End-To-End Validation And Refresh Discovery

**Files:**
- Create: `none`
- Modify:
  - `docs/generated/planning_lineage.yaml`
- Test:
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_app.py`
- Docs:
  - exact entries from the Doc Update Matrix

- [ ] Step 1: Run the focused regression suite for the Wave 2 subset:
  - `python -m pytest tests/test_pipeline.py tests/test_fitcv_cp/test_app.py`
- [ ] Step 2: If failures reveal cross-surface drift, make the smallest bounded fix in the owning runtime or control-plane file and re-run the affected tests.
- [ ] Step 3: Refresh generated discovery and managed-doc outputs:
  - `python scripts/generate_planning_lineage.py`
  - `python scripts/sync_architecture_docs.py`
  - `python scripts/sync_architecture_docs.py --check`
- [ ] Step 4: Run repo contract validation:
  - `python scripts/validate_adoption_shape.py`
  - `python scripts/validate_repo_contracts.py --fast`
- [ ] Step 5: Confirm the worktree only contains intended Wave 2 changes plus any unrelated pre-existing files.
- [ ] Step 6: Commit the Wave 2 validation and generated-output refresh.

## Shared-Surface Risks

- `src/fitcv/pipeline.py`
  - event payload cleanup can accidentally duplicate stage artifacts or reopen
    settled runtime-truth semantics if the bounded contract is not kept small
- `src/fitcv_cp/app.py`
  - timeline and run-detail convenience logic can silently become a second truth
    system if message parsing outruns runtime payload shape
- `src/fitcv_cp/reporter.py`
  - payload persistence must remain a serializer seam, not a translation layer

## Sequencing Notes

- finish event emission semantics before changing timeline or run-detail readers
- keep payloads bounded first, then adjust UI projection and download gating
- run focused pipeline and control-plane regression suites before broad contract
  validation so naming drift is easier to localize

## Acceptance Criteria

- late-stage event records preserve deterministic outcome and stage-owned
  subreason in bounded machine-stable payloads
- control-plane timeline rows summarize real event and artifact truth without
  overstating success
- run-detail outcome labels preserve blocked, skipped, ready, and rejected
  distinctions
- artifact download availability matches actual stored stage artifact state

## Next Artifact

After this plan, the next plan should cover Wave 3 from the execution map:

- `fitcv-semantic-spine-input-mode-parity-spec`
- `agentic-cv-quality-analysis-grounding-spec`
