---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: shortlist-hybrid-retrieval-implementation-plan
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-late-stage-gating
parent_spec: docs/superpowers/specs/2026-05-28-14-09-shortlist-hybrid-retrieval-spec.md
targets:
  - src/fitcv/vector_search.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stages/common.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_store.py
  - src/fitcv/ranking.py
  - src/fitcv_cp/settings_schema.py
  - tests/test_vector_search.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_runner.py
  - tests/test_pipeline_stage_artifacts.py
  - tests/test_ranking.py
related_features:
  - pipeline_performance
related_stages:
  - shortlist
  - ranking
---

## Goal

Implement hybrid shortlist retrieval (`vector` + `bm25` + `hybrid_rrf`) behind controlled rollout so shortlist recall improves without breaking SSOT boundaries, schema contracts, or cross-engine symmetry between BigQuery and SQLite modes.

## Key Deliverables

### Deliverable 1: Canonical Hybrid Retrieval Contract In Runtime

Shortlist stage exposes one normalized retrieval contract with channel-local raw metrics and canonical fused rank, while preserving existing legacy shortlist keys consumed downstream.

### Deliverable 2: Symmetric Multi-Engine Execution

BigQuery and SQLite paths both produce equivalent normalized channel payloads and deterministic RRF fusion ordering for same inputs.

### Deliverable 3: Safe Shadow-Mode Rollout + Activation Gates

Pipeline supports shadow diagnostics mode, observable quality metrics, and promotion/rollback thresholds before active shortlist membership changes.

## Task/Wave Breakdown

### Task 1: Add Canonical Hybrid Retrieval Config Surface

**Purpose:**
- define single SSOT config surface for hybrid shortlist behavior and rollout mode

