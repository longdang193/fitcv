---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-llm-runtime-spine-phase-1-cv-analysis-single-owner-implementation
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-14-12-52-fitcv-llm-runtime-spine-phase-1-cv-analysis-single-owner-spec.md
targets:
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/contracts.py
  - src/fitcv/evidence.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv/reuse.py
  - src/fitcv/pipeline_observability.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_stages/common.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_analysis.yaml
  - docs/pipeline.md
  - docs/architecture.md
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
  - tests/test_agentic_cv_analysis.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - cv_system
  - inspection_debugging
  - settings_system
  - trigger_run_management
related_stages:
  - ranking
  - cv_analysis
  - cv_generation
---

# Implementation Plan: FitCV LLM runtime spine Phase 1 CV-analysis single owner

## Goal

Make `fitcv.agentic_cv_analysis.analyze_ranked_job` the only per-job
CV-analysis business entrypoint without changing ranking, evidence, gap, or
CV-generation meaning.

Pipeline keeps batch execution, reuse-candidate lookup, persistence,
observability, and downstream debug projection. It stops owning reranker gates,
evidence selection, fallback, gap computation, fit-gate classification, record
construction, reuse validity, and readiness meaning.

## Key Deliverables

### Deliverable 1: complete canonical analyzer contract

`analyze_ranked_job` handles reranker block, exact eligible reuse, fresh
analysis, fallback evidence, fit-gate skip, ready output, and analysis failure.
`CvAnalysisRecord` contains required identity, reuse, decision, grounding, and
trace fields without pipeline hydration. Stable identity uses existing
`job_identity_keys`; reuse rejects incomplete or contract-incompatible records.

### Deliverable 2: one pipeline path for CV analysis

Built-in versus agentic analysis branching is deleted. Configured
`cv_analysis_concurrency` remains observable, but Phase 1 runs one serial
canonical analyzer path and reports effective concurrency as `1`.

### Deliverable 3: deleted duplicate owners

Pipeline-local record/input hydration helpers and stage-runner semantic helpers
are removed. Remaining orchestration and projections consume canonical records.

### Deliverable 4: contract proof and documentation alignment

Focused analyzer, pipeline, replay/resume, worker, and control-plane tests prove
one record shape and one status meaning. Stage and architecture docs change only
where current owner wording is stale; generated metadata is refreshed only when
its source changes.

## Task/Wave Breakdown

### Task 1: Lock canonical contract with failing tests

**Purpose:**
- define executable behavior before deleting duplicate branches

**Files:**
- Inspect: `src/fitcv/agentic_cv_analysis.py`
- Inspect: `src/fitcv/pipeline.py`
- Modify: `tests/test_agentic_cv_analysis.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`

**Preconditions:**
- Phase 1 spec has `status: active`
- current analyzer and pipeline tests pass before new assertions are added

**Steps:**
- [x] Add canonical-record assertions for `analysis_input_components`,
      `reuse_decision`, decision chain, evidence summary, gap, requirement
      coverage, section confidence, `do_not_claim`, and trace.
- [x] Add exact-reuse fixtures for `ready_for_generation` and
      `skipped_fit_gate` records with matching fingerprints.
- [x] Add recomputation fixtures for `analysis_failed`, reranker-blocked,
      mismatched-fingerprint, fingerprintless, incomplete, and
      contract-incompatible candidates.
- [x] Add identity fixtures for same raw fingerprint with changed URL, duplicate
      URL with distinct raw fingerprints, and minimal input without raw
      fingerprint.
- [x] Add failure-envelope fixtures for reranker resolution and fingerprint
      construction, not only failures inside evidence/gap work.
- [x] Add empty, single-item, and mixed-status pipeline fixtures.
- [x] Add status/error fixtures proving expected blocks/skips use
      `outcome_reason`, failures use `error`, and ready output uses neither.
- [x] Add pipeline parity assertion proving compatibility mode cannot change
      canonical CV-analysis output for same deterministic inputs.
- [x] Run new tests before implementation and confirm they fail for missing
      canonical reuse/identity behavior or existing branch divergence.

**Verification:**
- [x] `python -m pytest tests/test_agentic_cv_analysis.py -q`
- [x] `python -m pytest tests/test_pipeline_agentic_late_stage.py -k cv_analysis -q`
- [x] `python -m pytest tests/test_pipeline_stage_resume_parity.py -k cv_analysis -q`

**Exit Criteria:**
- tests encode every Phase 1 admissible outcome and fail against current split
  ownership for expected reasons

### Task 2: Complete `analyze_ranked_job` and canonical record

**Purpose:**
- move missing identity and reuse semantics into sole analysis owner

**Files:**
- Modify: `src/fitcv/contracts.py`
- Modify: `src/fitcv/evidence.py`
- Inspect: `src/fitcv/reuse.py`
- Inspect: `src/fitcv/late_stage_contract.py`
- Inspect: `src/fitcv/pipeline_stages/common.py`
- Modify: `src/fitcv/agentic_cv_analysis.py`
- Verify: `tests/test_agentic_cv_analysis.py`

