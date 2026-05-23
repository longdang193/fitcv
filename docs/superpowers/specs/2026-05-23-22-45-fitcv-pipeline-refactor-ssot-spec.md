---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-pipeline-ssot-symmetry-invariance-refactor
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-operator-diagnostics
targets:
  - src/fitcv/pipeline.py
  - tests/test_pipeline.py
related_features: []
related_stages: []
---

# FitCV pipeline refactor: SSOT + symmetry + invariance

## Goal

Refactor `src/fitcv/pipeline.py` to remove contract drift and hidden duplication by establishing single-source-of-truth (SSOT) for:

- pipeline stage identifiers and sequencing
- pipeline/runtime status and reason-code taxonomies
- pipeline configuration defaults + validation rules
- pipeline checkpoint/state schema boundaries

Do this without changing external behavior, except where explicitly defined as a deliberate “fail-fast vs silent fallback” policy decision.

## Key Deliverables

### Deliverable 1: Contract SSOT layer

Define canonical typed contract surfaces (Enum/dataclass/TypedDict) for stage names, reason codes, and config defaults/validation that `pipeline.py` consumes.

### Deliverable 2: Symmetry model for stage handling

Define a uniform “stage result envelope” and stage boundary semantics that apply equivalently across normalize/enrich/filter/shortlist/ranking/cv_analysis/cv_generation.

### Deliverable 3: Migration + safety controls

Define compatibility and rollback strategy for any persisted artifacts (checkpoint payloads, emitted events, debug records) impacted by contract normalization.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- capture current divergence points and classify them into drift/contradiction/obsolete/duplication/missing-contract/edge-case buckets

**Steps:**
- [ ] confirm exact drift sites in `src/fitcv/pipeline.py`:
  - Top-N config access drift (soft `get(..., 0)` vs hard `config[...]`)
  - duplicate `_build_stage_dispatch_map()` definitions
  - `CV_REVIEW_REQUIRED_REASON_CODES` vs `_normalize_review_required_reason_code()` outputs mismatch
  - fingerprint/hash duplication across local and imported builders
  - `embed_scope` doc-only promise
- [ ] identify persisted/published surfaces touched by these contracts:
  - checkpoint payload shape
  - debug records written/emitted
  - worker entrypoints (e.g., `src/fitcv_cp/worker_job.py`)

**Verification:**
- [ ] GitNexus index is fresh for repo alias `fitcv`

**Exit Criteria:**
- drift list is precise enough to drive bounded refactor actions A1–A5 below

### Wave 2: Decision closure

**Purpose:**
- decide SSOT module boundaries, fail-fast policy, and compatibility approach

**Steps:**
- [ ] decide canonical contract module placement:
  - option A: new `src/fitcv/pipeline_contracts.py` (pipeline-specific SSOT)
  - option B: extend `src/fitcv/contracts.py` (cross-module SSOT)
- [ ] decide config policy:
  - keep silent `0` defaults (current behavior compatibility)
  - or move to early hard validation (behavior change; requires explicit migration plan)
- [ ] decide reason-code governance:
  - Enum-only SSOT, forbid free-string codes
  - or keep “known set + passthrough unknown” (lower strictness; higher drift risk)
- [ ] decide checkpoint schema evolution:
  - backward-compatible parser for old checkpoints
  - or versioned checkpoint schema with explicit upgrade step

**Verification:**
- [ ] acceptance criteria below are all satisfiable without cross-repo changes

**Exit Criteria:**
- design is bounded: A1–A3 must be doable without A4–A5

### Wave 3: Validation and approval readiness

**Purpose:**
- define test evidence required before implementation planning/execution

**Steps:**
- [ ] define unit tests required for reason-code SSOT and config validation policy
- [ ] define invariants that must not regress (below)
- [ ] define rollback/containment strategy per action

**Verification:**
- [ ] validation plan proves drift/contradiction removal

**Exit Criteria:**
- spec ready for approval; implementation planning can start with `skill-writing-plans`

## Design Decisions

### Decision: SSOT contract location

