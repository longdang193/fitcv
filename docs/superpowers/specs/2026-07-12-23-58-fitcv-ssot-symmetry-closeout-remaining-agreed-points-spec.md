---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-ssot-symmetry-closeout-remaining-agreed-points
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md
  - src/fitcv/config.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv/pipeline.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/reconciler.py
  - src/fitcv_cp/reconciler_service.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/worker_job.py
  - tests/test_config.py
  - tests/test_pipeline.py
  - tests/test_runtime_routing.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_reconcile_integration_sqlite.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_settings_store.py
  - tests/test_fitcv_cp/test_settings_store_sqlite.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - trigger_run_management
  - inspection_debugging
  - settings_system
related_stages:
  - ranking
  - cv_analysis
  - cv_generation
---

# Detailed Spec: FitCV SSOT / symmetry closeout for remaining agreed review points

## Goal

Close remaining agreed SSOT and symmetry gaps from
`C:\Users\HOANG PHI LONG DANG\OneDrive\OBSIDIAN 24 09 01\24 09 01 obsidian-go-obsidian_v.0.3.1\Overall assessment.md`
after Phases 1-6 without reopening full architecture rewrite.

This spec also closes planning-lineage ambiguity by updating
`docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`
so remaining unresolved work points here instead of leaving competing child-spec
sequencing alive.

This closeout spec covers only still-open agreed problem classes:

- persistence compatibility residue still leaking `project` / `dataset` / `bigquery_dataset` shape into active paths
- lifecycle policy still distributed across route helpers, worker logic, and raw status comparisons
- late-stage outcome meaning still split across contract and pipeline callers
- settings truth still partially split between `SETTINGS_SCHEMA` and parallel maps or heuristics
- runtime-routing truth still not fully symmetric across startup, trigger snapshot, worker, and diagnostics
- bounded monolith reduction only where required to make one-owner policy callable from both web and worker

## Key Deliverables

### Deliverable 1: active persistence boundary becomes SQLite-shaped end to end

Active control-plane runtime paths stop accepting or threading `project`, `dataset`, or equivalent backend-compat arguments unless the field is an explicit inert boundary adapter with a removal note.

This deliverable includes:

- deletion of active-path compatibility parameters from app and worker helpers where they no longer affect behavior
- reduction of `ControlPlaneStore` compatibility surface until active callers speak one SQLite-shaped contract
- removal or quarantine of `bigquery_dataset` as runtime truth in active config/routing surfaces

### Deliverable 2: one lifecycle policy owns command and transition meaning

One small lifecycle-policy owner defines:

- allowed run transitions
- operator command capability checks
- archive / unarchive / cancel / retry / continue semantics
- terminal versus non-terminal grouping

API handlers, worker code, and persistence-facing state transitions read through same policy surface.

### Deliverable 3: one late-stage outcome contract owns outcome literals and meaning

`src/fitcv/late_stage_contract.py` becomes sole owner for late-stage outcome identifiers and interpretation used by pipeline, analysis, artifact logic, and UI-facing summaries.

No second free-form outcome string list remains in `pipeline.py`, `agentic_cv_analysis.py`, or control-plane projections.

### Deliverable 4: settings boundary finishes schema-derived ownership

`SETTINGS_SCHEMA` remains canonical owner.

Remaining section/group/stage/control-surface/native-attribute projections that still depend on parallel maps, suffix folklore, or hand-maintained filters are derived from schema-owned metadata or one schema-owned projection helper.

No second settings registry is introduced.

### Deliverable 5: runtime-routing truth is symmetric across equivalent runtime surfaces

Equivalent runtime surfaces use same routing resolution truth for provider/model/API-key capability and resolved snapshot display:

- startup checks
- trigger-time runtime envelope capture
- worker execution path
- diagnostics / inspection views

This deliverable extends prior API-key unification work to full routing snapshot semantics, not only key lookup.

## Task/Wave Breakdown

### Wave 1: persistence residue closeout on active runtime paths

**Purpose:**

