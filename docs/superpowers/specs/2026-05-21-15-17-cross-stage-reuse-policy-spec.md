---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: cross-stage-reuse-policy-symmetry-and-ssot
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-cross-stage-cache-safety
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - config/runtime/pipeline.yaml
related_features: []
related_stages:
  - enrich
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Define single, stage-symmetric reuse policy contract that eliminates current control-surface drift across enrich, embedding/query, ranking, cv_analysis, and cv_generation, while preserving safe defaults and deterministic behavior.

## Key Deliverables

### Reuse Policy SSOT Contract

Specify canonical config shape for per-stage reuse controls (`enabled`, `policy`, `max_age_days`, optional safeguards) and ownership boundary between code and runtime settings.

### Reuse Observability Invariance Contract

Specify stage-symmetric status vocabulary and canonical evidence envelope so reused/fresh/disabled/mismatch decisions are explained consistently in artifacts and run detail.

### Migration-Safe Rollout Contract

Specify phased rollout that keeps current behavior stable before enabling new controls, especially for cv_generation reuse.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- establish current reuse behavior and asymmetries before design decisions

**Steps:**
- [ ] document existing reuse families in source:
  - enrich (`enrich_reuse_status`)
  - embeddings/query (`embedding_reuse_status`, `candidate_query_reuse_status`)
  - late-stage ranking/cv_analysis (`reused_exact_match` via `late_stage_reuse_snapshots`)
  - synonym triage reuse toggle (`synonym_management.triage_recommendation_reuse_enabled`)
- [ ] record where reuse is configurable vs implicit in code
- [ ] identify current artifact/evidence split and operator-facing drift

**Verification:**
- [ ] current-state map contains each stage, status field, policy source, and evidence source

**Exit Criteria:**
- no proposed design decision depends on unknown stage reuse behavior

### Wave 2: Decision closure

**Purpose:**
- close design on SSOT reuse controls, status invariance, and staged rollout

**Steps:**
- [ ] define canonical reuse settings namespace and per-stage keys
- [ ] define shared status vocabulary and mapping from existing stage values
- [ ] define canonical reuse diagnostics payload and stage-specific extensions
- [ ] decide cv_generation reuse gating and default-disabled safety
- [ ] decide run-detail/settings exposure model and ownership

**Verification:**
- [ ] each non-obvious design branch includes alternatives and chosen rationale

**Exit Criteria:**
- spec contains coherent, bounded design ready for implementation planning

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof plan that confirms symmetry/SSOT gains without regressions

**Steps:**
- [ ] define contract tests for settings-schema, defaults, and behavior parity
- [ ] define integration checks for reuse decisions and diagnostic payloads
- [ ] define UI proof points for settings and run-detail metrics consistency

**Verification:**
- [ ] validation plan proves both behavioral safety and control-surface invariance

**Exit Criteria:**
- spec is approval-ready for implementation-plan handoff

## Design Decisions

### Decision: Introduce canonical reuse-policy namespace with per-stage controls

- context: current reuse controls are fragmented; some stages are implicit-only and one workflow has explicit toggle
- choice: add canonical settings block for stage reuse policy (example keys):
  - `reuse.enrich.enabled`
  - `reuse.shortlist_embeddings.enabled`
  - `reuse.shortlist_query_embedding.enabled`
  - `reuse.ranking_ai_score.enabled`
  - `reuse.cv_analysis.enabled`
  - `reuse.cv_generation.enabled`
  - each stage includes `policy: exact_match_only` and `max_age_days`
- alternatives considered:
  - keep current ad hoc mix of implicit code paths and selective UI toggles
  - add only cv_generation and cv_analysis toggles without shared namespace
- impact:
  - centralizes policy ownership in runtime settings
  - reduces per-stage divergence risk
  - enables future stage additions without new control model

### Decision: Standardize reuse status vocabulary across stages

- context: stage-specific statuses exist but not normalized for operator reasoning
- choice: define canonical statuses used in diagnostics and UI summaries:
  - `reused_exact_match`
  - `fresh_compute`
  - `reuse_disabled`
  - `fingerprint_mismatch`
  - `stale_snapshot`
  - `not_applicable`
- alternatives considered:
  - keep current free-form stage-specific status values
  - normalize only late-stage statuses
- impact:
  - consistent telemetry and run-detail interpretation
  - easier test contracts and alerting rules

