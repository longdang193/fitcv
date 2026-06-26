---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: fitcv-cp-ssot-immediate-patch
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - reviews/2026-06-26-09-55-57-fitcv-cp/FITCV_CP_SSOT_SYMMETRY_INVARIANCE_REVIEW.md
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/orchestrator.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/reconciler_service.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/templates/base.html
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/
related_features: []
related_stages: []
---

# Detailed Spec: FitCV control-plane SSOT immediate patch

## Goal

Define concrete, bounded patch scope for highest-confidence control-plane SSOT,
symmetry, and invariance defects from
`reviews/2026-06-26-09-55-57-fitcv-cp/FITCV_CP_SSOT_SYMMETRY_INVARIANCE_REVIEW.md`.

This spec covers immediate correctness fixes and small structural hardening only.
It does not approve full control-plane architecture rewrite.

## Triage

Layer: change
Feature type: MODIFY
Summary: patch live control-plane state, orchestration, settings, and UI SSOT splits that can produce wrong persisted truth or backend-dependent behavior
Reasoning: current code already has canonical owners (`BackendRuntime`, `RunSubmission`, `ControlPlaneStore`) but live paths still bypass them in several correctness-critical places
Invariants:
  - one run request persists one authoritative orchestration binding
  - equivalent SQLite and BigQuery paths preserve same run/settings contract unless explicit compatibility downgrade is recorded
  - terminal lifecycle states do not re-enter active execution through retry/cancel races
  - web and worker read same effective runtime and settings identity rules
Dependencies:
  - `reviews/2026-06-26-09-55-57-fitcv-cp/FITCV_CP_SSOT_SYMMETRY_INVARIANCE_REVIEW.md`
  - existing `BackendRuntime`, `RunSubmission`, and `ControlPlaneStore` abstractions
Affected stages:
  - none
Affected features:
  - none
Primary lens: cross-cutting
Affected docs:
  feature_source: none
  feature_yaml: none
  feature_lineage: none
  feature_history: none
  stage_source: none
  stage_contract: none
  feature_docs: []
  cross_cutting_docs:
    - `docs/architecture.md`
    - `docs/usage.md`
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

### Deliverable 1: Runtime and persistence path ownership is single-owner enough for live correctness

The patch must route backend type, SQLite path, and BigQuery client acquisition
through one live owner per concern so web, worker, reconciler, and store paths do
not silently diverge.

### Deliverable 2: Orchestration and lifecycle truth becomes durable and race-safe enough for current deployments

The patch must stop reconstructing orchestration truth from process-local cache
and must close current retry/cancel/reconcile races that can create duplicate or
resurrected execution.

### Deliverable 3: Settings and UI contract behavior becomes endpoint-invariant

The patch must make canonical settings key behavior and visible write failure
behavior consistent across single-key and grouped routes, and must remove the
highest-risk shared-style ownership conflicts in the base templates.

### Deliverable 4: Validation remains bounded and executable

Each adopted fix must land with direct regression proof in
`tests/test_fitcv_cp/` and must avoid broad extraction work unless a smaller
existing owner cannot carry the fix.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm which review findings are live correctness bugs versus follow-up architecture debt

**Steps:**
- [x] inspect all live call paths for runtime resolution, submission persistence, lifecycle transition, and settings writes
- [x] mark each finding as `fix now` or `defer`
- [x] reuse existing owners before inventing new modules or interfaces

**Verification:**
- [x] each fix-now item maps to one current source owner and one minimal patch site

**Exit Criteria:**
- no immediate patch item depends on unverified large-scale refactor assumptions

### Wave 2: Decision closure

**Purpose:**
- lock patch boundaries and concrete contract rules before implementation planning

**Steps:**
- [x] define one owner for backend runtime and SQLite path resolution
- [x] define one persisted owner for orchestration backend/run binding
- [x] define allowed retry/cancel/reconcile transitions for current lifecycle states
- [x] define canonical settings-key persistence and error semantics
- [x] define minimum template SSOT fixes worth landing now

**Verification:**
- [x] every adopted finding has explicit chosen owner, patch boundary, and non-goal

