---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: shortlist-hybrid-retrieval-spec
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-late-stage-gating
targets:
  - src/fitcv/vector_search.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stages/common.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/ranking.py
  - src/fitcv_cp/settings_schema.py
related_features:
  - pipeline_performance
related_stages:
  - shortlist
  - ranking
---

## Goal

Define SSOT-safe hybrid shortlist retrieval design that combines lexical BM25 recall with existing cosine vector recall, while preserving current shortlist/ranking contracts and enforcing structural symmetry and invariance across SQLite and BigQuery execution modes.

## Key Deliverables

### Hybrid Retrieval Architecture Contract

Specify one canonical shortlist retrieval contract with two retrieval channels (`vector`, `bm25`) and one canonical fusion channel (`hybrid_rrf`), including ownership boundaries and normalized output shape.

### Score and Rank Normalization Contract

Specify canonical row schema carrying per-channel raw signals and canonical fused rank, without mixing incompatible score scales into single pseudo-score.

### Validation and Rollout Contract

Specify shadow-mode rollout, acceptance criteria, invariants, and measurable promotion gates before implementation activation.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- define current shortlist behavior and contract edges before introducing hybrid retrieval

**Steps:**
- [ ] confirm current shortlist scoring signal source in `src/fitcv/vector_search.py`
- [ ] confirm shortlist materialization/backfill contract in `src/fitcv/pipeline.py`
- [ ] confirm stage execution and persistence boundaries in `src/fitcv/pipeline_stage_runner.py` and `src/fitcv/pipeline_store.py`
- [ ] confirm downstream ranking consumption contract in `src/fitcv/ranking.py`

**Verification:**
- [ ] current raw shortlist contract and scoring-shortlist contract are explicitly separated

**Exit Criteria:**
- no hybrid design decision depends on unstated assumptions about current shortlist fields

### Wave 2: Decision closure

**Purpose:**
- finalize hybrid architecture, schema, and rollout mode

**Steps:**
- [ ] define retrieval-channel symmetry requirements
- [ ] define canonical fusion algorithm and tie-breaking
- [ ] define SSOT field ownership by stage/function
- [ ] define configuration surfaces and defaults

**Verification:**
- [ ] every major hybrid decision has chosen approach, alternatives, and downstream impact

**Exit Criteria:**
- design is bounded, internally coherent, and implementation-plan ready

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof obligations explicit before coding

**Steps:**
- [ ] define test matrix for BigQuery and SQLite paths
- [ ] define shadow-mode evidence outputs
- [ ] define promotion thresholds and rollback triggers

**Verification:**
- [ ] validation plan proves recall gain claims without violating shortlist/ranking invariants

**Exit Criteria:**
- spec can be approved and handed off to implementation planning

## Design Decisions

### Decision: Keep vector similarity as first-class SSOT signal, add BM25 as parallel first-class signal

- context: current shortlist uses cosine-only retrieval with `vector_similarity` and `vector_rank`; lexical misses remain possible for acronym/tool/version-heavy queries.
- choice: run two independent retrieval channels over same passed-job universe: `vector` and `bm25`.
- alternatives considered:
  - vector-only with larger top-N
  - weighted score blending `alpha * cosine + beta * bm25`
- impact:
  - preserves existing vector contract for backward compatibility
  - introduces explicit lexical channel without score-scale coupling

### Decision: Use Reciprocal Rank Fusion (RRF) as canonical fusion method

- context: cosine and BM25 raw scores are not directly comparable across distributions/providers.
- choice: fuse by rank using RRF, not raw-score weighted sum.
- alternatives considered:
  - min-max normalize then weighted sum
  - z-score normalize then weighted sum
  - learning-to-rank in shortlist stage
- impact:
  - invariance to raw score scale drift
  - reduced tuning sensitivity
  - deterministic fused ordering from rank positions

### Decision: One canonical shortlist row schema with channel-specific raw fields

- context: downstream code already depends on `vector_similarity`, `vector_rank`, `shortlist_origin`, and ranking-stage fields.
- choice: extend shortlist row shape with additive channel fields while keeping legacy fields valid.
- alternatives considered:
  - replace existing fields with generic map
  - store separate shortlist tables per retriever
- impact:
  - preserves existing interfaces and auditability
  - enables diagnostics without breaking current ranking ingestion

### Decision: Shadow mode first, activation second

- context: retrieval changes can affect ranking mix and CV generation outcomes.
- choice: first compute hybrid diagnostics without changing scoring shortlist membership; activate only after gates pass.
- alternatives considered:
  - direct cutover
  - per-run manual toggle without shadow baseline
- impact:
  - safe rollout with measurable gain/loss evidence
  - clear rollback path

### Decision: Enforce structural symmetry across execution engines

