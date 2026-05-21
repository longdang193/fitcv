---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: stage-reuse-toggle-symmetry-default-on
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-cross-stage-cache-safety
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/synonym_proposals.py
  - config/runtime/pipeline.yaml
related_features: []
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Patch reuse-control symmetry break by introducing explicit ON/OFF toggles for every reuse-capable stage, with default `ON` behavior across stages.

## Key Deliverables

### Symmetric Reuse Toggle Contract

Define canonical config keys for each reuse-capable stage so control-plane and runtime no longer mix explicit toggle for one stage and implicit behavior for others.

### Default-ON Backward-Compatible Behavior Contract

Set defaults to `true` for all new reuse toggles so existing effective behavior remains reuse-enabled without operator migration burden.

### Unified Runtime Decision Contract

Define single gate pattern used by all stages: read toggle, decide `reused_exact_match` vs `fresh_compute`, emit explicit reason when reuse disabled.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm root-cause asymmetry and exact blast surface before design lock

**Steps:**
- [ ] map current explicit toggle surface:
  - `synonym_management.triage_recommendation_reuse_enabled`
- [ ] map reuse-capable but implicit stages:
  - enrich (`enrich_reuse_status`)
  - ranking (`ai_score_reuse_status`)
  - cv_analysis (`analysis_reuse_status`)
  - cv_generation (reuse-ready policy surface currently absent)
- [ ] confirm schema/config absence for per-stage toggles outside synonym triage

**Verification:**
- [ ] evidence list includes file+line references for explicit/implicit split

**Exit Criteria:**
- root cause stated as contract asymmetry, not algorithm defect

### Wave 2: Decision closure

**Purpose:**
- finalize concrete setting keys, default values, and runtime gate invariants

**Steps:**
- [ ] define canonical keys:
  - `reuse.enrich.enabled`
  - `reuse.ranking.enabled`
  - `reuse.cv_analysis.enabled`
  - `reuse.cv_generation.enabled`
  - `reuse.synonym_triage.enabled` (alias/migration path from existing key)
- [ ] define default value: `true` for all keys
- [ ] define migration mapping from legacy synonym key
- [ ] define stage-level disabled status reason contract (`reuse_disabled`)

**Verification:**
- [ ] decisions include alternatives and rejection reasons

**Exit Criteria:**
- design ready for implementation plan without open key-shape ambiguity

### Wave 3: Validation and approval readiness

**Purpose:**
- establish proof that symmetry patch works and defaults preserve behavior

**Steps:**
- [ ] add schema-level tests for key presence/default/type
- [ ] add pipeline-stage tests for enabled/disabled branching
- [ ] add control-plane settings serialization tests for new keys
- [ ] add migration tests for legacy synonym key compatibility

**Verification:**
- [ ] test matrix covers each stage in ON and OFF mode

**Exit Criteria:**
- spec produces executable plan path with unambiguous acceptance tests

## Design Decisions

### Decision: Adopt stage-symmetric reuse namespace with explicit booleans

- context: today only synonym triage has explicit ON/OFF toggle; other reuse stages run implicit-only
- choice: introduce `reuse.<stage>.enabled` booleans for every reuse-capable stage
- alternatives considered:
  - keep one-off synonym toggle only
  - add toggles only for ranking/cv_analysis and skip enrich/cv_generation
- impact:
  - removes structural asymmetry
  - makes runtime behavior operator-visible and testable

### Decision: Default ON for all stage reuse toggles

- context: user requirement is default ON; current implicit stages already behave as reuse-enabled where cache/fingerprint matches
- choice: set every new `reuse.<stage>.enabled` default to `true`
- alternatives considered:
  - default OFF for high-risk stages
  - mixed defaults per stage
- impact:
  - preserves expected throughput/perf characteristics
  - avoids silent behavior regression during rollout

### Decision: Preserve legacy synonym key via compatibility bridge

- context: existing setting key already used in schema/UI/runtime
- choice: keep reading legacy key, map to canonical `reuse.synonym_triage.enabled`, and emit normalized settings payload
- alternatives considered:
  - hard cutover to new key only
- impact:
  - no breaking config migration requirement
  - enables staged deprecation path

### Decision: CV generation joins same toggle contract, default ON

- context: cv_generation currently lacks explicit reuse toggle; symmetry requires same control plane
- choice: add `reuse.cv_generation.enabled: true` with strict exact-match fingerprint gating in reuse engine
- alternatives considered:
  - postpone cv_generation toggle
  - add key but default OFF
- impact:
  - symmetry restored end-to-end
  - still safe due to exact-match contract

## Invariants

- every reuse-capable stage has explicit boolean toggle in schema + runtime config
- default effective value for each stage toggle is `true`
- `enabled=false` must force fresh compute for that stage and emit `reuse_disabled`
- `enabled=true` never bypasses existing exact-match fingerprint requirements
- control-plane settings payload reflects canonical values for all stage toggles

## Acceptance Criteria

1. settings schema includes all `reuse.<stage>.enabled` keys listed in this spec.
2. runtime config (`config/runtime/pipeline.yaml`) includes these keys with default `true`.
3. enrich stage obeys `reuse.enrich.enabled` gate for cached enrichment reuse.
4. ranking stage obeys `reuse.ranking.enabled` gate for exact-match score reuse.
5. cv_analysis stage obeys `reuse.cv_analysis.enabled` gate for exact-match analysis reuse.
6. cv_generation stage has explicit toggle `reuse.cv_generation.enabled` with default `true` and exact-match safeguards unchanged.
7. synonym triage supports canonical toggle plus legacy-key compatibility.
8. tests verify ON/OFF behavior and status evidence for each stage.

## Non-Goals

- redesign fingerprint algorithms for existing stages
- introduce non-boolean policy controls (TTL, partial-match) in this patch
- rewrite unrelated settings IA/UX structure beyond reuse toggle exposure
- remove legacy synonym key in same patch

## Risks and Mitigations

- risk: duplicate key sources cause drift during migration
  - mitigation: define single canonical read helper; legacy key read only as fallback
- risk: default-ON misunderstood as unconditional reuse
  - mitigation: document exact-match requirement in settings help text and runtime logs
- risk: cv_generation toggle added without complete fingerprint parity
  - mitigation: block reuse path unless required fingerprint fields present; fallback to fresh_compute

## Validation Plan

- proof target: schema and config are stage-symmetric with default ON
  - method: schema unit tests + config snapshot check
  - evidence: passing tests asserting key presence and `true` defaults

- proof target: each stage honors ON/OFF toggle gates
  - method: stage-level integration tests with reusable fixture inputs
  - evidence: reused statuses when ON + exact-match; fresh status with `reuse_disabled` reason when OFF

- proof target: legacy synonym key remains compatible
  - method: app settings load/save compatibility tests
  - evidence: legacy-only config still yields expected runtime toggle behavior

- proof target: control-plane exposes canonical toggle set
  - method: API response contract test for settings payload
  - evidence: payload includes all canonical reuse toggles with resolved booleans

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