**Exit Criteria:**
- implementation can proceed as targeted patch series rather than architecture program

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof concrete before implementation starts

**Steps:**
- [x] define targeted tests for each adopted correctness fix
- [x] define inspection proof for deferred architecture items
- [x] define docs follow-up only where user-visible behavior changes

**Verification:**
- [x] validation plan covers behavior, not only code motion

**Exit Criteria:**
- spec is ready for implementation planning

## Design Decisions

### Decision: Patch current live owners, not full module extraction

- context: review found real correctness bugs plus several true but larger structural problems in `app.py` and taxonomy/artifact ownership
- choice: land only changes that can ride existing owners such as `BackendRuntime`, `RunSubmission`, `ControlPlaneStore`, and current template base classes
- alternatives considered:
  - full `app.py` service-layer extraction first
  - full taxonomy/artifact store redesign in same patch
- impact:
  - keeps patch reviewable
  - fixes live correctness first
  - defers broad modular cleanup to follow-up spec/plan

### Decision: `BackendRuntime` becomes live source for backend type and SQLite path

- context: backend selection and SQLite location are currently split across `backend_runtime.py`, `bq_store.py`, `settings_store.py`, and `worker_job.py`
- choice: all live SQLite-path and backend-mode resolution must flow from `resolve_backend_runtime()` or values derived from it and injected once into store/runtime context
- alternatives considered:
  - keep local `_local_sqlite_path()` helpers and only align defaults
- impact:
  - removes env-only split brain between web, worker, and settings paths
  - allows tests to assert one path owner

### Decision: `RunSubmission` remains rich object through all internal persistence paths

- context: current compatibility tuple wrappers and `_RUN_SUBMISSION_CACHE` allow backend truth to be reconstructed from current process state
- choice: internal trigger, continue, retry, and persistence paths must carry `RunSubmission` until durable binding is written; tuple return shape may remain only for external compatibility shims
- alternatives considered:
  - keep cache reconstruction and extend TTL/size
- impact:
  - persisted `orchestration_backend` becomes backend-that-accepted-request, not backend-guessed-later

### Decision: Immediate lifecycle hardening uses bounded guards, not new state machine framework

- context: current code allows retry from active states, queued cancel can finalize without backend confirmation, and worker can move cancelled run back to running
- choice: patch current state transitions with explicit guards and compare-current-state checks where existing persistence surfaces allow them; defer general transition framework/CAS API to follow-up work
- alternatives considered:
  - full shared transition engine in same patch
- impact:
  - closes live duplicate/resurrection bugs fast
  - avoids cross-cutting redesign in one pass

### Decision: Settings persistence canonicalizes keys at load/save boundary

- context: settings alias normalization currently adds canonical keys without deleting legacy keys, and single-key writes hide BigQuery failures
- choice: add one canonical key helper and require both load/save and route-layer responses to use canonical keys; single-key and grouped writes must both surface BigQuery failure
- alternatives considered:
  - route-only normalization
  - keep legacy alias rows and prefer latest on read
- impact:
  - same semantic setting has one stored identity and one visible error contract

### Decision: Template patch lands only shared-owner conflicts with clear blast radius

- context: review found large inline-style debt plus base-class meaning drift and generic hover override bugs
- choice: fix shared-class ownership and generic button-hover conflicts now; defer mass inline-style extraction and JS-controller cleanup
- alternatives considered:
  - full template design-system cleanup
- impact:
  - removes current cross-page style overrides without turning patch into UI rewrite

## Invariants

- same control-plane config plus same env overrides must resolve same backend mode, project, dataset, and SQLite path across web, worker, reconciler, and settings persistence
- persisted `orchestration_backend` and `orchestration_run_id` must describe backend that accepted run execution request, not backend inferred from later process state
- retry request on `RUNNING`, `QUEUED`, `CANCELLING`, `CANCELLED`, or `SUCCEEDED` must never enqueue another active attempt
- worker claim must not transition a run from `CANCELLED` or `CANCELLING` back to `RUNNING`
- unknown persisted run status must not be silently re-labeled as true pipeline failure without preserving diagnostic distinction
- canonical and legacy setting aliases must resolve to one persisted key and one active value
- same settings write failure class must surface consistently across single-key and grouped endpoints
- shared CSS class names in `base.html` must keep one invariant meaning across pages unless explicit modifier classes are introduced