- context: shortlist logic runs on both SQLite and BigQuery paths.
- choice: retrieval-stage abstractions expose same channel outputs, same fusion logic, same row schema, same tie-break rules in both modes.
- alternatives considered:
  - implement hybrid only in BigQuery path first
- impact:
  - avoids environment-specific behavior drift
  - keeps invariants verifiable in unit/integration tests

## Invariants

- shortlist retrieval universe remains rule-filtered passed-job set only; hybrid cannot bypass stage filters.
- `vector_similarity` remains cosine-derived signal and remains populated for vector-returned rows.
- BM25 raw score remains channel-local (`bm25_score`) and is never coerced into `vector_similarity`.
- shortlist-to-ranking interface remains backward compatible for existing required fields.
- fusion ranking is deterministic given same candidate query and same retrieval inputs.
- backfill semantics remain explicit and distinguishable from retrieval returns.
- SSOT for retrieval orchestration remains shortlist stage (`run_vector_search` successor boundary), not duplicated in ranking stage.
- channel symmetry holds: each retrieval channel emits normalized row payload through single normalization path before fusion.
- no hidden special cases per source unless mathematically/operationally required and documented.

## Acceptance Criteria

- hybrid shortlist design defines exact canonical fields, ownership, and tie-breaking.
- both SQLite and BigQuery paths have equivalent behavior for retrieval channel normalization and fusion ranking.
- ranking stage receives same required legacy fields as today with additive hybrid diagnostics.
- shadow mode emits sufficient metrics to decide activation without ambiguity.
- promotion thresholds and rollback triggers are explicitly documented and testable.

## Non-Goals

- no implementation of BM25 index/provider in this spec.
- no learning-to-rank model design.
- no redesign of ranking final-score formula in this spec.
- no CV-generation policy change.

## Risks and Mitigations

- risk: lexical channel increases noisy shortlist entries.
  - mitigation: shadow-mode compare precision proxies (strong/stretch rates, final top-N quality deltas) before activation.
- risk: schema drift between shortlist artifacts and ranking consumers.
  - mitigation: additive-only schema evolution with contract tests for required legacy keys.
- risk: BigQuery/SQLite divergence.
  - mitigation: shared normalization/fusion utility and parity tests across both execution modes.
- risk: configuration sprawl.
  - mitigation: single canonical config block for hybrid shortlist controls with explicit defaults and compatibility projection rules.

## Validation Plan

- proof target: current-state retrieval contract is accurately captured
  - method: source inspection
  - evidence: references in `src/fitcv/vector_search.py`, `src/fitcv/pipeline.py`, and `src/fitcv/pipeline_stage_runner.py`

- proof target: hybrid schema preserves backward compatibility
  - method: contract tests
  - evidence: tests asserting required legacy shortlist and ranking keys remain present and semantically unchanged

- proof target: fusion is deterministic and scale-invariant
  - method: unit tests with fixed ranked inputs and perturbed raw score scales
  - evidence: identical fused ordering under score-scale perturbation when ranks unchanged

- proof target: BigQuery and SQLite paths are behaviorally symmetric
  - method: parity tests with shared fixtures
  - evidence: equivalent normalized channel rows and fused shortlist ordering for same mock corpus/query

- proof target: activation decision is evidence-based
  - method: shadow-run metrics comparison over defined evaluation window
  - evidence: run-level report showing overlap@N, unique_gain@N, backfill_rate delta, and quality-label deltas against thresholds

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

## Triage

Layer: change
Feature type: MODIFY
Summary: Add hybrid shortlist retrieval design (vector + BM25 + RRF fusion) with SSOT-safe contracts.
Reasoning: Existing shortlist contract is stable and bounded; change affects retrieval behavior and shortlist artifacts, not roadmap/workstream ownership.
Invariants:
- shortlist stage owns retrieval orchestration and normalization
- ranking contract backward compatibility maintained
Dependencies:
- retrieval channel implementation for BM25
- shortlist artifact schema extension
Affected stages:
- shortlist
- ranking
Affected features:
- pipeline_performance
Primary lens: mixed
Affected docs:
- feature_source: none
- feature_yaml: none
- feature_lineage: none
- feature_history: none
- stage_source: none
- stage_contract: none
- feature_docs:
  - none
- cross_cutting_docs:
  - docs/pipeline.md
- readme: none
- generated:
  - none
Generated refresh required: no
Capability IDs:
- none
Invariant IDs:
- none
Spec needed: yes
Plan needed: yes

## Open Questions

- BM25 backend choice for BigQuery mode: native search index, external service, or precomputed sparse vectors.
- BM25 strategy for SQLite mode: local FTS table vs. in-memory scoring.
- Activation gate thresholds: exact numeric bounds for unique gain and quality regression tolerance.