Stop active code from carrying dead backend-shape arguments after SQLite truth already won.

**Steps:**

- [ ] inventory still-live `project`, `dataset`, `bigquery_dataset`, and `ControlPlaneStore` compatibility touchpoints in active runtime modules only
- [ ] update master remediation spec so this closeout lane is explicit remaining-work owner rather than parallel to stale child-spec sequencing
- [ ] delete pass-through parameters from active call chains where values are ignored or constant
- [ ] if one boundary shim still must remain for a local leaf helper, isolate it behind one adapter instead of threading args through app and worker
- [ ] include reconciler entry/runtime path in same residue cleanup so `ControlPlaneStore` and backend-shape cleanup does not stop at web or worker boundary
- [ ] ensure active config normalization does not present `bigquery_dataset` as meaningful runtime truth when SQLite mode is only supported path
- [ ] keep historical one-off scripts and dead migrations out of scope unless imported by active runtime or tests

**Verification:**

- [ ] grep proof shows active `app.py`, `worker_job.py`, and related helpers no longer expose broad `project` / `dataset` threading
- [ ] reconciler integration coverage still passes after same persistence-contract cleanup
- [ ] storage tests still pass with same operator-visible behavior
- [ ] config tests prove unsupported backend residue is absent or explicitly inert

**Exit Criteria:**

- active runtime contract is SQLite-shaped and no longer pretends backend polymorphism where none exists

### Wave 2: canonical lifecycle policy extraction

**Purpose:**

Make run command semantics symmetric between UI, worker, and persistence.

**Steps:**

- [ ] identify current lifecycle truth split across helper predicates, raw status sets, and transition branches
- [ ] introduce one small lifecycle policy owner near current control-plane runtime contracts, not a service tree
- [ ] move capability checks and transition/grouping logic behind policy helpers
- [ ] make route handlers and worker/reconciler consumers call policy instead of open-coded status comparisons
- [ ] allow tiny helper extraction from `app.py` only if needed to share exact same policy with worker path

**Verification:**

- [ ] tests prove cancel/archive/unarchive/retry/continue capability is same across equivalent surfaces
- [ ] tests prove reconciler terminalize/requeue behavior still matches lifecycle policy after consolidation
- [ ] invariant test proves every status belongs to exactly one terminal/non-terminal interpretation and allowed command set
- [ ] grep proof shows old duplicate lifecycle helper predicates or raw grouping maps removed from active owners

**Exit Criteria:**

- lifecycle behavior has one callable owner and no parallel command semantics remain in active web/worker paths

### Wave 3: late-stage outcome contract consolidation

**Purpose:**

End duplicate literals and partial meaning drift for late-stage analysis outcomes.

**Steps:**

- [ ] keep `late_stage_contract.py` as canonical owner and move any remaining duplicate literals or meaning tables into it
- [ ] make pipeline and analysis callers import canonical literals, predicates, or typed outcome helpers from same owner
- [ ] centralize reusable meaning needed by generation gating, artifact applicability, and UI summaries
- [ ] keep change bounded to existing outcome set unless a mismatch is proven and fixed in same patch

**Verification:**

- [ ] grep proof shows late-stage outcome strings no longer re-declared in pipeline and analysis callers
- [ ] tests prove generation gating and operator-visible outcome summaries still match expected behavior, including control-plane projections
- [ ] invariant test proves every exported late-stage outcome has one interpretation for reusable/proceed/error semantics

**Exit Criteria:**

- late-stage outcomes have one owner for both literal truth and meaning truth

### Wave 4: finish settings-schema derivation for remaining split surfaces

**Purpose:**

Remove residual parallel settings maps and naming heuristics that still compete with schema truth.

**Steps:**

- [ ] audit remaining non-schema settings projections in `settings_schema.py`, `settings_store.py`, and `app.py` boundary helpers
- [ ] move section/group/stage/control-surface/native-attribute truth into schema rows or one schema-derived projection layer
- [ ] delete parallel maps that only restate schema-owned facts
- [ ] keep form rendering native-first and boundary-adapted instead of custom control behavior
- [ ] preserve saved-value compatibility and operator-facing form shape unless current mismatch is explicitly fixed

