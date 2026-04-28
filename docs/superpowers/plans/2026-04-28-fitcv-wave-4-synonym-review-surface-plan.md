---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
parent_spec: docs/superpowers/specs/2026-04-28-agentic-synonym-review-queue-and-operator-actions-spec.md
targets:
  - docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md
  - docs/superpowers/specs/2026-04-28-agentic-synonym-review-queue-and-operator-actions-spec.md
  - docs/superpowers/execution_maps/2026-04-28-fitcv-first-wave-implementation-execution-map.md
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/bq_store.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_bq_store.py
related_features:
  - trigger_run_management
  - inspection_debugging
  - settings_system
related_stages:
  - enrich
  - rule_filter
---

# FitCV Wave 4 Synonym Review Surface Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `multiple`
- `docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-synonym-review-queue-and-operator-actions-spec.md`
**Implementation Execution Map:** `docs/superpowers/execution_maps/2026-04-28-fitcv-first-wave-implementation-execution-map.md`  
**Type:** add  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Turn existing run-scoped mapping suggestions and overlay seams into one bounded synonym proposal primitive plus one operator review surface that can approve, reject, defer, and apply proposals as run-scoped overlays without mutating shared canonical synonym config.

**Architecture:** This wave builds on the stable runtime truth, operator truth, and checkpoint parity work from Waves 1 through 3. The first seam creates a stable review-ready proposal object from existing mapping suggestion snapshots and persisted run evidence. The second seam builds the operator review queue and action model on top of that object inside the control plane. The center of gravity is mostly control-plane and persistence orchestration, with worker snapshots and run-detail overlay surfaces acting as the grounding surfaces.

**Key Invariants:**
- shared canonical synonym config remains human-approved truth
- proposal generation is advisory and review-first
- run-scoped overlay adoption is distinct from shared-default promotion
- review actions preserve proposal identity, rationale, and provenance
- operator-facing synonym review state must stay faithful to persisted proposal truth

**Rollout / Revert:**  
- rollback_trigger: synonym proposals become ambiguous to identify, review actions silently mutate shared config, or run overlays stop being traceable back to approved proposals  
- rollback_method: revert the Wave 4 proposal and review-surface patches together until synonym assistance returns to immutable run-scoped suggestion snapshots plus manual overlay upload only

## Triage

Layer: `change`  
Feature type: `ADD`  
Summary: Implement the Wave 4 synonym proposal primitive and shared operator review surface across mapping-suggestion derivation, run-scoped persistence, queue actions, and overlay provenance surfaces.  
Reasoning:

- the execution map explicitly splits synonym work into a standalone proposal primitive followed by the shared review surface
- Waves 1 through 3 already stabilized the truth vocabulary this review flow should reuse
- the repo already has mapping suggestions, run overlays, and inspection surfaces, so this wave can stay bounded to proposal and review semantics instead of inventing the whole system from scratch

Invariants:

- mapping suggestion snapshots remain upstream evidence, not the final review schema
- proposal identity is stable enough for queue and action references
- queue rows are projections of proposal objects, not a second competing schema
- overlay provenance remains inspectable in run detail after approval-driven adoption

Dependencies:

- `docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-synonym-review-queue-and-operator-actions-spec.md`
- `docs/superpowers/execution_maps/2026-04-28-fitcv-first-wave-implementation-execution-map.md`
- merged Wave 1, Wave 2, and Wave 3 truth work on `main`

Affected stages:

- `enrich`
- `rule_filter`

Affected features:

- `trigger_run_management`
- `inspection_debugging`
- `settings_system`

Primary lens: `mixed`

Affected docs:
  feature_source: `none`
  feature_yaml: `none`
  feature_lineage:
    - `docs/features/trigger_run_management/lineage.generated.yaml`
    - `docs/features/inspection_debugging/lineage.generated.yaml`
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

- proposal ids, review state, or overlay provenance stop being trustworthy
  enough for operator review and debugging

Rollback method:

- revert the combined Wave 4 proposal-engine and review-surface changes until
  synonym assistance is back to reviewless snapshots plus manual overlay upload

Migration needed: `no`  
Risk level: `medium`

## Doc Update Matrix

- Feature source: `none`
- Feature contract: `none`
- Feature lineage:
  - `docs/features/trigger_run_management/lineage.generated.yaml`
  - `docs/features/inspection_debugging/lineage.generated.yaml`
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
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/models.py`
- `src/fitcv_cp/bq_store.py`
- generated:
  - `docs/generated/planning_lineage.yaml`
  - `docs/features/trigger_run_management/lineage.generated.yaml`
  - `docs/features/inspection_debugging/lineage.generated.yaml`

Tests to update:

- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_worker_job.py`
- `tests/test_fitcv_cp/test_bq_store.py`

Files to create:

- `none`

