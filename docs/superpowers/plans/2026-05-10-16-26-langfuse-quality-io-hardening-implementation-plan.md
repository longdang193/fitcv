---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: langfuse-quality-io-hardening-implementation
parent_thread: workstream-agentic-observability.agentic-observability-provider-provenance
parent_spec: docs/superpowers/specs/2026-05-09-evaluable-langfuse-item-observation-contract-spec.md
targets:
  - src/fitcv/telemetry.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv/test_telemetry.py
  - tests/test_fitcv_cp/test_reporter.py
  - tests/test_pipeline.py
  - docs/observability.md
  - docs/pipeline.md
related_stages:
  - enrich
  - cv_analysis
  - cv_generation
  - acceptance_review
---

# 2026-05-10-16-26 Langfuse Quality IO Hardening Implementation Plan

## Goal

Implement audit-priority readable quality IO hardening across quality stages so top-level trace `input`/`output` are reviewer-usable, bounded, and never undefined on sampled stage traces.

## Key Deliverables

### Deliverable 1: Quality-stage readable IO contract enforcement

Define and enforce stage-level contract where `enrich_item`, `cv_analysis_item`, `cv_generation_item`, and `acceptance_review_item` emit bounded readable `input` and non-empty readable `output`.

### Deliverable 2: Payload domain separation contract

Ensure reviewer-facing summaries remain in top-level `input`/`output`, with evaluable structured fields in `metadata.quality.*` and operational control fields in `metadata.ops.*`.

### Deliverable 3: Verification-ready implementation lane

Provide task-level implementation structure and verification gates proving no undefined quality-stage output and reviewer-fast quality assessment feasibility in Langfuse traces.

## Task/Wave Breakdown

### Task 1: Define telemetry helper contract updates (`telemetry.py`)

**Purpose:**
- Introduce helper-level contract updates for bounded readable IO and payload partitioning.

**Files:**
- Inspect: `src/fitcv/telemetry.py`
- Modify: `src/fitcv/telemetry.py`
- Verify: `tests/test_fitcv/test_telemetry.py`

**Preconditions:**
- Existing Wave 2 plan patch includes audit-priority task 0 requirements.

**Steps:**
- [ ] Step 1: finalize required fields and bounds for readable `input`/`output` across quality stages.
- [ ] Step 2: codify payload partition shape (`metadata.quality.*`, `metadata.ops.*`).
- [ ] Step 3: add guardrails so top-level `output` cannot be emitted empty/undefined.
- [ ] Step 4: add stage-specific summary builder hooks (`enrich`, `cv_analysis`, `cv_generation`, `acceptance_review`).

**Verification:**
- [ ] `python -m pytest tests/test_fitcv/test_telemetry.py -q`

**Exit Criteria:**
- Telemetry helper layer enforces readable IO invariants for all quality stages.

### Task 2: Patch stage emission call sites (`pipeline.py`, `reporter.py`, `worker_job.py`)

**Purpose:**
- Ensure stage emissions use helper contract consistently and preserve lineage.