**Verification:**

- [ ] settings tests prove grouping, section ownership, stage ownership, and native attrs derive from schema-owned metadata
- [ ] app/settings/store tests still pass for render and save/load behavior
- [ ] grep proof shows targeted parallel maps removed or reduced to schema projections

**Exit Criteria:**

- settings boundary behavior is materially more schema-derived and no second owner claims same facts

### Wave 5: runtime-routing symmetry closeout across startup, trigger, worker, and diagnostics

**Purpose:**

Finish routing symmetry beyond shared API-key lookup.

**Steps:**

- [ ] inventory where runtime routing is resolved, serialized, snapshotted, or displayed across active surfaces
- [ ] keep `resolve_model_routing_part(...)` and current routing modules as canonical owner; do not add second resolver
- [ ] make equivalent surfaces consume one shared projection for resolved routing snapshot fields where they currently hand-roll equivalent data
- [ ] ensure startup validation, trigger snapshot capture, worker execution, and diagnostics agree on provider/model/base URL/API-key-availability semantics for same inputs
- [ ] keep envelope provenance fields only if they carry unique evidence; otherwise derive rather than restate

**Verification:**

- [ ] routing tests prove same env/config inputs yield same resolved snapshot across equivalent surfaces
- [ ] app and worker tests prove diagnostics do not drift from execution truth for same run settings
- [ ] grep proof shows ad hoc routing field assembly reduced in active surfaces

**Exit Criteria:**

- equivalent runtime surfaces tell same routing truth from same canonical resolver inputs

## Design Decisions

### Decision: one closeout lane beats new phase fan-out

- context: remaining agreed issues are coupled residue around same SSOT themes
- choice: close them in one bounded spec instead of drafting more phase documents
- alternatives considered:
  - separate Phase 7, Phase 8, and Phase 9 specs
- impact:
  - less planning churn
  - easier cross-proof for symmetry

### Decision: delete residue first, extract tiny shared helpers second

- context: most remaining drift comes from compatibility threading and repeated maps, not missing abstractions
- choice: remove dead surfaces first; add only smallest shared policy/projection helpers needed for reuse
- alternatives considered:
  - big service/repository rewrite
  - leave split truth and patch call sites again
- impact:
  - smallest safe diff
  - clearer SSOT proof

### Decision: existing canonical owners stay canonical

- context: repo already has plausible owners for settings, routing, and late-stage contracts
- choice: strengthen `SETTINGS_SCHEMA`, `late_stage_contract.py`, and existing routing resolver surfaces instead of creating second registries
- alternatives considered:
  - `AppServices`
  - new domain package tree
  - new settings registry beside schema
- impact:
  - lower churn
  - less risk of moving duplication instead of deleting it

### Decision: monolith reduction stays opportunistic and bounded

- context: `app.py` remains large, but size alone does not justify rewrite in closeout lane
- choice: allow only tiny extractions required to share lifecycle or projection truth across web and worker
- alternatives considered:
  - full app decomposition
  - no extraction even when duplicate policy would remain
- impact:
  - no architecture detour
  - still allows real SSOT cleanup

## Invariants

- active control-plane runtime paths speak one SQLite-shaped persistence contract
- master remediation lineage points remaining agreed work at this closeout spec rather than parallel stale child-spec ordering
- no active web or worker path relies on `project` / `dataset` threading to express behavior
- active reconciler path follows same persistence and lifecycle truth as web and worker
- lifecycle command meaning derives from one callable policy owner
- late-stage outcome literals and outcome meaning derive from one contract owner
- settings section/group/stage/control-surface/native-attribute truth derives from `SETTINGS_SCHEMA` or one schema-owned projection
- runtime-routing truth for equivalent inputs is symmetric across startup, trigger snapshot, worker execution, and diagnostics
- native UI behavior is reused where possible and adapted at boundary rather than reimplemented in custom code

