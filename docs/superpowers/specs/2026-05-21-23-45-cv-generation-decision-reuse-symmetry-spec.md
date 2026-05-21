---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: cv-generation-decision-reuse-symmetry
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-cross-stage-cache-safety
targets:
  - src/fitcv/pipeline.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv/tracker.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - tests/
related_features:
  - trigger_run_management
related_stages:
  - cv_generation
---

## Goal

Eliminate avoidable late-stage evidence drift for identical cv-generation inputs by introducing a symmetric two-tier reuse contract: artifact reuse and decision reuse, both default ON and auditable per item.

## Key Deliverables

### Two-Tier Reuse Contract

Define and adopt separate, explicit reuse paths for cv-generation artifact reuse and cv-generation terminal decision reuse.

### Deterministic Decision Cache Surface

Add a canonical persisted cache for terminal decision replay keyed by deterministic fingerprint contract so identical evidence does not require repeated LLM calls.

### Operator-Visible Reuse Path Evidence

Expose per-item reuse path and cache-hit/miss reason in run artifacts/timeline so operators can distinguish fresh compute vs deterministic replay.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- freeze current cv-generation reuse boundary and identify asymmetry causing fresh LLM calls under reuse-enabled settings

**Steps:**
- [ ] inspect current cv-generation artifact reuse lookup and hit conditions
- [ ] inspect current terminal decision derivation branches and persistence surfaces
- [ ] identify where non-accepted outcomes bypass reusable persistence

**Verification:**
- [ ] explicit trace exists from trigger input to reuse decision to LLM call/no-call behavior

**Exit Criteria:**
- root-cause asymmetry is documented with exact source paths and branch conditions

### Wave 2: Decision closure

**Purpose:**
- choose concrete cache contract and policy defaults that enforce structural symmetry

**Steps:**
- [ ] define two-tier controls (`artifact` and `decision`) with default ON
- [ ] define decision-cache row schema and key contract versioning
- [ ] define replay eligibility and fallback rules when row invalid/stale

**Verification:**
- [ ] each non-obvious design edge has a closed decision or explicit deferral

**Exit Criteria:**
- design is bounded, symmetric, and implementation-ready

### Wave 3: Validation and approval readiness

**Purpose:**
- make runtime proof and regression proof requirements explicit before implementation planning

**Steps:**
- [ ] define per-run evidence fields for cache path and hit/miss reasons
- [ ] define deterministic replay proof protocol for repeated identical runs
- [ ] define negative/fallback proof for stale/incomplete decision cache rows

**Verification:**
- [ ] validation plan can prove both reuse effectiveness and correctness preservation

**Exit Criteria:**
- spec ready for implementation planning handoff

## Design Decisions

### Decision: Split cv-generation reuse controls into artifact and decision lanes

- context: current single reuse toggle permits artifact reuse only, leaving decision reuse unresolved for non-accepted outcomes
- choice: introduce `reuse.cv_generation.artifact.enabled` and `reuse.cv_generation.decision.enabled`; both default `true`
- alternatives considered:
  - keep single toggle and infer dual behavior implicitly
  - force artifact persistence for all outcomes only
- impact:
  - removes semantic ambiguity in operator settings
  - supports deterministic replay without requiring markdown artifact existence

### Decision: Introduce terminal decision cache with versioned key contract

- context: repeated identical runs can still call LLM when artifact row absent; this reintroduces evidence drift
- choice: persist terminal decision cache rows keyed by `(cv_generation_input_fingerprint, validation_evidence_fingerprint, decision_contract_version)`
- alternatives considered:
  - key on input fingerprint only
  - replay from event stream only without durable cache
- impact:
  - same evidence can be replayed deterministically
  - explicit versioning prevents semantic replay across taxonomy/policy changes

### Decision: Reuse non-accepted outcomes through decision cache, not markdown artifact emulation

- context: non-accepted outcomes often have no valid final markdown artifact
- choice: cache terminal decision evidence and replay decision directly; keep artifact reuse path unchanged for accepted rows
- alternatives considered:
  - persist synthetic markdown for non-accepted outcomes
  - do not reuse non-accepted outcomes
- impact:
  - avoids malformed artifact reuse
  - reduces unnecessary LLM calls while preserving outcome semantics

### Decision: Emit explicit per-item cache-path observability

- context: current timeline can hide why LLM was called under reuse-enabled settings
- choice: emit normalized field `cv_generation_cache_path` with values `artifact_reuse | decision_reuse | fresh_compute` plus `cache_miss_reason`
- alternatives considered:
  - keep implicit reasoning in debug JSON only
- impact:
  - immediate operator clarity and faster debugging loops

## Invariants

- `reuse.cv_generation.artifact.enabled` and `reuse.cv_generation.decision.enabled` default to `true`.
- Artifact reuse requires valid persisted structured+markdown artifact and exact input fingerprint match.
- Decision reuse requires exact `(input_fp, evidence_fp, decision_contract_version)` match.
- Same key in decision cache must replay same `(status, review_required_reason_code)`.
- Fresh compute remains legal fallback when required cache row missing/invalid.
- Determinism guard remains active and must report conflicts for same key with different status.

## Acceptance Criteria

- Settings surface exposes independent artifact/decision reuse controls under cv-generation with default ON values.
- For repeated runs where decision-cache key matches, cv-generation skips LLM call and emits `cv_generation_cache_path=decision_reuse`.
- For repeated runs where artifact row matches, cv-generation emits `cv_generation_cache_path=artifact_reuse`.
- For cache miss, cv-generation emits `cv_generation_cache_path=fresh_compute` with non-empty `cache_miss_reason`.
- No same-key terminal status conflicts observed in deterministic replay validation set.

## Non-Goals

- No redesign of upstream ranking or cv-analysis scoring semantics.
- No change to acceptance policy thresholds themselves.
- No migration of historical event payload shapes beyond required compatibility shims.
- No forced replay across changed decision-contract versions.

## Risks and Mitigations

- Risk: stale decision cache replays outdated semantics.
  - Mitigation: mandatory `decision_contract_version` in key; bump on rule/taxonomy changes.
- Risk: cache growth and lookup latency.
  - Mitigation: bounded retention/TTL policy and indexed lookup fields.
- Risk: silent fallback hides reuse misses.
  - Mitigation: required `cache_path` + `cache_miss_reason` event fields and run-detail exposure.
- Risk: partial writes create inconsistent replay rows.
  - Mitigation: atomic persistence per terminal outcome and row-validity checks before replay.

## Validation Plan

- proof target: identical key replays identical terminal decision without LLM invocation
  - method: repeated live runs with frozen inputs + compare telemetry/debug artifacts
  - evidence: per-run rows show `cv_generation_cache_path=decision_reuse`, stable status/reason, and no LLM call markers
- proof target: artifact reuse lane still works for accepted rows
  - method: replay run with known accepted cached version
  - evidence: `cv_generation_cache_path=artifact_reuse`, `reused_cv_version_id` present
- proof target: cache miss path remains explicit and safe
  - method: run with intentionally unseen fingerprint
  - evidence: `cv_generation_cache_path=fresh_compute` and non-empty `cache_miss_reason`
- proof target: determinism guard catches same-key divergence
  - method: synthetic mismatch injection test at worker finalization path
  - evidence: `determinism_violation` event with mismatch payload
- proof target: regression safety for existing reason taxonomy
  - method: targeted pytest module + validator fast hook
  - evidence: passing `tests/test_cv_generation_reason_mapping.py` and `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
4. repeated identical runs demonstrate deterministic replay path selection with explicit cache-path evidence
5. no unresolved ambiguity remains on why LLM was or was not called for cv-generation
