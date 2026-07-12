---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-ssot-symmetry-phase-2-stage-lifecycle-late-stage-consolidation
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-12-13-10-fitcv-ssot-symmetry-phase-2-stage-lifecycle-late-stage-consolidation-spec.md
targets:
  - src/fitcv/pipeline_contracts.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/run_lifecycle.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/reconciler_service.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/templates/run_detail.html
  - docs/architecture.md
  - docs/api.md
  - docs/pipeline.md
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_pipeline_status_registry.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_queue.py
  - tests/test_fitcv_cp/test_reconciler.py
  - tests/test_fitcv_cp/test_run_lifecycle.py
related_features: []
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Execute Phase 2 from
`docs/superpowers/specs/2026-07-12-13-10-fitcv-ssot-symmetry-phase-2-stage-lifecycle-late-stage-consolidation-spec.md`:

- centralize runtime stage-equivalent facts in `src/fitcv/pipeline_contracts.py`
- centralize lifecycle policy in `src/fitcv_cp/run_lifecycle.py`
- centralize late-stage status meaning in `src/fitcv/late_stage_contract.py`

## Key Deliverables

### Deliverable 1: runtime stage registry is single-owner

`pipeline.py` and `app.py` stop owning local stage-sequence, timeline-stage,
download-label, and artifact-bundle literal maps. They consume one registry and
derived helpers from `src/fitcv/pipeline_contracts.py`.

### Deliverable 2: lifecycle policy is executable and bounded

`RunStatus` stays in `models.py`, while `run_lifecycle.py` owns only command
eligibility, status projection/grouping, stale-cancelling detection, and
timeout / lifecycle target-status interpretation.

### Deliverable 3: late-stage contract is sole meaning owner

`pipeline.py`, `agentic_cv_analysis.py`, and `agentic_cv_generation.py` stop
owning duplicate late-stage literals and parity wrappers. Tests move from
duplicate-parity assertions to direct owner-contract assertions.

### Deliverable 4: bounded proof is executable

Focused grep checks, compile checks, pytest set, planning-lineage refresh, and
fast validator prove Phase 2 landed cleanly without pulling in Phase 3 or Phase
4 cleanup.

## Task/Wave Breakdown

### Task 1: Consolidate runtime stage registry

**Purpose:**
- move stage-equivalent runtime truth to one owner without redesigning stage
  docs or file structure

**Files:**
- Modify: `src/fitcv/pipeline_contracts.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_artifacts.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Phase 2 spec accepted
- no Phase 3 settings or Phase 4 routing work mixed into stage-owner patch

**Steps:**
- [ ] Step 1: expand `pipeline_contracts.py` with one immutable stage registry
      that owns stage order, display label, event alias mapping, download
      eligibility, stage artifact filename, and bundle membership.
- [ ] Step 2: replace `PIPELINE_STAGE_SEQUENCE` ownership in `pipeline.py` with
      imports/derived helpers from `pipeline_contracts.py`.
- [ ] Step 3: replace `STAGE_SEQUENCE`, `TIMELINE_STAGE_LABELS`,
      `TIMELINE_STAGE_DOWNLOADS`, `TIMELINE_STAGE_DOWNLOADABLE_EVENTS`,
      `STAGE_DOWNLOAD_LABELS`, `BUNDLE_STAGE_IDS`, and
      `BUNDLE_ARTIFACT_FILENAMES` ownership in `app.py` with imports/derived
      helpers.
- [ ] Step 4: route run-detail timeline and artifact-download helpers through
      the canonical stage registry while keeping external filenames and stage
      availability stable.
- [ ] Step 5: rewrite tests to lock external stage/download contract, not the
      old local literal placement.

**Verification:**
- [ ] `rg -n "^PIPELINE_STAGE_SEQUENCE =|^STAGE_SEQUENCE:|^TIMELINE_STAGE_LABELS:|^TIMELINE_STAGE_DOWNLOADS:|^TIMELINE_STAGE_DOWNLOADABLE_EVENTS:|^STAGE_DOWNLOAD_LABELS:|^BUNDLE_STAGE_IDS:|^BUNDLE_ARTIFACT_FILENAMES:" src/fitcv/pipeline.py src/fitcv_cp/app.py`
- [ ] `py -3 -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- runtime stage-equivalent facts have one executable owner in
  `pipeline_contracts.py`