## Task 1: Create The Synonym Proposal Primitive

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv/pipeline.py`
  - `src/fitcv_cp/worker_job.py`
  - `src/fitcv_cp/models.py`
  - `src/fitcv_cp/bq_store.py`
- Test:
  - `tests/test_fitcv_cp/test_worker_job.py`
  - `tests/test_fitcv_cp/test_bq_store.py`
- Docs:
  - `none`

- [ ] Step 1: Add or tighten failing tests for:
  - mapping suggestion snapshots deriving one bounded proposal object shape
  - stable `proposal_id`, `proposal_scope`, `proposal_family`, and
    `proposal_status` fields
  - confidence, rationale, evidence summary, and conflict summary preserving
    review-ready meaning
  - immutable run-scoped suggestion snapshots remaining source evidence rather
    than being overwritten by proposal storage
- [ ] Step 2: Run the targeted failing tests:
  - `python -m pytest tests/test_fitcv_cp/test_worker_job.py -k "mapping_suggestions or synonym or proposal"`
  - `python -m pytest tests/test_fitcv_cp/test_bq_store.py -k "mapping_suggestions or synonym or proposal"`
- [ ] Step 3: Update `src/fitcv/pipeline.py`, `src/fitcv_cp/worker_job.py`,
  `src/fitcv_cp/models.py`, and `src/fitcv_cp/bq_store.py` so:
  - existing mapping suggestions can be normalized into a canonical proposal
    object
  - proposal identity and review-first state are persisted without mutating
    canonical synonym config
  - conflict and ambiguity cases remain explicit proposal objects rather than
    being flattened into simple alias mappings
  - run-scoped evidence and artifact references remain available for later queue
    and overlay actions
- [ ] Step 4: Re-run the targeted tests and confirm pass.
- [ ] Step 5: Commit the proposal-primitive change.

## Task 2: Build The Shared Review Queue And Operator Actions

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/models.py`
  - `src/fitcv_cp/bq_store.py`
  - `src/fitcv_cp/worker_job.py`
- Test:
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_bq_store.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
- Docs:
  - `none`

- [ ] Step 1: Add or tighten failing tests for:
  - queue rows projecting persisted proposal objects instead of ad hoc summary
    shapes
  - bounded review states such as `proposed_unreviewed`, `in_review`,
    `approved_for_run_overlay`, `rejected`, and `deferred`
  - explicit operator actions preserving proposal id, timestamp, actor, and
    bounded note fields
  - approval producing run-scoped overlay provenance that stays distinct from
    manual overlay upload
- [ ] Step 2: Run the targeted failing tests:
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym or proposal or review"`
  - `python -m pytest tests/test_fitcv_cp/test_bq_store.py -k "synonym or proposal or review"`
  - `python -m pytest tests/test_fitcv_cp/test_worker_job.py -k "synonym or proposal or review"`
- [ ] Step 3: Update `src/fitcv_cp/app.py`, `src/fitcv_cp/models.py`,
  `src/fitcv_cp/bq_store.py`, and `src/fitcv_cp/worker_job.py` so:
  - the operator control plane exposes a bounded review queue for synonym
    proposals
  - review actions are explicit state transitions rather than implicit overlay
    side effects
  - approved proposals can generate or update run-scoped overlays while
    preserving proposal provenance
  - the run-detail surface keeps manual-upload overlays and review-derived
    overlays semantically distinct
- [ ] Step 4: Re-run the targeted tests and confirm pass.
- [ ] Step 5: Commit the review-surface change.

## Task 3: Run Wave 4 Validation And Refresh Discovery

**Files:**
- Create: `none`
- Modify:
  - `docs/generated/planning_lineage.yaml`
  - `docs/features/trigger_run_management/lineage.generated.yaml`
  - `docs/features/inspection_debugging/lineage.generated.yaml`
- Test:
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
  - `tests/test_fitcv_cp/test_bq_store.py`
- Docs:
  - exact entries from the Doc Update Matrix

- [ ] Step 1: Run the focused regression suite for the Wave 4 subset:
  - `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_bq_store.py -k "synonym or proposal or review"`
- [ ] Step 2: If failures reveal cross-surface drift, make the smallest bounded
  fix in the owning file and re-run the affected tests.
- [ ] Step 3: Refresh generated discovery and managed-doc outputs:
  - `python scripts/generate_planning_lineage.py`
  - `python scripts/sync_architecture_docs.py`
  - `python scripts/sync_architecture_docs.py --check`
- [ ] Step 4: Run repo contract validation:
  - `python scripts/validate_adoption_shape.py`
  - `python scripts/validate_repo_contracts.py --fast`
- [ ] Step 5: Confirm the worktree only contains intended Wave 4 changes plus
  any unrelated pre-existing files.
- [ ] Step 6: Commit the Wave 4 validation and generated-output refresh.

## Shared-Surface Risks

- `src/fitcv/pipeline.py`
  - mapping suggestions can remain too raw, which would force the review queue
    to guess proposal meaning
- `src/fitcv_cp/worker_job.py`
  - proposal derivation can drift from run-owned snapshots if persistence and
    worker checkpoints do not share one bounded object shape
- `src/fitcv_cp/app.py`
  - queue rows and action buttons can become a second semantic system if they do
    not project persisted proposal truth directly
- `src/fitcv_cp/models.py` and `src/fitcv_cp/bq_store.py`
  - proposal status and action persistence can drift if identity, provenance,
    or notes are not modeled explicitly enough

## Sequencing Notes

- finish the proposal primitive before building any operator queue or action
  surface on top of it
- keep run-scoped overlay adoption bounded and explicit before considering any
  later shared-default promotion workflow
- validate proposal persistence and operator review surfaces together before
  broad repo contract checks so synonym-review drift is easier to localize

## Acceptance Criteria

- a reviewer can inspect one persisted synonym proposal object and understand
  what alias or conflict is being proposed, why, and with what confidence
- review queue rows are projections of proposal objects rather than a second
  ad hoc schema
- operator actions preserve proposal identity, state transition history, and
  bounded notes
- approval creates or updates run-scoped overlay provenance without mutating
  shared canonical synonym config