- context: pipeline contracts currently exist as scattered strings/sets/helpers inside `pipeline.py`, causing drift and contradictions
- choice: create `src/fitcv/pipeline_contracts.py` as pipeline-scoped SSOT for stage/reason/config/state contracts
- alternatives considered:
  - extend `src/fitcv/contracts.py` (risk: cross-domain coupling; unclear ownership boundary)
  - leave contracts in `pipeline.py` (keeps drift risk; blocks symmetry)
- impact:
  - `pipeline.py` imports and uses SSOT types; string literals reduced

### Decision: reason-code strictness

- context: `CV_REVIEW_REQUIRED_REASON_CODES` is narrower than `_normalize_review_required_reason_code()` outputs (contradiction)
- choice: make reason codes Enum-only SSOT; `_normalize_review_required_reason_code()` returns `ReasonCode | None`
- alternatives considered:
  - widen the existing set only (still allows new free-string drift)
  - allow unknown passthrough codes (keeps analytics/UI inconsistency risk)
- impact:
  - downstream consumers can rely on stable reason-code universe

### Decision: Top-N config policy

- context: same concept (pipeline Top-N) mixes silent-fallback (`0`) and hard-required access
- choice: introduce single accessor that encodes chosen policy (compat vs fail-fast) and use it everywhere
- alternatives considered:
  - keep mixed access (known drift source)
  - convert all to hard required immediately (may change behavior unexpectedly)
- impact:
  - invariance: one rule for all Top-N reads; easier tests

### Decision: stage-name governance

- context: stage names are plain strings; duplicated helper exists; stage validation exists but stage-dispatch scaffolding is duplicated/unused
- choice: define `PipelineStage` Enum (or `typing.Literal` union) as SSOT; keep `PIPELINE_STAGE_SEQUENCE` as derived list from SSOT
- alternatives considered:
  - keep tuple of strings (weak contract; drift risk)
- impact:
  - stage boundary logic becomes type-checkable; duplication removable

### Decision: checkpoint/state evolution

- context: pipeline state/checkpoint payload is `dict[str, Any]` large surface; refactors risk silent schema break
- choice: define explicit `PipelineState` TypedDict + `CheckpointPayload` schema version; add upgrade path for older payloads
- alternatives considered:
  - leave state untyped (keeps fragility; makes A5 unsafe)
- impact:
  - enables bounded refactors without breaking resume or worker integrations

## Invariants

- `run_pipeline(...)` public signature and return keys remain stable.
- Pipeline stage order semantics remain: normalize → enrich → rule_filter → shortlist → ranking → cv_analysis → cv_generation.
- No new persisted artifact fields removed without deprecation path.
- Fingerprint/hash generation stays deterministic for identical logical inputs (canonical JSON normalization).
- Reason code emitted/recorded is always member of SSOT reason-code universe (no free strings).
- Any config default policy is consistent across all call sites (no mixed “silent 0” vs “hard required” for same key).

## Acceptance Criteria

- Contradiction removed: reason codes produced by normalization are exactly subset of SSOT Enum.
- Drift removed: all Top-N reads use one accessor policy.
- Obsolete/duplication removed: only one `_build_stage_dispatch_map()` (or removed entirely if unused).
- Hash/fingerprint logic consolidated: pipeline uses one canonical helper for JSON→sha256 where appropriate.
- Checkpoint/state contract exists and is enforced at boundary (deserialize/restore) with schema versioning or TypedDict validation.
- `embed_scope` becomes either:
  - implemented config with enforced behavior, or
  - explicitly removed from docstring as non-goal (no stale promise).

## Non-Goals

- No rewrite of embedding/vector-search/ranking model logic.
- No redesign of BigQuery schemas beyond what is needed for contract alignment.
- No cross-module “perfect architecture”; changes remain bounded to pipeline and its immediate contracts/tests.
- No file split (A5) unless A1–A4 land with validation proof first.

## Risks and Mitigations

- Risk: tightening reason-code universe breaks downstream consumer expecting arbitrary strings
  - Mitigation: add compatibility mapping layer; stage deprecation period; add explicit “unknown/other” Enum member if needed