### Task 2: Add bounded lifecycle helper and route policy callers through it

**Purpose:**
- centralize lifecycle policy only where semantics are truly shared

**Files:**
- Modify: `src/fitcv_cp/models.py`
- Add: `src/fitcv_cp/run_lifecycle.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/reconciler_service.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Add: `tests/test_fitcv_cp/test_run_lifecycle.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_queue.py`
- Modify: `tests/test_fitcv_cp/test_reconciler.py`

**Preconditions:**
- Task 1 complete or at least not overlapping same helpers
- lifecycle helper remains pure-function only

**Steps:**
- [ ] Step 1: create `run_lifecycle.py` with pure helpers for status groups,
      status projection, action eligibility, lifecycle target-status selection,
      stale-cancelling detection, and timeout target-status interpretation.
- [ ] Step 2: encode explicit command contract for `cancel`, `continue`,
      `retry`, `archive`, `unarchive`, and `repair_stale_cancelling`.
- [ ] Step 3: replace local app helpers `RUN_STATUS_GROUPS`,
      `_run_status_projection`, `_can_cancel_run`, `_can_archive_run`,
      `_can_unarchive_run`, and `_is_stale_cancelling` with imports from the
      shared helper.
- [ ] Step 4: route worker/reconciler/sqlite-store lifecycle-policy decisions
      through shared helpers only where they represent command/transition
      semantics; leave unrelated export or domain checks local.
- [ ] Step 5: add focused tests for helper-level contract and update app /
      worker tests to assert symmetric behavior through shared helpers.

**Verification:**
- [ ] `rg -n "^RUN_STATUS_GROUPS =|def _run_status_projection|def _can_cancel_run|def _can_archive_run|def _can_unarchive_run|def _is_stale_cancelling" src/fitcv_cp/app.py`
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_run_lifecycle.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py -q`

**Exit Criteria:**
- lifecycle-policy logic has one bounded owner and app-local duplicates are gone

### Task 3: Consolidate late-stage meaning and delete parity wrappers

**Purpose:**
- make one late-stage contract own status meaning across pipeline, analysis,
  and generation code

**Files:**
- Modify: `src/fitcv/late_stage_contract.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/agentic_cv_analysis.py`
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `tests/test_pipeline_status_registry.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Modify: `tests/test_pipeline.py`

**Preconditions:**
- Task 1 complete enough that stage identifiers are stable
- late-stage contract remains single shared owner, not split by module

**Steps:**
- [ ] Step 1: move remaining late-stage literal ownership into
      `late_stage_contract.py`, including generation statuses still owned in
      `agentic_cv_generation.py` if they are part of shared semantic family.
- [ ] Step 2: delete duplicate helper wrappers from `pipeline.py` and
      `agentic_cv_analysis.py` where they only mirror shared contract logic.
- [ ] Step 3: switch pipeline/analysis/generation consumers to direct imports
      from the contract.
- [ ] Step 4: rewrite tests from parity-with-duplicate assertions to direct
      owner-contract and externally visible behavior assertions.

**Verification:**
- [ ] `rg -n "^CV_ANALYSIS_.*STATUS =|^CV_GENERATION_.*STATUS =|^ACCEPTED_STATUS:|^VALIDATION_FAILED_STATUS:|^GENERATION_FAILED_STATUS:|def _validation_status_for_cv_status|def _deterministic_truth_fields|def _cv_generation_status_for_analysis_status" src/fitcv/pipeline.py src/fitcv/agentic_cv_analysis.py src/fitcv/agentic_cv_generation.py`
- [ ] `py -3 -m pytest tests/test_pipeline_status_registry.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py -q`

**Exit Criteria:**
- late-stage status meaning has one owner and duplicate wrappers/literals are gone

### Task 4: Doc sweep and bounded closeout proof

**Purpose:**
- prove Phase 2 landed cleanly and did not slide into settings or routing work

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/api.md`
- Modify: `docs/pipeline.md`
- Verify: `docs/generated/planning_lineage.yaml`
- Verify: touched tests from Tasks 1-3

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [ ] Step 1: update cross-cutting docs only where runtime-owner descriptions or
      route semantics changed.