**Preconditions:**
- Task 1 contract tests exist and fail for intended gaps

**Steps:**
- [x] Extend `CvAnalysisRecord` with `raw_job_fingerprint`,
      `analysis_input_components`, and `reuse_decision`; do not add
      CV-generation-owned fields.
- [x] Reuse `job_identity_keys` for canonical record and trace identity; do not
      add another identity helper.
- [x] Remove mutable URL from CV-analysis semantic fingerprint payload and bump
      `CV_ANALYSIS_REUSE_SCHEMA_VERSION`.
- [x] Move `_analysis_input_components` behavior from pipeline into
      `agentic_cv_analysis.py` using existing fingerprint payload.
- [x] Extend `analyze_ranked_job` with optional `reusable_record` while keeping
      existing `top_k` behavior.
- [x] Keep reranker block first; blocked jobs do not retrieve evidence, compute
      gaps, or reuse prior analysis.
- [x] Compute current fingerprint once for non-blocked jobs and accept reuse only
      when fingerprint matches and prior status is `ready_for_generation` or
      `skipped_fit_gate`, current contract fingerprint matches, and every
      required canonical field is present.
- [x] Rebuild eligible reused output through `build_cv_analysis_record` using
      prior semantic payload plus current identity and job snapshot; set
      `analysis_reuse_status=reused_exact_match` with existing
      `build_reuse_decision`. Never return candidate dictionary directly.
- [x] Recompute failed, blocked, incomplete, contract-mismatched,
      fingerprint-mismatched, or fingerprintless candidates and record
      fresh-compute reason through same reuse-decision shape.
- [x] Update `build_cv_analysis_record` so every returned status shape, fresh
      or reused, includes input components and reuse decision.
- [x] Validate trust-boundary input types before analysis. After acceptance, wrap
      reranker, fingerprint, reuse, evidence, gap, fit, record, and trace work in
      one exception boundary returning canonical `analysis_failed`.
- [x] Preserve current evidence bundle, fallback, gap, fit-gate, and trace
      semantics; use canonical status constants only.

**Verification:**
- [x] `python -m pytest tests/test_agentic_cv_analysis.py -q`
- [x] Direct analyzer fixtures return complete records without pipeline helpers.

**Exit Criteria:**
- analyzer alone produces complete canonical records for fresh, reused, blocked,
  skipped, ready, and failed outcomes

### Task 3: Collapse pipeline onto canonical analyzer