**Files:**
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Verify: `tests/test_config.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- parent spec approved for hybrid contract
- existing `pipeline.vector_search_top_n` behavior understood

**Steps:**
- [ ] Step 1: introduce canonical config block for shortlist hybrid controls (enabled flag, mode, per-channel top-K, RRF `k`, activation mode).
- [ ] Step 2: wire compatibility defaults and validation constraints so missing keys preserve current vector-only behavior.
- [ ] Step 3: expose new controls in settings schema with stage ownership mapping to shortlist/ranking where applicable.

**Verification:**
- [ ] `python -m pytest -q tests/test_config.py tests/test_fitcv_cp/test_settings_schema.py`

**Exit Criteria:**
- config loads deterministically with backward-compatible defaults and schema validation coverage

### Task 2: Introduce Shared Retrieval Row Normalization + Fusion Utility

**Purpose:**
- enforce symmetry/invariance by centralizing row normalization and RRF fusion logic

**Files:**
- Inspect: `src/fitcv/pipeline_stages/common.py`
- Inspect: `src/fitcv/vector_search.py`
- Modify: `src/fitcv/pipeline_stages/common.py`
- Modify: `src/fitcv/vector_search.py`
- Verify: `tests/test_vector_search.py`

**Preconditions:**
- Task 1 complete
- existing shortlist row shape (`vector_similarity`, `vector_rank`, `shortlist_origin`) preserved

**Steps:**
- [ ] Step 1: add normalized channel-row schema helpers (`vector_rank`, `bm25_rank`, `hybrid_rank`, `vector_similarity`, `bm25_score`, `rrf_score`, `retrieval_sources`, `retrieval_strategy`).
- [ ] Step 2: implement deterministic RRF fusion utility (stable tie-break using canonical secondary ordering).
- [ ] Step 3: ensure utility keeps channel-local raw score isolation (no mixed pseudo-score).

**Verification:**
- [ ] `python -m pytest -q tests/test_vector_search.py`

**Exit Criteria:**
- one shared normalization/fusion path exists and unit tests assert deterministic fusion behavior

### Task 3: Implement BM25 Retrieval Channel For BigQuery + SQLite

**Purpose:**
- add lexical retrieval channel with same passed-job universe boundary and normalized outputs

**Files:**
- Inspect: `src/fitcv/vector_search.py`
- Modify: `src/fitcv/vector_search.py`
- Verify: `tests/test_vector_search.py`

**Preconditions:**
- Task 2 complete
- channel contract finalized

**Steps:**
- [ ] Step 1: add BigQuery BM25 retrieval query path constrained to same rule-filtered `passed_job_urls` universe.
- [ ] Step 2: add SQLite BM25 retrieval path with equivalent lexical behavior and bounded candidate set.
- [ ] Step 3: emit normalized BM25 rows keyed by `job_url` with stable rank and raw lexical score fields.

**Verification:**
- [ ] `python -m pytest -q tests/test_vector_search.py -k "bm25 or hybrid or shortlist"`

**Exit Criteria:**
- both engines return BM25 channel rows matching canonical normalization contract

### Task 4: Integrate Hybrid Fusion Into Shortlist Stage (Shadow + Active Modes)

**Purpose:**
- wire channel retrieval + fusion into shortlist stage without breaking current scoring-shortlist materialization semantics

**Files:**
- Inspect: `src/fitcv/pipeline_stage_runner.py`
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_runner.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_store.py`
- Verify: `tests/test_pipeline_stage_runner.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Tasks 1-3 complete
- current backfill logic behavior captured

**Steps:**
- [ ] Step 1: update shortlist runner to request vector + bm25 channel outputs and fused outputs from retrieval layer.
- [ ] Step 2: support `shadow` mode where fused outputs are recorded as diagnostics only while shortlist membership remains vector-driven.
- [ ] Step 3: support `active` mode where fused ranking drives shortlist membership before existing backfill and downstream storage.
- [ ] Step 4: preserve existing fallback/backfill semantics and mark origins unambiguously.

**Verification:**
- [ ] `python -m pytest -q tests/test_pipeline_stage_runner.py tests/test_pipeline.py -k shortlist`

**Exit Criteria:**
- shortlist stage supports vector-only, shadow hybrid, and active hybrid with deterministic behavior

### Task 5: Extend Artifacts + Diagnostics Without Breaking Ranking Contract

**Purpose:**
- persist and expose hybrid diagnostics while keeping ranking inputs backward compatible

**Files:**
- Inspect: `src/fitcv/pipeline_stage_artifacts.py`
- Inspect: `src/fitcv/ranking.py`
- Modify: `src/fitcv/pipeline_stage_artifacts.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/test_pipeline_stage_artifacts.py`
- Verify: `tests/test_ranking.py`

**Preconditions:**
- Task 4 complete

**Steps:**
- [ ] Step 1: add artifact payload fields for per-channel rank/score and fusion diagnostics.
- [ ] Step 2: add shortlist quality metrics for overlap/unique-gain/backfill deltas and mode provenance.
- [ ] Step 3: verify ranking stage still reads required legacy fields unchanged (`vector_similarity` contract intact).

**Verification:**
- [ ] `python -m pytest -q tests/test_pipeline_stage_artifacts.py tests/test_ranking.py`

**Exit Criteria:**
- diagnostics are richer, ranking remains backward compatible, and contract tests pass

### Task 6: End-to-End Verification + Rollout Gate Evidence

**Purpose:**
- prove correctness, symmetry, and readiness for activation decision

**Files:**
- Inspect: `tests/test_vector_search.py`
- Inspect: `tests/test_pipeline.py`
- Inspect: `tests/test_pipeline_stage_runner.py`
- Inspect: `tests/test_pipeline_stage_artifacts.py`
- Modify: `tests/test_vector_search.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_stage_runner.py`
- Modify: `tests/test_pipeline_stage_artifacts.py`

**Preconditions:**
- Tasks 1-5 complete

**Steps:**
- [ ] Step 1: add parity tests asserting BigQuery/SQLite produce equivalent normalized fused ordering for shared fixtures.
- [ ] Step 2: add deterministic tests for RRF tie-break and channel-missing behavior.
- [ ] Step 3: add shadow-mode evidence checks ensuring shortlist membership unchanged while diagnostics populate.
- [ ] Step 4: document rollout gate checklist and rollback trigger conditions in test-friendly assertions/comments.

**Verification:**
- [ ] `python -m pytest -q tests/test_vector_search.py tests/test_pipeline.py tests/test_pipeline_stage_runner.py tests/test_pipeline_stage_artifacts.py tests/test_ranking.py`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- hybrid retrieval behavior proven by automated tests and validator passes; rollout gate evidence available for go/no-go decision

## Verification

- `python -m pytest -q tests/test_config.py tests/test_fitcv_cp/test_settings_schema.py`
- `python -m pytest -q tests/test_vector_search.py tests/test_pipeline.py tests/test_pipeline_stage_runner.py tests/test_pipeline_stage_artifacts.py tests/test_ranking.py`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