## Acceptance Criteria

1. Runtime/backend path tests prove web, worker, and settings store resolve one SQLite path contract from one owner.
2. Prefect fallback or adapter mismatch tests prove persisted orchestration binding uses actual accepted backend, not cache-miss reconstruction.
3. Retry endpoint rejects active or terminal non-failed states; worker cancellation race tests prove cancelled runs do not restart.
4. Reconcile tests prove queue transport `finished` is not treated as pipeline success without domain-terminal evidence.
5. BigQuery and SQLite tests prove `jobs_input_manifest_json` is preserved symmetrically for inserted/read runs.
6. Settings alias tests prove legacy and canonical keys collapse to one canonical persisted identity.
7. Single-key settings save raises on BigQuery write failure just like grouped save.
8. Template tests or focused DOM assertions prove generic button hover no longer overrides specialized variants and shared class meanings are no longer page-redefined by same class name.

## Non-Goals

- no full `app.py` decomposition into service modules in this patch
- no new persistent attempt ledger or full compare-and-set lifecycle framework unless required to close one adopted bug
- no complete taxonomy-store extraction in this patch
- no mass removal of all inline styles or inline handlers from templates
- no broad artifact-backend protocol redesign in this patch
- no publication/governance refactor outside touched docs and tests

## Risks and Mitigations

- risk: patch scope balloons into full control-plane rewrite
  - mitigation: each code change must map to one accepted finding and one regression proof target
- risk: changing runtime-path ownership breaks older SQLite fallback flows
  - mitigation: keep compatibility shim at one owner and add cross-path tests before deleting helpers
- risk: lifecycle guard changes alter operator behavior unexpectedly
  - mitigation: add endpoint tests for retry/cancel/reconcile paths and preserve current user-visible statuses unless explicitly corrected
- risk: settings canonicalization surprises existing rows with legacy keys
  - mitigation: canonicalize on read as well as write; add mixed-order legacy/canonical fixtures
- risk: template class-owner fixes regress page layout
  - mitigation: keep CSS diff narrow and cover specialized button/style conflicts with focused HTML assertions

## Validation Plan

- proof target: runtime/backend path ownership is unified enough for live correctness
  - method: test
  - evidence: targeted tests for `BackendRuntime`, store resolution, worker runtime boot, and settings-store SQLite path usage

- proof target: orchestration submission truth is durable and cache-miss invariant
  - method: test
  - evidence: trigger/continue/retry tests showing persisted backend binding matches accepted `RunSubmission` under normal and fallback paths

- proof target: lifecycle guards block duplicate or resurrected execution
  - method: test
  - evidence: retry endpoint tests, cancel/worker-claim race tests, and reconcile tests for queued/running orphan paths

- proof target: BigQuery/SQLite run contract parity covers `jobs_input_manifest_json`
  - method: test
  - evidence: `bq_store` and app-level tests for insert/read parity and compatibility fallback behavior

- proof target: settings identity and failure semantics are endpoint-invariant
  - method: test
  - evidence: settings schema/store/app tests covering alias collapse, canonical response keys, and raised BigQuery failure on single-key writes

- proof target: shared template owner conflicts are removed without UI rewrite
  - method: inspection + targeted test
  - evidence: CSS/HTML assertions for specialized hover precedence and elimination of duplicate shared-class meaning for immediate conflict cases

- proof target: unknown run status remains diagnosable instead of silently becoming ordinary failure
  - method: test
  - evidence: store-reader tests preserving raw/unknown-state diagnostic behavior or explicit `UNKNOWN` handling contract

## Completion Criteria

1. all Key Deliverables are satisfied
2. each adopted finding has regression proof in `tests/test_fitcv_cp/` or explicit focused inspection evidence where runtime testing is not practical
3. deferred architecture findings are listed as non-goals or follow-up work rather than half-implemented abstractions
4. implementation can proceed without inventing new ownership rules beyond this spec

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
