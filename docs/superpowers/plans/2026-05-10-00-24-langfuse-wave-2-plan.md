---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: langfuse-wave-2-observability-integration
parent_thread: workstream-agentic-observability.agentic-observability-provider-provenance
parent_spec: docs/superpowers/specs/2026-05-09-evaluable-langfuse-item-observation-contract-spec.md
targets:
  - docs/observability.md
  - docs/pipeline.md
  - src/fitcv/telemetry.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/worker_job.py
  - scripts/
  - tests/test_fitcv/test_telemetry.py
  - tests/test_fitcv_cp/test_reporter.py
  - tests/test_pipeline.py
related_stages:
  - cv_analysis
  - cv_generation
  - acceptance_review
---

# 2026-05-10 Langfuse Wave 2 Observability Integration Plan

## Goal

Implement Wave 2 observability contract on top of existing Wave 1 Langfuse item telemetry by adding a truthful `acceptance_review_item` observation lane and a downstream evaluator/export lane, while preserving run-summary boundaries and stable lineage across `cv_analysis_item` -> `cv_generation_item` -> `acceptance_review_item` for deterministic review and offline evaluation.

## Key Deliverables

### Acceptance review observation contract

- Add canonical `acceptance_review_item` emission with strict enum validation for review action (`approved`, `rejected`, `changes_requested`, `approved_with_warnings`).
- Enforce lineage to generation attempt via required `source_generation_version_id` and linkable observation metadata.
- Preserve reviewer-first rendered `input`/`output` plus structured backing metadata for automation.

### Evaluator/export data products

- Add export path that materializes Wave 2 evaluator rows without reparsing rendered markdown.
- Support bounded JSONL and CSV outputs for downstream analysis.
- Include stable filter fields: `review_required`, `review_action`, `grounding_violations_count`, `skill_violations_count`, `validation_status`, `fit_label`, `prompt_version`, `provider`, `model`, `selected_attempt`, `source_generation_version_id`.

### Cross-cutting contract alignment and fixtures

- Keep Wave 1 run-level aggregate telemetry unchanged.
- Add tests and fixtures that prove schema, lineage, bounded payload behavior, and export row integrity across success, rejection, warning-accept, and change-request paths.
- Update docs to publish Wave 2 contract boundaries and handoff guidance.

## Task Breakdown

### task 1: lock Wave 2 contract boundaries and ownership

