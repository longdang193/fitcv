---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-ssot-symmetry-master-remediation
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - src/fitcv/config.py
  - src/fitcv/contracts.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv/persistence.py
  - src/fitcv/pipeline_contracts.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/data_plane.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/run_artifact_mirror.py
  - src/fitcv_cp/runtime_contracts.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/reconciler_service.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/settings.html
  - docs/architecture.md
  - docs/api.md
  - docs/configuration.md
  - docs/features/settings_system/feature.source.yaml
  - docs/pipeline.md
  - docs/setup.md
  - docs/usage.md
  - docs/observability.md
  - tests/test_config.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_runtime_routing.py
  - tests/test_fitcv/
  - tests/test_fitcv_cp/
  - tests/test_fitcv_cp/test_control_plane_config.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_settings_store.py
  - tests/test_fitcv_cp/test_settings_store_sqlite.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features: []
related_stages: []
---

# Detailed Spec: FitCV SSOT / symmetry master remediation

## Goal

Define one master architecture spec that patches all confirmed SSOT, symmetry,
legacy-backend, dead-surface, and native-boundary problems found in July 12
source audit.

This spec is umbrella design only. It defines final target state, canonical
owners, invariants, and phase boundaries. It does not approve big-bang rewrite
or implementation plan.

## Problem

Current repo has coherent business intent, but several core facts still have
multiple live owners:

- pipeline stage order, stage labels, download mapping, and bundle membership
- control-plane lifecycle capability and transition rules
- late-stage outcome literals and interpretation
- settings schema versus settings grouping, section ownership, stage ownership,
  control-surface ownership, and native input constraints
- routing truth between `resolve_model_routing_part(...)`, LangGraph env
  overrides, startup drift checks, trigger-time runtime envelopes, and ad hoc
  runtime snapshots
- SQLite-only product direction versus legacy `bq`, `project`, and `dataset`
  compatibility plumbing
- removed operator diagnostics versus lingering config keys, payload fields,
  helper functions, and tests

Some review conclusions are directionally correct but too rewrite-heavy. Repo
already has useful owners such as `SETTINGS_SCHEMA`,
`resolve_model_routing_part(...)`, `runtime_routing.py`,
`late_stage_contract.py`, `BackendRuntime`, and `RunStatus`. Master fix should
reuse and tighten these before creating new abstraction trees.

## Triage

Layer: change
Feature type: REPLACE
Summary: replace parallel ownership and legacy compatibility seams with one SSOT- and symmetry-driven contract set built from existing canonical modules where possible
Reasoning: current code already contains partial canonical owners, but they are incomplete, bypassed, or contradicted by duplicated maps and dead compatibility surfaces
Invariants:
  - every semantic fact has one authoritative owner and only derived projections elsewhere
  - native platform features stay primary; adapters normalize data only at HTTP, config, DB, and template boundaries
  - SQLite remains sole supported control-plane backend
  - trigger-time runtime truth stays preserved and replayable
  - deleted operator surfaces are removed fully, not hidden cosmetically
Dependencies:
  - existing control-plane SSOT patches and sqlite-only direction specs
  - current `SETTINGS_SCHEMA`, `late_stage_contract.py`, `runtime_routing.py`, `BackendRuntime`, and `RunStatus` owners
Affected stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
Affected features:
  - settings_system
Primary lens: cross-cutting
Affected docs:
  feature_source:
    - docs/features/settings_system/feature.source.yaml
  feature_yaml: none
  feature_lineage: none
  feature_history: none
  stage_source: none
  stage_contract: none
  feature_docs: []
  cross_cutting_docs:
    - docs/architecture.md
    - docs/api.md
    - docs/configuration.md
    - docs/pipeline.md
    - docs/setup.md
    - docs/usage.md
    - docs/observability.md
  readme: none
  generated: []
Generated refresh required: no
Capability IDs:
  - none
Invariant IDs:
  - none
Spec needed: yes
Plan needed: yes

## Key Deliverables

### Deliverable 1: Canonical ownership map is explicit and reuse-first