**Purpose:**
- delete pipeline-owned CV-analysis meaning while preserving orchestration and
  concurrency

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`
- Verify: `src/fitcv/pipeline_observability.py`
- Verify: `src/fitcv/pipeline_stage_artifacts.py`

**Preconditions:**
- Task 2 analyzer tests pass

**Steps:**
- [x] Import and call `analyze_ranked_job` by canonical name; remove
      `run_agentic_cv_analysis` alias.
- [x] Keep reuse snapshot indexing and candidate lookup in pipeline, but pass
      candidate record to analyzer without deciding reuse validity or mutating
      returned semantic fields.
- [x] Remove pipeline reranker-block record construction and pass every ranked
      job through canonical analyzer.
- [x] Replace built-in versus agentic compute branch with one analyzer call.
- [x] Delete CV-analysis executor/future branches and invoke canonical analyzer
      serially. Preserve configured concurrency in diagnostics and report
      effective concurrency as `1`.
- [x] Preserve result ordering for empty, single-item, and mixed-status batches.
- [x] Keep observation emission, aggregate counts, persistence, reuse-miss
      diagnostics, and CV-generation debug projection derived from returned
      record.
- [x] Delete pipeline-local `_analysis_input_components`,
      `_attach_analysis_input_components`, and `_build_cv_analysis_record`.
- [x] Remove now-unused evidence/gap imports only after repository search confirms
      no remaining non-analysis caller in `pipeline.py`.
- [x] Update tests to patch `fitcv.pipeline.analyze_ranked_job` and assert one
      path for compatibility-mode variants.

**Verification:**
- [x] `python -m pytest tests/test_pipeline_agentic_late_stage.py -q`
- [x] `python -m pytest tests/test_pipeline_stage_resume_parity.py -q`
- [x] `python -m pytest tests/test_pipeline.py -k "cv_analysis or late_stage" -q`
- [x] Empty, single-item, and mixed-status fixtures produce ordered canonical
      records for configured concurrency values `1` and greater than `1`.

**Exit Criteria:**
- pipeline contains one CV-analysis call path and no record, evidence, gap, fit,
  or reuse-validity implementation

### Task 4: Delete stage-runner semantic helpers and normalize consumers

**Purpose:**
- remove unused duplicate helper surface and keep readiness/status consumption
  canonical

**Files:**
- Modify: `src/fitcv/pipeline_stage_runner.py`
- Verify: `src/fitcv/pipeline_stages/common.py`
- Verify: `src/fitcv/pipeline_observability.py`
- Verify: `src/fitcv/pipeline_stage_artifacts.py`
- Modify: `tests/test_pipeline.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`

**Preconditions:**
- Task 3 pipeline path passes focused tests

**Steps:**
- [x] Delete `handle_cv_analysis_reranker_skip`,
      `handle_cv_analysis_reused_record`, and
      `handle_cv_analysis_compute_branch` after confirming no callers remain.
- [x] Remove helper-only imports and callable parameters made dead by deletion.
- [x] Keep batch iteration and generation-ready selection helpers only where they
      still reduce real duplication.
- [x] Replace local readiness string checks with canonical status constant or
      `is_generation_ready` where doing so removes duplicated meaning.
- [x] Verify observation, stage-artifact, and common projection helpers consume
      canonical fields without synthesizing missing defaults or recomputing
      status.
- [x] Delete tests that only prove removed helper placement; retain tests proving
      output and orchestration contracts.

**Verification:**
- [x] `rg -n "handle_cv_analysis_(reranker_skip|reused_record|compute_branch)|def _build_cv_analysis_record|def _attach_analysis_input_components|def _analysis_input_components|run_agentic_cv_analysis" src tests`
- [x] residue command returns no active implementation or test references
- [x] `python -m pytest tests/test_pipeline.py -k cv_analysis -q`

**Exit Criteria:**
- no second CV-analysis semantic helper surface remains outside canonical module

### Task 5: Verify downstream projections and refresh owned docs

**Purpose:**
- prove one Python record contract across worker/control-plane consumers and
  synchronize only affected documentation

**Files:**
- Verify: `src/fitcv_cp/worker_job.py`
- Verify: `src/fitcv_cp/app.py`
- Modify if stale: `docs/stages/cv_analysis.source.yaml`
- Generated if source changed: `docs/stages/cv_analysis.yaml`
- Modify if stale: `docs/pipeline.md`
- Modify if stale: `docs/architecture.md`
- Generated if metadata changed: `docs/generated/architecture_dag.yaml`
- Generated if metadata changed: `docs/generated/capability_lineage.yaml`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-4 pass focused analyzer and pipeline tests

**Steps:**
- [x] Update worker/control-plane fixtures to canonical record shape; do not add
      compatibility hydration in production consumers.
- [x] Verify worker summary counts and omission reasons still distinguish all
      four CV-analysis statuses.
- [x] Verify control-plane stage timelines and pipeline outcomes consume
      canonical status and error fields unchanged.
- [x] Inspect stage, pipeline, and architecture docs; edit only wording that still
      names pipeline, stage runner, built-in, or agentic branch as semantic owner.
- [x] If `cv_analysis.source.yaml` changes, run architecture metadata generator
      and include generated stage/discovery outputs.
- [x] Regenerate planning lineage after plan status or linkage changes.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_worker_job.py -q`
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py -k "cv_analysis or pipeline_outcome" -q`
- [x] `python tools/docs/generate_architecture_metadata.py --check`
- [x] `python scripts/validate_planning_lifecycle.py`

**Exit Criteria:**
- direct, pipeline, worker, control-plane, replay, and resume Python paths
  consume one record contract; this phase makes no storage-deployment parity
  claim; owned docs and generated surfaces are synchronized

## Verification

Run after all tasks:

```powershell
python -m pytest tests/test_agentic_cv_analysis.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline_stage_resume_parity.py -q
python -m pytest tests/test_pipeline.py -q
python -m pytest tests/test_fitcv_cp/test_worker_job.py -q
python -m pytest tests/test_fitcv_cp/test_app.py -k "cv_analysis or pipeline_outcome" -q
rg -n "handle_cv_analysis_(reranker_skip|reused_record|compute_branch)|def _build_cv_analysis_record|def _attach_analysis_input_components|def _analysis_input_components|run_agentic_cv_analysis" src tests
python tools/docs/generate_architecture_metadata.py --check
python scripts/generate_planning_lineage.py
python scripts/validate_repo_contracts.py --fast
git diff --check
```

Expected residue result: no active matches. If a compatibility fixture must retain
an old label, it must assert observational behavior only and must not patch or
select a second analysis method.

## Execution Evidence

- canonical analyzer suite: 20 passed
- focused late-stage and resume suite: 19 passed
- full pipeline suite: 125 passed
- worker suite: 75 passed
- focused control-plane suite: 17 passed
- architecture metadata check, planning lifecycle validation, and fast repo contract validation passed
- semantic residue searches returned no active pipeline or stage-runner owner
- GitNexus change detection was advisory because the index was stale; source, tests, and validators remained authoritative
- audit-evidence mandate did not trigger because this was planned invariant consolidation, not an unresolved runtime, data, security, or unclear-boundary failure

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

This plan has no child plans. Complete it only when focused and full pipeline
verification pass, residue is empty, canonical docs are synchronized, generated
metadata checks pass, and the Phase 1 spec can move to `status: completed`.

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-12-52-fitcv-llm-runtime-spine-phase-1-cv-analysis-single-owner-spec.md`
- `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- `docs/stages/cv_analysis.source.yaml`
- `src/fitcv/agentic_cv_analysis.py`
- `src/fitcv/late_stage_contract.py`
- `scripts/validate_planning_lifecycle.py`
</LINK>