**Files:**
- Inspect: `src/fitcv/telemetry.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/reporter.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect tests: `tests/test_fitcv/test_telemetry.py`, `tests/test_fitcv_cp/test_reporter.py`, `tests/test_pipeline.py`

- [ ] Step 1: confirm exact emission boundary where final acceptance decision becomes truthful and durable.
- [ ] Step 2: map current Wave 1 lineage fields and decide canonical parent linkage for `acceptance_review_item`.
- [ ] Step 3: define required vs optional Wave 2 metadata fields and bounded limits.
- [ ] Step 4: confirm run-summary surfaces remain aggregate-only and do not shadow-store full item IO.

### task 2: implement `acceptance_review_item` schema helper and guardrails

**Files:**
- Modify: `src/fitcv/telemetry.py`
- Modify/Add tests: `tests/test_fitcv/test_telemetry.py`

- [ ] Step 1: add helper builder for `acceptance_review_item` envelope with required fields:
  - `observation_type`, `schema_version`, `redaction_version`
  - `run_id`, `candidate_id`, `job_id`, `attempt_id`, `attempt_index`, `selected`
  - `source_generation_version_id`, `parent_observation_id`
  - `review_action`, `review_actor_type`, `review_status`, `review_required`
  - rendered `input`, rendered `output`, structured `metadata`.
- [ ] Step 2: enforce review-action enum and reject unknown values at helper boundary.
- [ ] Step 3: bound all free-text reviewer fields and issue lists with explicit truncation markers.
- [ ] Step 4: include normalization helpers for booleans, indexes, and nullable fields aligned with Wave 1 style.
- [ ] Step 5: preserve non-blocking telemetry behavior when exporters are disabled or degraded.

### task 3: emit `acceptance_review_item` at truthful pipeline boundary

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/reporter.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify/Add tests: `tests/test_pipeline.py`, `tests/test_fitcv_cp/test_reporter.py`

- [ ] Step 1: patch acceptance decision boundary to emit one `acceptance_review_item` per finalized review decision.
- [ ] Step 2: wire parent-child lineage to selected `cv_generation_item` attempt and include `source_generation_version_id`.
- [ ] Step 3: capture review context in structured metadata (reason codes, warning counts, override flags, operator note excerpts).
- [ ] Step 4: keep terminal disposition semantics distinguishable (`approved`, `rejected`, `changes_requested`, `approved_with_warnings`).
- [ ] Step 5: verify no duplicate emission for retried/edited review actions unless spec declares versioned review attempts.

### task 4: build evaluator/export integration lane

**Files:**
- Modify/Add: `scripts/` (Wave 2 export utility module/script)
- Modify: `src/fitcv_cp/reporter.py` and/or existing export ownership surface
- Modify/Add tests: export-focused tests near owning modules

- [ ] Step 1: implement extractor that reads structured observation metadata instead of rendered markdown.
- [ ] Step 2: produce normalized evaluator rows with stable primary keys (`run_id`, `job_id`, `candidate_id`, `source_generation_version_id`, `review_event_id`).
- [ ] Step 3: support JSONL + CSV outputs with consistent field ordering and null-handling.
- [ ] Step 4: add filter knobs for evaluator workflows (`review_required`, violation counts, action, provider/model, prompt version).
- [ ] Step 5: enforce bounded export behavior for large runs and emit summary counts for dropped/truncated rows.

### task 5: docs alignment and verification fixtures

**Files:**
- Modify: `docs/observability.md`
- Modify: `docs/pipeline.md`
- Modify/Add tests: `tests/test_fitcv/test_telemetry.py`, `tests/test_pipeline.py`, `tests/test_fitcv_cp/test_reporter.py`

- [ ] Step 1: document Wave 2 two-lane contract and explicit boundaries vs Wave 1.
- [ ] Step 2: publish `acceptance_review_item` schema table with required fields and enum values.
- [ ] Step 3: publish evaluator/export field contract and sample row semantics.
- [ ] Step 4: add fixtures for paths:
  - accepted clean
  - approved with warnings
  - rejected
  - changes requested
  - telemetry degraded/disabled fallback.
- [ ] Step 5: confirm fixtures validate lineage chain from analysis through generation to acceptance review.

### task 6: rollout containment and rollback notes

**Files:**
- Inspect/Modify as needed: `src/fitcv/telemetry.py`, `src/fitcv/pipeline.py`, export utility surface

- [ ] Step 1: gate Wave 2 emission/export with bounded config toggles if needed for incremental rollout.
- [ ] Step 2: define rollback method: disable Wave 2 emission + export path in one patch without breaking Wave 1 telemetry.
- [ ] Step 3: verify rollback leaves run-summary and Wave 1 item observations intact.

## Verification

```powershell
python -m pytest tests/test_fitcv/test_telemetry.py -q
python -m pytest tests/test_fitcv_cp/test_reporter.py -q
python -m pytest tests/test_pipeline.py -q -k "langfuse or telemetry or cv_generation or acceptance or review"
python scripts/validate_template_required_sections.py
python scripts/validate_planning_lifecycle.py --strict
python scripts/validate_repo_contracts.py --fast
```

Optional export verification lane:

```powershell
# execute one run with Langfuse enabled and at least one review-required item
# trigger acceptance decisions across at least two action types
# run Wave 2 evaluator export utility for JSONL + CSV outputs
# confirm exported rows join to source_generation_version_id and run_id
# confirm filter fields operate without parsing markdown payloads
```

## Completion Criteria

A plan item is considered complete when:

1. `acceptance_review_item` observation emits at truthful boundary with enforced action enum and required lineage fields.
2. Wave 2 export lane produces stable evaluator-ready JSONL/CSV rows from structured metadata.
3. Wave 1 run-summary and item-observation behavior remains backward compatible and separate from evaluator export concerns.
4. fixtures and tests pass for approval/rejection/change-request/warning-accept paths plus degraded telemetry path.
5. docs describe Wave 2 contract, dependencies, and rollout/rollback boundaries clearly for execution handoff.
6. planning lifecycle and template validators pass without introducing contract drift.

## Lifecycle Evidence Reconciliation (2026-05-10)

- Lane closeout action executed for bounded hotfix slice (local export + 429 retry resilience).
- Scope merged to `main` via PR:
  - `https://github.com/longdang193/fitcv/pull/18`
- Merge commit on `main`:
  - `7916b86afbfa0e2042352c0fd6a3411ac797a904`
- Checkpoint result pack:
  - `docs/intent/workstreams/checkpoints/workstream-agentic-observability/agentic-observability-provider-provenance/20260510-1325.md`
- Verification evidence captured in checkpoint pack includes targeted regression pass:
  - `tests/test_enrich.py` -> `69 passed in 1.85s`
- Residual risk explicitly accepted by operator for lane closure:
  - repo-level GitHub Actions failures remain open and are treated as follow-up debt outside this bounded merge action.