This master spec must lock which existing modules remain canonical owners, which
ones expand, and which ones are deleted so downstream phase specs do not invent
parallel ownership.

### Deliverable 2: Final target architecture is SSOT- and symmetry-driven

Final design must converge stage taxonomy, lifecycle policy, late-stage
outcomes, settings metadata, routing truth, and persistence/backend semantics on
single-owner contracts with derived projections only.

### Deliverable 3: Native-first boundary policy is explicit

Design must prefer FastAPI dependency injection, Pydantic/config coercion,
SQLite constraints/upserts/transactions, native HTML validation attributes, and
native file responses over custom re-implementation.

### Deliverable 4: Dead and legacy surfaces have explicit deletion contract

Removed or unsupported surfaces must have full-delete rules across code, tests,
docs, payloads, config keys, and route context, not partial visual removal.

### Deliverable 5: Downstream phase-spec set is bounded and ordered

This master spec must define exact phase lanes to author next, so each child
spec owns one bounded slice and repo stays shippable after every phase.

## Authoritative Ownership

### Pipeline stage taxonomy

- canonical owner after remediation: `src/fitcv/pipeline_contracts.py`
- role: own stage IDs, order, display metadata, event aliases, artifact IDs,
  bundle membership, and downloadability
- rule: `src/fitcv/pipeline.py`, `src/fitcv_cp/app.py`, bundle builders, and
  timeline/download presenters may derive projections only

### Control-plane lifecycle policy

- canonical owner after remediation: `src/fitcv_cp/models.py` for `RunStatus`
  values plus one shared lifecycle-policy helper in `src/fitcv_cp/`
- role: own allowed commands, legal transitions, archived/unarchived behavior,
  and UI capability checks
- rule: HTTP routes, worker, reconciler, and repository transitions must call
  same policy surface

### Late-stage outcome meaning

- canonical owner after remediation: `src/fitcv/late_stage_contract.py`
- role: own CV-analysis / CV-generation status literals and interpretation
- rule: duplicate status strings in `pipeline.py`, `agentic_cv_analysis.py`,
  `agentic_cv_generation.py`, and artifact/report builders are removed or become
  imports from this contract

### Settings contract

- canonical owner after remediation: `src/fitcv_cp/settings_schema.py`
- role: own key, type, default, constraints, section, group, stage,
  control-surface, widget hint, risk level, help text, and secret/restart flags
- rule: grouped sections, stage ownership, control-surface views, server
  validation, and native HTML attrs are derived from schema entries

### Runtime routing truth

- canonical owner after remediation: `src/fitcv/config.py` for generic routing
  resolution plus `src/fitcv/runtime_routing.py` for capability-specific
  adapters
- role: own provider/model/base_url/wire_api resolution and runtime provenance
- rule: startup drift checks, trigger-time snapshots, worker runtime setup, and
  diagnostics reuse these surfaces instead of reparsing env/config ad hoc

### Control-plane backend and SQLite path

- canonical owner after remediation: `src/fitcv/config.py` for backend type,
  `src/fitcv/persistence.py` for shared SQLite path resolution, and
  `src/fitcv_cp/backend_runtime.py` for control-plane runtime envelope
- role: expose sqlite-native backend truth only
- rule: active control-plane interfaces must not carry ignored `bq`, `project`,
  or `dataset` parameters after remediation
- rollout note: if bounded Phase 1 compatibility shims remain at store or
  runtime boundaries, they must stay boundary-local and retire no later than
  Phase 4; no later phase may spread them back into app, worker, or template
  code

### Removed-surface absence contract

- canonical owner after remediation: repo tests plus targeted source-search
  assertions in `tests/test_fitcv_cp/` and related suites
- role: prevent reintroduction of removed diagnostics, replay plumbing, and
  stale compatibility terms

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm live owners, dead surfaces, and minimal reuse-first path before child
  spec authoring

**Steps:**
- [x] inspect active source for stage, lifecycle, settings, routing, and
  backend duplication
- [x] verify which review claims are still live in current source
- [x] classify surfaces as `keep-and-expand`, `derive-only`, or `delete`
- [x] reject big-bang rewrites that duplicate owners already present

