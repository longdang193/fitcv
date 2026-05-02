---
layer: workstream
artifact_type: plan
status: proposed
parent_thread: workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-policy-versioned-stage-result-envelope
parent_spec: docs/superpowers/specs/2026-05-02-phase-2-policy-versioned-stage-result-spec.md
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/validator.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/reporter.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - docs/observability.md
related_features:
  - inspection_debugging
  - trigger_run_management
  - cv_system
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 2 Plan E StageResult Runtime Contract

**Spec Set:**
- `docs/superpowers/specs/2026-05-02-observability-evidence-control-docs-alignment-spec.md`
- `docs/superpowers/specs/2026-05-02-phase-2-policy-versioned-stage-result-spec.md`
- `docs/superpowers/specs/2026-05-02-phase-2-observability-otel-trace-context-spec.md`

**Implementation Execution Map:** `docs/superpowers/execution_maps/2026-05-02-phase-2-observability-evidence-control-implementation-execution-map.md`

**Goal:** Implement a first-class runtime `StageResult` contract so stage outcomes are persisted and inspectable as:

`{ output, evidence, validation, decision, policy_version, trace_context }`

This is the first code-delivery plan in Phase 2 and must produce behavior changes plus tests.

## Scope

- introduce a canonical StageResult payload shape at runtime
- attach StageResult entries to stage artifacts and run-scoped snapshots
- include policy-version and trace-context fields in StageResult records
- preserve existing operator exports/routes while augmenting contracts

## Non-Goals

- full OpenTelemetry backend integration (only OTel-compatible field shape in this plan)
- storage backend migration (BigQuery -> Postgres/SQLite)
- full degraded/full/local runtime mode behavior changes (deferred to Plan H)

## Execution-Pass Checkpoint Requirement

Each bounded-thread execution pass in this plan must publish one checkpoint result pack.

Required:

- create/update one pack per meaningful execution pass
- store pack at `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- follow `docs/operating_system/templates/checkpoint-result-pack.md`
- mark status as `pass`, `partial`, or `fail`
- include intent, actions, visible output, and next decision

## Key Invariants

- existing stage semantics and stage order remain unchanged
- deterministic acceptance authority remains in policy/validation layer
- no loss of existing run export compatibility for current control-plane routes
- StageResult contract is additive-safe where legacy consumers still read old fields

## Runtime Contract (v1)

Each stage record must provide:

- `stage_id`
- `stage_version` (initial static string allowed)
- `output` (bounded stage-owned output summary)
- `evidence` (stage-owned supporting facts)
- `validation`:
  - `checks`
  - `summary`
- `decision` (`pass` | `fail` | `manual_review` | `not_applicable`)
- `policy_version`
- `trace_context`:
  - `trace_id`
  - `span_id`
  - `parent_span_id`

## Task 1: Contract Shape And Builder Helpers

**Files:**
- Modify:
  - `src/fitcv/pipeline.py`
  - `src/fitcv/validator.py` (if helper constants/policy version wiring is needed)

- [ ] Step 1: Add bounded helper(s) to build StageResult entries with consistent keys.
- [ ] Step 2: Define per-stage default `policy_version` and `stage_version` values.
- [ ] Step 3: Add minimal trace_context generation/path threading (compatible placeholders allowed where upstream IDs are unavailable).

## Task 2: Stage-Level Integration In Pipeline

**Files:**
- Modify:
  - `src/fitcv/pipeline.py`

- [ ] Step 1: Build StageResult entries for each pipeline stage:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
- [ ] Step 2: Ensure `decision` aligns with existing stage-owned status truth.
- [ ] Step 3: Ensure failed/blocked/skipped outcomes are represented explicitly, not collapsed.

## Task 3: Snapshot Persistence And Export Surface Wiring

**Files:**
- Modify:
  - `src/fitcv_cp/worker_job.py`
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/reporter.py` (only if needed for trace-context handoff)

- [ ] Step 1: Persist StageResult payloads in run-scoped snapshots without breaking current artifact paths.
- [ ] Step 2: Ensure stage artifact downloads expose StageResult blocks.
- [ ] Step 3: Keep existing run exports stable; add StageResult contract as additive structured data.

## Task 4: Tests (Contract + Regression)

**Files:**
- Modify:
  - `tests/test_pipeline.py`
  - `tests/test_pipeline_agentic_late_stage.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
  - `tests/test_fitcv_cp/test_app.py`

- [ ] Step 1: Add failing tests for StageResult contract presence and key fields.
- [ ] Step 2: Add tests for pass/fail/manual_review/not_applicable decision coverage.
- [ ] Step 3: Add compatibility tests ensuring existing export endpoints remain functional.

## Task 5: Observability Doc Touch-Up (Narrow)

**Files:**
- Modify:
  - `docs/observability.md`

- [ ] Step 1: Document where StageResult appears in run artifacts.
- [ ] Step 2: Clarify StageResult `decision` is policy-owned; trace_context is observability-owned.

## Verification

Run at minimum:

```powershell
python -m pytest tests/test_pipeline.py
python -m pytest tests/test_pipeline_agentic_late_stage.py
python -m pytest tests/test_fitcv_cp/test_worker_job.py
python -m pytest tests/test_fitcv_cp/test_app.py
python scripts/validate_repo_contracts.py --fast
python scripts/validate_checkpoint_packs.py
```

## Exit Criteria

1. StageResult contract exists across all pipeline stages.
2. StageResult records include `policy_version` and `trace_context`.
3. Stage artifacts and run snapshots expose StageResult entries.
4. Existing operator routes/exports remain compatible.
5. Tests and repo contract validation pass.