## Acceptance Criteria

1. Active runtime no longer exposes broad compatibility threading for dead backend polymorphism.
2. Master remediation lineage no longer leaves competing unresolved child-spec sequencing beside this closeout lane.
3. One lifecycle-policy surface defines command capability and transition meaning used by web, worker, and reconciler paths.
4. `late_stage_contract.py` is sole owner for late-stage outcome literals and shared interpretation, including control-plane projections.
5. Remaining settings grouping/section/stage/native-attribute truth is schema-derived without breaking settings-store save/load behavior.
6. Equivalent routing surfaces report same resolved provider/model/API-key availability truth for same inputs.
7. Any helper extraction added in this lane is smaller than status quo duplication and does not introduce new architecture layers.

## Non-Goals

- no full `AppServices` rewrite
- no repository/service tree redesign
- no second settings registry beside `SETTINGS_SCHEMA`
- no second routing resolver beside existing routing owner surfaces
- no broad `app.py` breakup for style reasons alone
- no backfill of old artifacts or historical runtime outputs
- no repo-wide purge of dormant legacy scripts unless they are active imports or validator blockers

## Risks and Mitigations

- risk: closeout scope balloons into architecture rewrite
  - mitigation: require each extraction to delete more duplicate truth than it adds
- risk: lifecycle centralization changes operator-visible command behavior
  - mitigation: freeze current intended behavior in tests before deleting old predicates
- risk: settings derivation cleanup breaks saved-value or form behavior
  - mitigation: preserve schema keys/defaults and validate render plus save/load parity
- risk: routing symmetry cleanup drops useful provenance detail
  - mitigation: keep unique envelope evidence fields, delete only duplicate resolved-truth fields
- risk: persistence residue removal touches many call sites
  - mitigation: start from grep inventory and collapse args at leaf-to-root boundaries in one pass

## Validation Plan

- proof target: active persistence contract is SQLite-shaped and residue is removed
  - method: targeted grep plus focused storage/config tests
  - evidence: `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_reconcile_integration_sqlite.py`, `tests/test_config.py`
- proof target: master remediation source no longer advertises competing remaining child-spec order
  - method: source inspection of master remediation spec and generated lineage refresh
  - evidence: `docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`, `docs/generated/planning_lineage.yaml`
- proof target: lifecycle policy is symmetric across equivalent surfaces
  - method: focused app/worker/reconciler tests plus invariant coverage for commands and terminal grouping
  - evidence: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_reconcile_integration_sqlite.py`
- proof target: late-stage outcomes have one owner and one meaning table
  - method: grep proof plus pipeline and control-plane projection tests
  - evidence: `tests/test_pipeline.py`, `tests/test_fitcv_cp/test_app.py`
- proof target: settings boundary derives from schema truth
  - method: settings projection/render/save/store tests plus grep proof for removed parallel maps
  - evidence: `tests/test_fitcv_cp/test_settings_schema.py`, `tests/test_fitcv_cp/test_settings_store.py`, `tests/test_fitcv_cp/test_settings_store_sqlite.py`, `tests/test_fitcv_cp/test_app.py`
- proof target: runtime-routing truth is symmetric across equivalent surfaces
  - method: routing resolver tests plus app/worker snapshot tests for same inputs
  - evidence: `tests/test_runtime_routing.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_worker_job.py`
- proof target: planning artifact stays valid
  - method: repo validator subset
  - evidence: `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

This spec is complete when:

- one implementation plan can execute all remaining agreed closeout work without further phase drafting
- master remediation source and generated planning lineage both point remaining agreed work at this closeout lane
- active runtime no longer carries dead backend-compat truth through app and worker paths
- lifecycle, late-stage outcomes, settings projections, and routing snapshots each have one explicit owner
- reconciler path follows same persistence and lifecycle truth as web and worker
- validation evidence exists for persistence, lifecycle, settings, late-stage, and routing symmetry claims
- no new architecture layer was introduced unless it deleted more duplication than it created