- [ ] Step 2: run final residue grep for stage-owner duplicates, app lifecycle
      helper duplicates, and late-stage wrapper duplicates.
- [ ] Step 3: run focused compile checks and full Phase 2 pytest set.
- [ ] Step 4: refresh planning lineage and rerun fast validator.
- [ ] Step 5: confirm no Phase 3 settings-schema or Phase 4 routing/persistence
      cleanup landed by accident.

**Verification:**
- [ ] `py -3 -m py_compile src/fitcv/pipeline_contracts.py src/fitcv/late_stage_contract.py src/fitcv/pipeline.py src/fitcv/agentic_cv_analysis.py src/fitcv/agentic_cv_generation.py src/fitcv/pipeline_stage_artifacts.py src/fitcv_cp/models.py src/fitcv_cp/run_lifecycle.py src/fitcv_cp/app.py src/fitcv_cp/worker_job.py src/fitcv_cp/reconciler_service.py src/fitcv_cp/sqlite_store.py`
- [ ] `py -3 -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_status_registry.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_run_lifecycle.py -q`
- [ ] `py -3 scripts/generate_planning_lineage.py`
- [ ] `py -3 scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- Phase 2 is proven clean, bounded, and ready for execution closeout or Phase 3
  handoff

## Verification

- `rg -n "^PIPELINE_STAGE_SEQUENCE =|^STAGE_SEQUENCE:|^TIMELINE_STAGE_LABELS:|^TIMELINE_STAGE_DOWNLOADS:|^TIMELINE_STAGE_DOWNLOADABLE_EVENTS:|^STAGE_DOWNLOAD_LABELS:|^BUNDLE_STAGE_IDS:|^BUNDLE_ARTIFACT_FILENAMES:" src/fitcv/pipeline.py src/fitcv_cp/app.py`
- `rg -n "^RUN_STATUS_GROUPS =|def _run_status_projection|def _can_cancel_run|def _can_archive_run|def _can_unarchive_run|def _is_stale_cancelling" src/fitcv_cp/app.py`
- `rg -n "^CV_ANALYSIS_.*STATUS =|^CV_GENERATION_.*STATUS =|^ACCEPTED_STATUS:|^VALIDATION_FAILED_STATUS:|^GENERATION_FAILED_STATUS:|def _validation_status_for_cv_status|def _deterministic_truth_fields|def _cv_generation_status_for_analysis_status" src/fitcv/pipeline.py src/fitcv/agentic_cv_analysis.py src/fitcv/agentic_cv_generation.py`
- `py -3 -m py_compile src/fitcv/pipeline_contracts.py src/fitcv/late_stage_contract.py src/fitcv/pipeline.py src/fitcv/agentic_cv_analysis.py src/fitcv/agentic_cv_generation.py src/fitcv/pipeline_stage_artifacts.py src/fitcv_cp/models.py src/fitcv_cp/run_lifecycle.py src/fitcv_cp/app.py src/fitcv_cp/worker_job.py src/fitcv_cp/reconciler_service.py src/fitcv_cp/sqlite_store.py`
- `py -3 -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_status_registry.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_run_lifecycle.py -q`
- `py -3 scripts/generate_planning_lineage.py`
- `py -3 scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-12-13-10-fitcv-ssot-symmetry-phase-2-stage-lifecycle-late-stage-consolidation-spec.md`
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