**Files:**
- Inspect/Modify: `src/fitcv/pipeline.py`
- Inspect/Modify: `src/fitcv_cp/reporter.py`
- Inspect/Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_pipeline.py`, `tests/test_fitcv_cp/test_reporter.py`

**Preconditions:**
- Task 1 helper contract fields and builders are finalized.

**Steps:**
- [ ] Step 1: route `enrich_item` emissions through readable summary builder.
- [ ] Step 2: route `cv_analysis_item` and `cv_generation_item` emissions through readable summary builders.
- [ ] Step 3: route `acceptance_review_item` emission with non-empty `output` guardrail and structured quality metadata.
- [ ] Step 4: verify lineage fields remain stable from generation to acceptance review.

**Verification:**
- [ ] `python -m pytest tests/test_pipeline.py -q -k "langfuse or telemetry or cv_generation or acceptance or review"`
- [ ] `python -m pytest tests/test_fitcv_cp/test_reporter.py -q`

**Exit Criteria:**
- All quality stages emit bounded readable IO with required lineage and metadata partitioning.

### Task 3: Add verification matrix + regression fixtures (tests)

**Purpose:**
- Prove invariants and stage-level observability behavior under normal and degraded telemetry modes.

**Files:**
- Modify/Add: `tests/test_fitcv/test_telemetry.py`
- Modify/Add: `tests/test_pipeline.py`
- Modify/Add: `tests/test_fitcv_cp/test_reporter.py`

**Preconditions:**
- Task 2 call-site wiring complete.

**Steps:**
- [ ] Step 1: add tests that assert no quality-stage `output` is undefined/empty.
- [ ] Step 2: add tests for `metadata.quality.*` vs `metadata.ops.*` separation.
- [ ] Step 3: add bounded-length assertions for stage summaries.
- [ ] Step 4: add degraded/disabled telemetry fallback assertions that preserve non-blocking execution.

**Verification Matrix (Stage-Level Readable IO Contract):**

| Stage | Required readable `input` | Required readable `output` | Bounded summary assertion | Metadata domain assertion |
|---|---|---|---|---|
| `enrich_item` | source excerpt + normalization context present | extraction/delta summary non-empty | output length capped + truncation marker when capped | quality facts in `metadata.quality.*`; provenance/config in `metadata.ops.*` |
| `cv_analysis_item` | candidate+job analysis context present | fit/reason summary non-empty | output length capped + truncation marker when capped | fit/score rationale under `metadata.quality.*`; routing/model/config under `metadata.ops.*` |
| `cv_generation_item` | selected prompt/context present | generated CV + validation summary non-empty | output length capped + truncation marker when capped | validation/quality indicators under `metadata.quality.*`; provider/run control under `metadata.ops.*` |
| `acceptance_review_item` | review decision context present | action+rationale summary non-empty | output length capped + truncation marker when capped | review quality signals under `metadata.quality.*`; operator/system provenance under `metadata.ops.*` |

**Verification:**
- [ ] `python -m pytest tests/test_fitcv/test_telemetry.py -q`
- [ ] `python -m pytest tests/test_pipeline.py -q -k "langfuse or telemetry or cv_generation or acceptance or review"`
- [ ] `python -m pytest tests/test_fitcv_cp/test_reporter.py -q`

**Exit Criteria:**
- Tests enforce readable IO, metadata split, bounded summaries, and fallback behavior.

### Task 4: Docs and operator-readability contract alignment (`docs/observability.md`, `docs/pipeline.md`)

**Purpose:**
- Publish contract so implementation and review practice remain synchronized.

**Files:**
- Modify: `docs/observability.md`
- Modify: `docs/pipeline.md`

**Preconditions:**
- Task 1–3 behavior and tests finalized.

**Steps:**
- [ ] Step 1: document quality-stage readable IO invariants and summary intent per stage.
- [ ] Step 2: document `metadata.quality.*` and `metadata.ops.*` separation contract.
- [ ] Step 3: add reviewer workflow note for sub-15-second trace inspection target.

**Verification:**
- [ ] manual review of docs against code/test behavior

**Exit Criteria:**
- Docs accurately reflect final hardening behavior and reviewer usage expectations.

### Task 5: Final validation + rollback boundaries

**Purpose:**
- Confirm lane safety and retain Wave 1 compatibility.

**Files:**
- Verify affected files above

**Preconditions:**
- Task 1–4 complete.

**Steps:**
- [ ] Step 1: run test subset and planning/contract validators.
- [ ] Step 2: verify rollback guidance preserves Wave 1 run-summary behavior.
- [ ] Step 3: produce concise handoff for execution closeout.

**Rollback Boundaries (Explicit):**

- Rollback scope is limited to quality-stage readable IO hardening additions:
  - stage summary builders
  - stage-level non-empty `output` guardrails
  - `metadata.quality.*` / `metadata.ops.*` partition refinements
- Rollback must not remove or alter Wave 1 run-summary aggregate telemetry fields, counters, or disposition semantics.
- Rollback must preserve existing Wave 1 lineage chain identifiers already consumed by downstream run-level reporting.
- Rollback execution strategy:
  1. disable new quality-stage summary-builder wiring behind feature/config flag or revert bounded helper patch
  2. keep baseline item observation emission path active where previously supported
  3. rerun Wave 1 regression slices to prove run-summary parity
- Rollback acceptance gate:
  - run-summary outputs remain schema-compatible with pre-hardening snapshots
  - no regression in aggregate metrics visibility (`analysis`, `generation`, acceptance aggregates)
  - degraded telemetry mode remains non-blocking for pipeline execution

**Verification:**
- [ ] `python -m pytest tests/test_fitcv/test_telemetry.py -q`
- [ ] `python -m pytest tests/test_fitcv_cp/test_reporter.py -q`
- [ ] `python -m pytest tests/test_pipeline.py -q -k "langfuse or telemetry or cv_generation or acceptance or review"`
- [ ] `python scripts/validate_template_required_sections.py`
- [ ] `python scripts/validate_planning_lifecycle.py --strict`

**Exit Criteria:**
- Quality IO hardening implementation lane is validated, rollback-aware, and handoff-ready.

## Verification

```powershell
python -m pytest tests/test_fitcv/test_telemetry.py -q
python scripts/validate_template_required_sections.py
python scripts/validate_planning_lifecycle.py --strict
```

## Completion Criteria

A plan item is considered complete when:

1. implementation plan frontmatter and lineage fields remain valid for change-layer execution.
2. required template sections exist and remain consistent with implementation-plan contract.
3. implementation tasks provide executable path to satisfy patched Wave 2 quality IO invariants.