- Risk: changing Top-N default policy changes output behavior (silent empty vs error)
  - Mitigation: make policy explicit; add tests for both policies; use feature flag/config toggle if required
- Risk: checkpoint schema changes break resume/worker flows
  - Mitigation: schema version field + upgrade adapter; golden snapshot tests
- Risk: large file refactor introduces accidental behavior changes
  - Mitigation: refactor in bounded actions A1→A5 with tests after each; GitNexus impact checks before edits

## Refactor Action Model (A1–A5)

### A1: Reason-code SSOT normalization

- normalization target:
  - `ReasonCode` Enum (SSOT)
  - normalization function returns `ReasonCode | None`
  - delete or derive `CV_REVIEW_REQUIRED_REASON_CODES` from Enum
- symmetry model:
  - all CV generation outcomes that need “reason” use same Enum values
- invariants to preserve:
  - existing meaning of each reason branch

### A2: Remove duplicate/unused stage dispatch helper

- normalization target:
  - single authoritative stage sequencing and optional dispatch scaffold
- symmetry model:
  - stage name validation uses SSOT stage universe everywhere
- invariants to preserve:
  - stage order and resume behavior

### A3: Config access normalization (Top-N and similar)

- normalization target:
  - single accessor for pipeline config ints: required/default/min-value rules encoded once
- symmetry model:
  - all stages read Top-N values the same way
- invariants to preserve:
  - explicitly selected policy (compat vs fail-fast)

### A4: Checkpoint/state contract boundary

- normalization target:
  - `PipelineState` TypedDict + schema version
  - explicit restore/upgrade path
- symmetry model:
  - stage result envelope written/read consistently
- invariants to preserve:
  - resume produces same outcomes as fresh run for same inputs

### A5: Module split for symmetry (optional, gated)

- normalization target:
  - `pipeline.py` becomes orchestration-only
  - stage implementations move to dedicated modules with uniform interface
- symmetry model:
  - each stage module exposes `run_stage(stage_ctx) -> StageResult`
- invariants to preserve:
  - no behavior change; import/public API stability

## Prioritized Action Plan (bounded scope)

1) A1 (reason-code SSOT) — risk: medium; requires unit tests; smallest contradiction fix
2) A2 (remove duplicate/unused helper) — risk: low; safe cleanup after confirming no callers
3) A3 (config access normalization) — risk: medium; requires explicit policy decision + tests
4) A4 (checkpoint/state contract) — risk: high; requires compatibility + snapshot tests
5) A5 (module split) — risk: high; gated on A1–A4 proof

Dependency ordering: A1 → A2 → A3 → A4 → A5.

## Validation Plan

- proof target: reason-code contradiction removed
  - method: unit tests + static assertion (“all returned reasons in Enum”)
  - evidence: `tests/test_pipeline.py` (or new dedicated test file) asserts mapping coverage for each branch
- proof target: Top-N config drift removed
  - method: unit tests on accessor + grep-style enforcement (no raw `config["pipeline"]["...top_n"]` in pipeline)
  - evidence: test + code inspection checklist item in PR
- proof target: stage helper duplication removed
  - method: inspection + GitNexus impact showing no callers before deletion
  - evidence: `npx gitnexus impact -r fitcv Function:src/fitcv/pipeline.py:_build_stage_dispatch_map --include-tests` output stored in PR notes
- proof target: checkpoint schema safe
  - method: golden snapshot test for checkpoint payload; upgrade adapter test
  - evidence: test fixtures + passing `pytest`
- proof target: invariants preserved end-to-end
  - method: E2E pipeline test(s) with fixed inputs/stubs; compare stable outputs
  - evidence: `pytest` run output + fixture diffs (no unexpected changes)

## Completion Criteria

- Spec approved.
- For implementation:
  - A1–A3 shipped with tests proving acceptance criteria.
  - A4 shipped only with explicit backward-compat story and golden snapshot proof.
  - A5 shipped only after A1–A4 proofs and explicit approval.
