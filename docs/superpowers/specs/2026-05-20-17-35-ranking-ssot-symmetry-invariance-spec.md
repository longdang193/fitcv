---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: ranking-ssot-symmetry-invariance
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-late-stage-gating
targets:
  - src/fitcv/ranking.py
  - src/fitcv/gap_analysis.py
  - src/fitcv/ai_score.py
  - src/fitcv/pipeline.py
  - src/fitcv/ranking_contract.py
  - src/fitcv/persistence.py
related_features:
  - cv_system
related_stages:
  - ranking
---

## Goal

Define and execute bounded refactor removing SSOT drift, structural asymmetry, and invariant gaps across ranking, gap analysis, and AI scoring.

## Key Deliverables

### Shared ranking contract module

Single contract surface for fit-label thresholds, fit-label derivation, threshold validation, and ranking weight/default validation.

### Shared persistence helper module

Single helper surface for local SQLite path resolution and BigQuery client construction.

### Scoped compatibility-preserving patches

Refactor target modules to consume shared contracts/helpers while preserving runtime behavior except explicitly corrected inconsistencies.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm divergences and high-risk edges across scoped files and key caller in pipeline

**Steps:**
- [x] inspect `ranking.py`, `gap_analysis.py`, `ai_score.py`
- [x] inspect fit-label caller duplication in `pipeline.py`
- [x] inspect stale/unused surfaces and persistence duplication

**Verification:**
- [x] finding matrix mapped to concrete symbols and files

**Exit Criteria:**
- every patch traces to explicit finding

### Wave 2: Decision closure

**Purpose:**
- lock implementation shape for RF-01..RF-05

**Steps:**
- [x] RF-01: introduce `ranking_contract.py`
- [x] RF-02: normalize normalization invariants via explicit helper usage and contract checks (bounded)
- [x] RF-03: introduce `persistence.py`
- [x] RF-04: remove/contain obsolete API surfaces with compatibility guard
- [x] RF-05: enforce config invariants via validation helper calls

**Verification:**
- [ ] no duplicate fit-label threshold logic remains in scoped paths
- [ ] no duplicate local sqlite path helper remains in scoped paths

**Exit Criteria:**
- changes are internally coherent and bounded

### Wave 3: Validation and approval readiness

**Purpose:**
- prove invariant preservation and controlled behavior corrections

**Steps:**
- [ ] run targeted tests for ranking/gap/ai_score and any affected pipeline tests
- [ ] run lint/type checks for touched modules
- [ ] verify no unintended symbol/process drift

**Verification:**
- [ ] validation evidence captured from test outputs

**Exit Criteria:**
- patch set is merge-ready or residual risks explicitly documented

## Design Decisions

### Decision: Centralize fit-label thresholds and mapping (RF-01)

- context: threshold/mapping logic duplicated in ai_score and pipeline
- choice: move defaults, extraction, and label derivation into `fitcv.ranking_contract`
- alternatives considered:
  - keep duplication with comments
- impact:
  - removes drift risk and guarantees identical fit-label mapping behavior

### Decision: Centralize persistence primitives (RF-03)

- context: sqlite path and BigQuery client logic repeated across modules
- choice: add `fitcv.persistence` helper functions and consume in scoped modules
- alternatives considered:
  - local helper copy with naming convention
- impact:
  - lower maintenance and consistent auth/path handling

### Decision: Enforce ranking config invariants in resolver layer (RF-05)

- context: weights/defaults/thresholds accepted without hard validation
- choice: validate and normalize contracts in shared module; callers consume validated outputs
- alternatives considered:
  - validate only in config loading layer
- impact:
  - earlier failure for invalid configs; prevents latent scoring defects

### Decision: Obsolete API containment with compatibility-safe behavior (RF-04)

- context: unused helper and unused parameter surfaces create confusion
- choice: remove unused helper; keep parameter but mark compatibility path and avoid silent semantics drift
- alternatives considered:
  - hard remove parameter now
- impact:
  - cleans dead code without caller breakage

### Decision: Parse hardening for malformed reranker payloads

- context: `float(raw)` can raise for non-numeric ai_score despite valid JSON
- choice: add numeric-coercion guard with fallback parser status
- alternatives considered:
  - reject entire response aggressively
- impact:
  - safer runtime behavior in degraded model outputs

## Invariants

- fit-label mapping from ai_score must be identical across all call sites
- default threshold semantics remain strong>=stretch with existing default values
- ranking feature contract keys remain unchanged
- persistence table schemas and column names remain unchanged
- sqlite-mode and BigQuery-mode behavior remain both supported

## Validation Plan

- proof target: fit-label mapping is SSOT
  - method: unit tests for shared mapper + caller integration checks
  - evidence: passing tests showing ai_score and pipeline produce same labels for same thresholds
- proof target: persistence symmetry
  - method: integration tests in sqlite mode and mocked bq mode
  - evidence: passing writes for gap/ai_score/ranking
- proof target: parse hardening
  - method: unit tests for non-numeric and malformed payloads
  - evidence: parser returns safe defaults with explicit parser_status
- proof target: config invariant enforcement
  - method: unit tests for invalid thresholds and invalid weight sums
  - evidence: deterministic validation errors raised

## Acceptance Criteria

- RF-01..RF-05 code changes land in bounded files
- all matrix issues from prior finding set are addressed or explicitly downgraded with rationale
- no duplicated fit-label threshold code remains in scoped flow
- no duplicated local sqlite path helper remains in scoped flow

## Non-Goals

- broad redesign of ranking formulas or business semantics
- large-scale pipeline architecture rewrite
- changing external storage schemas

## Risks and Mitigations

- risk: validation strictness breaks permissive configs
  - mitigation: normalize where safe, raise only on true invariant violations
- risk: helper extraction changes behavior subtly
  - mitigation: preserve interfaces and defaults; add regression tests
- risk: stale GitNexus limits impact confidence
  - mitigation: source-first review + targeted tests + explicit residual risk note

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