**Verification:**
- [x] master problem set is grounded in current source, tests, and docs

**Exit Criteria:**
- no child phase spec needs to rediscover current-state ownership from scratch

### Wave 2: Decision closure

**Purpose:**
- lock canonical owners, deletion rules, and phase boundaries before
  implementation planning

**Steps:**
- [x] choose reuse-first owners for each duplicated concept
- [x] define native-first boundary policy
- [x] define phase ordering that preserves shippable repo after each phase
- [x] record explicit non-goals to block rewrite creep

**Verification:**
- [x] every major design choice has one chosen owner and at least one rejected
  alternative

**Exit Criteria:**
- downstream phase specs can be authored without reopening core architecture
  questions

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof expectations and downstream phase-spec set

**Steps:**
- [x] define cross-phase invariants and final acceptance criteria
- [x] define repo-search, route, template, and test evidence needed for removals
- [x] define child phase-spec lanes and required sequencing

**Verification:**
- [x] validation plan proves both architecture convergence and deletion
  completeness

**Exit Criteria:**
- master spec is ready to drive child phase specs and later implementation plans

## Design Decisions

### Decision: Reuse existing owners before creating new architecture layers

- context: review correctly found duplication, but proposed `AppServices` /
  `domain/application/infrastructure` rewrite is larger than needed for first
  convergence pass
- choice: extend or trim existing owners first: `pipeline_contracts.py`,
  `late_stage_contract.py`, `settings_schema.py`, `runtime_routing.py`,
  `BackendRuntime`, `sqlite_store.py`, and `RunStatus`
- alternatives considered:
  - immediate `AppServices` + dependency-injected repository/service tree
  - whole-folder rewrite before deleting dead surfaces
- impact:
  - keeps diffs smaller and rooted in current code
  - preserves native framework features
  - lets phase specs land real fixes before optional file-structure cleanup

### Decision: One stage registry owns all stage-equivalent projections

- context: stage IDs and related labels exist in both `pipeline.py` and
  `fitcv_cp/app.py`
- choice: create one immutable stage registry in `src/fitcv/pipeline_contracts.py`
  and derive timeline/download/bundle/settings projections from it
- alternatives considered:
  - keep `PIPELINE_STAGE_SEQUENCE` plus separate UI maps with parity tests only
  - create brand-new top-level `domain/stages.py` package immediately
- impact:
  - SSOT for stage order and semantics
  - removes control-plane and pipeline drift hazard

### Decision: Lifecycle policy becomes one callable control-plane contract

- context: lifecycle capability checks are spread across helpers and raw status
  checks
- choice: keep `RunStatus` in `src/fitcv_cp/models.py`, add one shared
  lifecycle-policy helper for commands/transitions, and route HTTP/worker/
  repository paths through it
- alternatives considered:
  - keep raw status-set checks and harden tests only
  - embed all policy inside enum methods and app routes directly
- impact:
  - symmetry between UI affordances and actual transition enforcement
  - bounded change, no framework rewrite

### Decision: `late_stage_contract.py` is sole late-stage status owner

- context: late-stage status literals already have partial canonical home but
  are still duplicated elsewhere
- choice: consolidate meaning there and import from it everywhere else
- alternatives considered:
  - move status ownership into `pipeline.py`
  - create second late-stage enum module beside existing contract
- impact:
  - deletes duplicate literals
  - keeps current shared contract owner instead of replacing it

### Decision: `SETTINGS_SCHEMA` grows into full settings SSOT

- context: schema exists, but grouping, stage ownership, control-surface
  semantics, and native input attrs still live in parallel structures or naming
  heuristics
- choice: enrich each schema entry until it can derive sections, groups,
  control-surface views, native attrs, and server validation from same owner
- alternatives considered:
  - keep parallel maps with parity tests
  - add second UI-metadata registry beside schema
- impact:
  - stronger symmetry between HTTP validation and browser validation
  - fewer parallel maps to maintain

### Decision: Existing routing resolver stays root SSOT