### Decision: Extend reuse evidence contract to all relevant stages

- context: `late_stage_reuse_snapshots` covers ranking/cv_analysis only
- choice: define canonical reuse diagnostics envelope (v2) with stage slots:
  - `enrich_records`
  - `embedding_records`
  - `query_embedding_records`
  - `ranking_ai_scores`
  - `cv_analysis_records`
  - `cv_generation_records` (new)
- alternatives considered:
  - leave multi-location evidence split
  - only append cv_generation to existing late-stage payload
- impact:
  - single evidence surface for reuse decisions
  - clear backward-compatibility path from `late_stage_reuse_v1`

### Decision: CV generation reuse ships default-disabled behind exact-match safeguards

- context: cv_generation currently lacks reuse path and has highest content-integrity risk
- choice: implement reuse path but default `reuse.cv_generation.enabled=false`, require strict fingerprint over:
  - job input fingerprint
  - candidate profile fingerprint
  - preset/model
  - section toggles and limits
  - prompt/template version identifiers
- alternatives considered:
  - enable by default
  - defer cv_generation entirely
- impact:
  - preserves current output behavior unless explicitly enabled
  - allows controlled adoption with auditability

### Decision: Preserve behavior-first compatibility during migration

- context: existing production behavior must remain stable during SSOT unification
- choice: two-step migration:
  1. introduce settings schema + telemetry + diagnostic normalization with defaults matching current behavior
  2. enable new stage controls and optional cv_generation reuse after proof
- alternatives considered:
  - immediate behavior switch on schema introduction
- impact:
  - minimizes regression blast radius
  - supports staged verification and rollback

## Invariants

- reuse decision for any stage must be deterministic from explicit fingerprint and declared policy
- disabling a stage reuse control must force fresh compute for that stage
- run artifact evidence must always explain reused vs fresh outcome counts per stage
- backward compatibility for existing `late_stage_reuse_v1` consumers must be preserved during migration window
- no stage may introduce hidden reuse behavior outside canonical policy namespace after adoption

## Acceptance Criteria

1. settings schema exposes canonical per-stage reuse controls for enrich, shortlist embeddings/query, ranking, cv_analysis, cv_generation.
2. default values preserve current effective behavior for existing stages; cv_generation reuse remains off by default.
3. run output diagnostics contain normalized reuse status vocabulary and per-stage reused/fresh totals.
4. run detail can render reuse metrics consistently for all configured reuse stages.
5. disabling any stage reuse setting yields fresh-compute behavior and corresponding status evidence.
6. contract tests cover status mapping, toggle behavior, and diagnostics shape.

## Non-Goals

- redesign of ranking/cv-analysis scoring logic unrelated to reuse controls
- replacing existing enrichment or embedding cache storage backend
- introducing approximate-match reuse policies in this iteration
- changing publication/governance workflows outside reuse-control scope

## Risks and Mitigations

- risk: status normalization breaks downstream consumers expecting old strings
  - mitigation: support compatibility mapping and staged deprecation notices
- risk: cv_generation reuse serves stale markdown due to incomplete fingerprint inputs
  - mitigation: strict fingerprint contract and default-disabled rollout
- risk: settings sprawl increases operator confusion
  - mitigation: grouped settings UX with concise “why this matters” copy and safe defaults
- risk: mixed old/new diagnostics payloads during migration
  - mitigation: versioned envelope + parser compatibility tests

## Validation Plan

- proof target: canonical reuse settings are single-source and stage-complete
  - method: inspection + schema unit tests
  - evidence: updated `src/fitcv_cp/settings_schema.py` tests asserting keys/defaults/types

- proof target: stage reuse behavior respects enabled/disabled controls
  - method: pipeline integration tests with controlled snapshots/cache fixtures
  - evidence: tests showing each stage flips between reused/fresh outcomes based on toggle

- proof target: diagnostics payload is symmetric and version-safe
  - method: serialization contract tests
  - evidence: tests for v1 backward-read + v2 canonical envelope generation

- proof target: run-detail reuse reporting remains coherent
  - method: app route rendering tests
  - evidence: `tests/test_fitcv_cp/test_app.py` assertions for per-stage reuse metrics rows

- proof target: cv_generation reuse remains inert unless explicitly enabled
  - method: negative-path integration test
  - evidence: test proving fresh generation when `reuse.cv_generation.enabled=false`

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