- context: review correctly found routing duplication, but central resolver
  already exists in `resolve_model_routing_part(...)`
- choice: keep `src/fitcv/config.py` root resolver, use
  `src/fitcv/runtime_routing.py` as adapter layer, and replace ad hoc env/config
  parsing with calls into these owners
- alternatives considered:
  - create second `ModelRoutingResolver` abstraction without first deleting
    current duplicates
  - leave multiple runtime-specific resolvers in place
- impact:
  - native reuse of current routing truth
  - preserves trigger-time runtime envelope while removing drift sites

### Decision: SQLite-only control plane becomes strict in interfaces, not only docs

- context: `resolve_data_backend()` already returns `sqlite`, but active call
  surfaces still accept ignored BigQuery-era parameters
- choice: remove `bq`, `project`, and `dataset` from active control-plane store,
  worker, app, and sqlite-store interfaces; shrink `BackendRuntime` to
  sqlite-native concerns only
- alternatives considered:
  - keep compatibility parameters indefinitely
  - support both SQLite and BigQuery as product paths
- impact:
  - real SSOT for backend truth
  - simpler worker/web/control-plane call surfaces

### Decision: Removal means full removal

- context: multiple diagnostics were visually removed but still survive in
  helpers, config keys, payloads, or tests
- choice: every removed surface must delete labels, helper functions, context
  keys, config keys, payload fields, routes, docs, and tests together unless a
  surviving public contract is explicitly retained
- alternatives considered:
  - leave hidden helper residue
  - keep dead routes/scripts "just in case"
- impact:
  - no zombie operator surface debt
  - clearer repo-search proofs

### Decision: Child specs are phase-bounded; no big-bang rewrite phase exists

- context: problem set is broad, but repo must stay shippable and reviewable
- choice: author child specs in this order:
  - Phase 1: legacy-surface deletion and backend-interface trim
  - Phase 2: stage, lifecycle, and late-stage contract consolidation
  - Phase 3: settings-schema completion and native-form boundary convergence
  - Phase 4: routing/runtime-envelope convergence, persistence-truth cleanup,
    and retirement of any temporary Phase 1 backend-compat boundary shims
  - Phase 5: bounded control-plane monolith reduction and optional storage normalization
- alternatives considered:
  - one monolithic implementation plan
  - file-structure rewrite before canonical owner convergence
- impact:
  - each phase can prove one bounded contract improvement
  - later decomposition happens only after core owners are stable

## Invariants

- every semantic fact named by more than one surface must have one authoritative
  owner and only derived projections elsewhere
- control-plane product support is SQLite-only; active interfaces must not carry
  ignored BigQuery-era parameters
- stage ID, order, aliasing, bundle membership, and downloadability derive from
  one stage registry
- every `RunStatus` capability and transition rule derives from one lifecycle
  policy used by HTTP, worker, reconciler, and repository paths
- late-stage status strings and meaning derive from one late-stage contract
- `SETTINGS_SCHEMA` owns both server validation semantics and native input attrs
- native browser validation stays primary; JavaScript may enhance UX but must
  not recreate same rules independently
- runtime routing truth derives from `resolve_model_routing_part(...)` and
  shared routing adapters; trigger-time runtime envelopes remain preserved
- removed operator surfaces stay absent across UI, routes, payloads, config
  keys, tests, and docs unless explicitly retained as supported contract
- run/event/settings persistence must not split into hidden fallback stores that
  diverge from primary reads
- web and worker must continue to share one runtime data path and one persisted
  run/event truth surface

## Acceptance Criteria

1. One canonical stage registry exists, and independent hardcoded stage lists in
   active pipeline/control-plane surfaces are removed or explicitly derived.
2. One lifecycle-policy surface exists, and UI capability checks match worker/
   repository transition enforcement.
3. `late_stage_contract.py` is sole owner for late-stage status literals and
   interpretation.
4. `SETTINGS_SCHEMA` is rich enough to derive server validation, native input
   attrs, sections, groups, stage ownership, and control-surface membership from
   one owner.
5. Active control-plane interfaces no longer accept ignored `bq`, `project`, or
   `dataset` parameters, and SQLite-only product direction is truthful in docs
   and runtime surfaces.
6. Ad hoc LangGraph/routing parsing in startup, app, worker, or diagnostics is
   replaced by existing canonical routing surfaces.
7. `_LOCAL_RUNS`, dead-letter fallback/event replay residue, removed diagnostics,
   and other audited zombie surfaces are deleted fully or explicitly retained as
   supported contracts with named owner and tests.
8. Child phase specs exist for all five ordered lanes in this master spec.

## Non-Goals

- no immediate `AppServices` or full `domain/application/infrastructure` tree
  rewrite
- no one-shot split of `app.py`, `pipeline.py`, or `worker_job.py` purely for
  file-size aesthetics
- no recreation of native browser validation in custom JavaScript
- no second settings metadata registry beside `SETTINGS_SCHEMA`
- no second routing resolver beside `resolve_model_routing_part(...)` plus
  shared routing adapters
- no removal of domain vocabulary where `BigQuery` remains genuine job-skill
  taxonomy rather than backend infrastructure
- no speculative multi-backend support reintroduction

## Risks and Mitigations

- risk: child specs reopen architecture from scratch and drift from master
  invariants
  - mitigation: require every child spec to cite this master spec and inherit
    its ownership map and phase boundary
- risk: rewrite pressure grows because monolith files are large
  - mitigation: canonical owner convergence and deletion happen before optional
    extraction work
- risk: partial deletion leaves stale tests/docs or hidden helpers alive
  - mitigation: every removal proof includes repo search plus focused route/
    template/test evidence
- risk: settings migration breaks saved rows or UI forms
  - mitigation: canonicalize on read and write, keep typed round-trip tests, and
    phase settings work after backend/stage cleanup
- risk: lifecycle hardening changes operator behavior unexpectedly
  - mitigation: require capability and transition tests across route, worker,
    and repository layers before behavior changes ship
- risk: routing convergence drops trigger-time provenance or override clarity
  - mitigation: preserve trigger-time runtime envelope and verify startup/worker/
    diagnostics provenance against same routed truth

## Validation Plan

- proof target: canonical owner map is complete and reuse-first
  - method: inspection
  - evidence: approved master spec plus child specs that reuse named owners

- proof target: stage taxonomy converges on one registry
  - method: test + repo search
  - evidence: parity tests reference one registry and active code no longer
    maintains independent hardcoded stage lists

- proof target: lifecycle policy is symmetric across UI, worker, and
  persistence
  - method: test
  - evidence: focused transition/capability tests in `tests/test_fitcv_cp/`

- proof target: settings contract is one-owner and native-first
  - method: test + inspection
  - evidence: `tests/test_fitcv_cp/test_settings_schema.py` and related app tests
    prove same schema drives server validation and native attrs

- proof target: routing truth is centralized on existing resolvers
  - method: test + repo search
  - evidence: control-plane config/routing tests plus absence of ad hoc routing
    parsing outside canonical boundary helpers

- proof target: SQLite-only backend truth is real, not cosmetic
  - method: test + repo search
  - evidence: no active interface carries ignored BigQuery-era params, startup
    and worker tests remain green, docs describe only supported backend truth

- proof target: removed diagnostics and replay/dead-letter residue stay absent
  - method: repo search + focused tests
  - evidence: absence checks for removed labels, routes, payload keys, config
    keys, and helper names, with explicit allowlist for any retained public
    contract

- proof target: persistence no longer has hidden split-brain fallback paths
  - method: test + inspection
  - evidence: sqlite-store and worker tests show atomic primary persistence or
    explicit failure, with no dead-letter side store or incoherent in-memory
    shadow cache

## Completion Criteria

1. all Key Deliverables are satisfied
2. child phase specs exist for all ordered lanes defined in this document
3. downstream implementation plans inherit this master spec rather than
   redefining ownership or phase order
4. every child item is `completed`, `superseded`, or `dropped`

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/planning/planning-dispatch.md`
- `scripts/validate_planning_lifecycle.py`
