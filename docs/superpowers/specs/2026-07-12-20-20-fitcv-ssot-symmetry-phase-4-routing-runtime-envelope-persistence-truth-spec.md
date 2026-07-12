---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-ssot-symmetry-phase-4-routing-runtime-envelope-persistence-truth
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md
  - docs/superpowers/specs/2026-07-12-09-34-fitcv-ssot-symmetry-phase-1-legacy-surface-and-backend-trim-spec.md
  - docs/superpowers/specs/2026-07-12-13-10-fitcv-ssot-symmetry-phase-2-stage-lifecycle-late-stage-consolidation-spec.md
  - docs/superpowers/specs/2026-07-12-18-35-fitcv-ssot-symmetry-phase-3-settings-schema-native-form-boundary-spec.md
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/settings_system/feature.source.yaml
  - docs/features/trigger_run_management/feature.source.yaml
  - src/fitcv/config.py
  - src/fitcv/persistence.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/data_plane.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/run_artifact_mirror.py
  - src/fitcv_cp/runtime_contracts.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/worker_job.py
  - docs/api.md
  - docs/architecture.md
  - docs/configuration.md
  - docs/observability.md
  - docs/generated/planning_lineage.yaml
  - tests/test_config.py
  - tests/test_runtime_routing.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_control_plane_config.py
  - tests/test_fitcv_cp/test_main.py
  - tests/test_fitcv_cp/test_settings_store.py
  - tests/test_fitcv_cp/test_settings_store_sqlite.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - inspection_debugging
  - settings_system
  - trigger_run_management
related_stages:
  - cv_analysis
  - cv_generation
---

# Detailed Spec: FitCV SSOT / symmetry Phase 4 routing, runtime-envelope, and persistence-truth convergence

## Goal

Execute fourth concrete remediation lane from
`docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`:

- converge live routing truth on existing routing owners instead of app/startup-local env parsing
- make trigger-time runtime envelope the one replayable run-scoped runtime truth for downstream inspection and synonym-triage flows
- converge SQLite path and persistence call surfaces on one SQLite-native owner set
- retire temporary Phase 1 backend-compat boundary shims and hidden persistence shadow state that still survive in control-plane code

This phase is routing/persistence convergence only. It does not reopen stage registry, lifecycle policy, late-stage contract, or settings-schema ownership.

## Problem

Current repo still has four live Phase 4 drift classes.

1. Routing/env truth is still split across canonical and ad hoc owners.
   - `src/fitcv/config.py` already owns `resolve_model_routing_part(...)` and `resolve_langgraph_runtime_expectation(...)`
   - `src/fitcv/runtime_routing.py` already owns CV-generation-specific derived helpers
   - but `src/fitcv_cp/main.py:_warn_or_fail_langgraph_override_drift()` re-parses `FITCV_LANGGRAPH_*`
   - `src/fitcv_cp/app.py:_resolve_synonym_triage_runtime()` re-parses `FITCV_LANGGRAPH_*` and partially overlays persisted run data
   - `src/fitcv_cp/app.py` settings-mode summary still reads live env directly for provider/model authority state

2. Trigger-time runtime envelope is captured once but not treated as sole run-scoped truth afterwards.
   - `_apply_trigger_runtime_envelope(...)` persists `runtime_inputs.agentic_runtime_expectation`
   - later run-scoped consumers still mix process env and persisted payloads instead of reading one stable run snapshot first
   - this risks inspection drift when live env changes after trigger time

3. SQLite path truth is still duplicated.
   - `src/fitcv/persistence.py:get_local_sqlite_path()` reads env directly
   - `src/fitcv_cp/backend_runtime.py:resolve_backend_runtime()` reimplements sqlite path resolution with control-plane config fallback
   - `src/fitcv_cp/sqlite_store.py:_local_sqlite_path()` duplicates runtime/env fallback
   - `src/fitcv_cp/settings_store.py:_local_sqlite_path()` adds separate `FITCV_CP_SETTINGS_SQLITE_PATH` override that can split settings persistence from run/event persistence

4. Persistence surfaces still carry fake backend-compat plumbing and shadow state.
   - `src/fitcv_cp/app.py:create_app(...)` still seeds `client=None`, `store_project="local"`, and `store_dataset="fitcv"` and threads them through active calls
   - `src/fitcv_cp/store.py:ControlPlaneStore._call()` still catches `TypeError` and injects `client` / `project` / `dataset` compatibility kwargs
   - `src/fitcv_cp/reporter.py`, `src/fitcv_cp/run_artifact_mirror.py`, `src/fitcv_cp/queue.py`, and `src/fitcv_cp/worker_job.py` still speak sqlite through BigQuery-era parameter shapes
   - `src/fitcv_cp/sqlite_store.py` still keeps `_LOCAL_RUNS` as in-process shadow state beside persisted sqlite truth

Until this lane lands, routing provenance and persistence behavior still depend on reading multiple partially overlapping helpers instead of one routed owner set plus one persisted sqlite truth surface.

## Relationship To Existing Specs

This Phase 4 spec is authoritative only for bounded routing/persistence convergence after Phase 1 through Phase 3.

- `docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`
  remains parent authority for phase order, final architecture, and cross-phase invariants.
- `docs/superpowers/specs/2026-07-12-09-34-fitcv-ssot-symmetry-phase-1-legacy-surface-and-backend-trim-spec.md`
  remains precondition authority for initial SQLite-only direction and deletion of unsupported operator residue. Phase 4 retires any temporary boundary-local backend-compat shims that were allowed to survive that lane.
- `docs/superpowers/specs/2026-07-12-13-10-fitcv-ssot-symmetry-phase-2-stage-lifecycle-late-stage-consolidation-spec.md`
  remains authority for stage/lifecycle/late-stage owners. Phase 4 may consume those owners but must not redefine them.
- `docs/superpowers/specs/2026-07-12-18-35-fitcv-ssot-symmetry-phase-3-settings-schema-native-form-boundary-spec.md`
  remains authority for settings-schema ownership. Phase 4 may change where mode-strip/runtime notes get their routed truth, but must not move page semantics back out of schema.

## Triage

Layer: change
Feature type: REPLACE
Summary: replace ad hoc LangGraph/runtime parsing and sqlite compatibility residue with one routed runtime-envelope contract and one SQLite-native persistence truth surface
Reasoning: current repo already has partial routing and backend owners, but active startup/app/store helpers still bypass them or preserve fake backend portability and split-brain persistence seams
Invariants:
  - `resolve_model_routing_part(...)` stays root SSOT for routing part resolution
  - `resolve_langgraph_runtime_expectation(...)` stays root SSOT for env-override-aware live LangGraph expectation
  - run-scoped runtime provenance must be preserved at trigger time and reused later without reinterpretation drift
  - run/event/settings persistence must resolve to one SQLite truth surface
  - active control-plane runtime must not carry ignored `client` / `project` / `dataset` backend-compat args
Dependencies:
  - Phase 1 deletion/backend trim outputs
  - Phase 2 stage/lifecycle/late-stage owners
  - Phase 3 settings-schema/page-contract owners
  - current `resolve_model_routing_part(...)`, `resolve_langgraph_runtime_expectation(...)`, `runtime_routing.py`, `BackendRuntime`, `sqlite_store.py`, and `settings_store.py`
Affected stages:
  - cv_analysis
  - cv_generation
Affected features:
  - inspection_debugging
  - settings_system
  - trigger_run_management
Primary lens: cross-cutting
Affected docs:
  feature_source:
    - docs/features/inspection_debugging/feature.source.yaml
    - docs/features/settings_system/feature.source.yaml
    - docs/features/trigger_run_management/feature.source.yaml
  feature_yaml: none
  feature_lineage: none
  feature_history: none
  stage_source: none
  stage_contract: none
  feature_docs: []
  cross_cutting_docs:
    - docs/api.md
    - docs/architecture.md
    - docs/configuration.md
    - docs/observability.md
  readme: none
  generated:
    - docs/generated/planning_lineage.yaml
Generated refresh required: yes
Capability IDs:
  - inspection_debugging.prompt-provenance-diagnostics
  - inspection_debugging.settings-used-export
  - settings_system.trigger-time-effective-settings-snapshot
  - settings_system.settings-used-exports
  - trigger_run_management.job-input-modes
  - trigger_run_management.run-owned-artifact-exports
Invariant IDs:
  - none
Spec needed: yes
Plan needed: yes

## Key Deliverables

### Deliverable 1: existing routing owners become complete and shared

Phase 4 must keep routing ownership boring and explicit.

Owner split after this lane:

- `src/fitcv/config.py`
  - owns generic part routing via `resolve_model_routing_part(...)`
  - owns env-override-aware live LangGraph expectation via `resolve_langgraph_runtime_expectation(...)`
- `src/fitcv/runtime_routing.py`
  - owns capability-specific derived payloads built from those resolvers
  - examples: LangGraph env override maps, runtime provenance summaries, drift-comparison helpers, or other pure adapter payloads needed by startup/app/pipeline consumers

`src/fitcv_cp/main.py`, `src/fitcv_cp/app.py`, and runtime/pipeline callers must stop parsing `FITCV_LANGGRAPH_PROVIDER`, `FITCV_LANGGRAPH_MODEL`, `FITCV_LANGGRAPH_OPENAI_BASE_URL`, and `FITCV_LANGGRAPH_WIRE_API` directly when shared helpers can answer the same question.

Explicit allowlist for direct raw `FITCV_LANGGRAPH_*` reads after Phase 4:

- `src/fitcv/config.py`
- `src/fitcv/runtime_routing.py`
- tests that verify env-override behavior

Any other production-path raw read must be justified as a bounded exception in the implementation patch.

No new routing service class, provider manager, or dependency-injected runtime object.

### Deliverable 2: trigger-time runtime envelope becomes sole run-scoped truth

Phase 4 must distinguish two truths cleanly.

1. live control-plane runtime expectation
   - what current process env + routing config say now
   - owner: existing routing helpers
2. persisted trigger-time runtime expectation
   - what specific run captured when trigger happened
   - owner: run-scoped persisted effective settings / settings-used payloads

Rules:

- run creation continues to snapshot runtime expectation exactly once into trigger-time effective settings
- run-scoped consumers such as synonym triage workspace, run detail diagnostics, and `settings-used.json` shaping read persisted trigger-time expectation first
- live env/routing may still power future-run settings/admin summaries, but only through shared routing helpers and never by app-local raw env parsing
- fallback to live env for run-scoped consumers is allowed only when a bounded legacy run truly lacks persisted expectation payloads

Canonical persisted snapshot contract for this phase:

- source path: `effective_settings_json.runtime_inputs.agentic_runtime_expectation`
- required fields:
  - `provider`
  - `model`
  - `base_url`
  - `wire_api`
  - `source`
- `settings-used.json` may mirror this contract for operator inspection, but it is not a second human-owned source
- if a legacy run lacks this block, bounded fallback may consult current routed live expectation only for inspection continuity; new runs must always persist the full block

### Deliverable 3: one SQLite path owner exists

Phase 4 must converge SQLite path resolution on one shared owner.

Chosen owner split from master spec:

- `src/fitcv/config.py`
  - owns backend type validation (`sqlite` only)
- `src/fitcv/persistence.py`
  - owns shared SQLite path resolution
- `src/fitcv_cp/backend_runtime.py`
  - owns control-plane runtime envelope and reuses shared path helper instead of reimplementing path resolution rules

Canonical SQLite path precedence after Phase 4:

1. `FITCV_CP_SQLITE_PATH`
2. `control_plane.data_backend.sqlite.path`
3. `data/fitcv_cp.sqlite3`

All active runtime and control-plane sqlite consumers must use this exact precedence through one shared helper path.

Active sqlite consumers in `src/fitcv/` and `src/fitcv_cp/` must route through that shared path owner rather than keeping parallel `_local_sqlite_path()` logic with different env fallbacks.

`FITCV_CP_SETTINGS_SQLITE_PATH` is retired in this phase. Tests and docs must stop treating it as supported behavior. One SQLite file remains canonical truth for run, event, and settings persistence.

### Deliverable 4: persistence interfaces become SQLite-native and shadow-state-free

Phase 4 must remove active BigQuery-era compatibility signatures from supported control-plane persistence paths.

Examples in scope:

- `client`, `project`, and `dataset` threading through `src/fitcv_cp/app.py`
- `ControlPlaneStore._call()` TypeError-based compat shim in `src/fitcv_cp/store.py`
- sqlite-store public call surface that still advertises ignored backend-compat params
- `PipelineReporter` constructor and calls that still carry project/dataset shape
- `persist_terminal_run_artifact_mirror(...)` compatibility kwargs
- inline queue/worker status/event updates that still pass fake local project/dataset identifiers

This lane must also remove hidden shadow state that can diverge from sqlite truth.

Minimum examples in scope:

- `_LOCAL_RUNS` in `src/fitcv_cp/sqlite_store.py`
- any equivalent in-memory cache or side-path that can disagree with persisted sqlite rows for run/event/settings truth

### Deliverable 5: phase boundary stays tight

This lane finishes routing/runtime-envelope and persistence-truth convergence only.

It does not:

- redesign model-routing config schema
- reopen settings-page ownership
- split monolith files for style only
- introduce a second storage backend or remote state store
- absorb optional Phase 5 monolith-reduction work

## Task/Wave Breakdown

### Wave 1: Source-first routing and persistence inventory

**Purpose:**
- turn master-level Phase 4 goals into exact live-owner and residue inventory

**Steps:**
- [ ] enumerate every active read of `FITCV_LANGGRAPH_PROVIDER`, `FITCV_LANGGRAPH_MODEL`, `FITCV_LANGGRAPH_OPENAI_BASE_URL`, and `FITCV_LANGGRAPH_WIRE_API`
- [ ] classify each read as canonical owner, valid adapter use, or duplicate app/startup residue
- [ ] enumerate every active SQLite path resolver and compare fallback order
- [ ] enumerate every active control-plane persistence API that still carries `client` / `project` / `dataset`
- [ ] confirm where `_LOCAL_RUNS` or equivalent shadow state is still written/read

**Verification:**
- [ ] each Phase 4 drift class maps to named source paths and a keep/delete/move decision

**Exit Criteria:**
- no implementation step depends on vague “routing cleanup” or “persistence cleanup” wording

### Wave 2: Routing and runtime-envelope convergence

**Purpose:**
- converge live routing helpers and run-scoped runtime provenance without changing unrelated feature behavior

**Steps:**
- [ ] move startup drift checks onto shared routing-comparison helpers instead of raw env parsing
- [ ] move app-level synonym/runtime summary helpers onto shared routing/runtime helpers
- [ ] keep trigger-time runtime expectation snapshot explicit and immutable per run
- [ ] make run-scoped diagnostics/triage prefer persisted runtime snapshot over current process env

**Verification:**
- [ ] routed provider/model/base_url/wire_api facts are shared across startup, pipeline, settings/admin summaries, and run-scoped diagnostics without duplicate parsing logic

**Exit Criteria:**
- no active app/startup helper re-implements LangGraph routing truth already available from canonical owners

### Wave 3: SQLite truth convergence and compat-shim retirement

**Purpose:**
- remove fake backend portability and shadow persistence truth from supported control-plane paths

**Steps:**
- [ ] converge SQLite path resolution on one shared helper
- [ ] remove `FITCV_CP_SETTINGS_SQLITE_PATH` split-path behavior unless explicitly retained as supported contract
- [ ] remove `client` / `project` / `dataset` from active sqlite-native persistence call surfaces
- [ ] delete `ControlPlaneStore` compat injection and sqlite-store compat signatures no longer needed
- [ ] delete `_LOCAL_RUNS` and any equivalent hidden shadow cache
- [ ] keep run artifact mirror and settings-used exports reading persisted sqlite truth only

**Verification:**
- [ ] repo search shows no active supported control-plane path still depends on BigQuery-era sqlite compatibility params or in-memory shadow run state

**Exit Criteria:**
- routing and persistence truths are each one-owner and replay-safe

## Design Decisions

### Decision: keep current routing resolver ladder, widen helpers only where needed

- context: current repo already has `resolve_model_routing_part(...)`, `resolve_langgraph_runtime_expectation(...)`, and `runtime_routing.py`
- choice: reuse those owners and add the minimum pure helper functions needed for startup/app/runtime summaries instead of inventing a new routing service layer
- alternatives considered:
  - new control-plane routing service object
  - leave duplicate startup/app parsing and enforce parity only with tests
- impact:
  - shortest SSOT path
  - pure helper reuse across startup, app, and runtime code

### Decision: live routing truth and persisted run truth stay distinct

- context: one process can change env after a run is triggered; later inspection must still explain what that run used
- choice: preserve separate concepts for live expectation and trigger-time snapshot, and require run-scoped consumers to prefer persisted snapshot
- alternatives considered:
  - always read current env for run-scoped diagnostics
  - store nothing and reconstruct runtime provenance later
- impact:
  - replay-safe diagnostics
  - no hidden reinterpretation drift when env changes after trigger time

### Decision: shared SQLite path owner lives in `src/fitcv/persistence.py`

- context: current path resolution is duplicated across runtime and control-plane modules with slightly different fallbacks
- choice: converge on one shared sqlite-path helper and let control-plane runtime/store code adapt to it
- alternatives considered:
  - keep duplicate `_local_sqlite_path()` helpers in each module
  - move path truth into a new dedicated config/runtime package
- impact:
  - one path rule for runtime, stores, and tests
  - simpler docs and lower split-brain risk

### Decision: delete compat signatures instead of hiding them behind wrappers

- context: `ControlPlaneStore._call()` currently preserves fake backend portability by catching `TypeError` and injecting `client` / `project` / `dataset`
- choice: make active sqlite-native call surfaces explicit and delete the compat shim
- alternatives considered:
  - keep compat shim forever because tests can still pass
  - add another adapter layer to translate old signatures
- impact:
  - active signatures finally match supported backend truth
  - repo search can prove backend-compat residue is gone

### Decision: `_LOCAL_RUNS` is deletion scope, not acceptable shadow cache

- context: reads already prefer sqlite, but writes still populate `_LOCAL_RUNS`
- choice: remove in-process run shadow state unless implementation discovers a truly required bounded cache with explicit invariants and tests
- alternatives considered:
  - keep shadow cache because it is “harmless” if reads prefer sqlite
  - formalize in-memory cache as second persistence layer
- impact:
  - one persisted run truth
  - cleaner recovery/debug story across web and worker processes

## Invariants

- provider/model/base_url/wire_api routing truth comes from shared routing owners, not app/startup-local parsing
- run-scoped runtime provenance is captured once at trigger time and reused later without reinterpretation drift
- future-run admin/settings summaries may show live routed truth only through shared helpers
- run/event/settings persistence resolve to one SQLite path and one persisted truth surface
- active sqlite-native control-plane interfaces do not expose ignored `client` / `project` / `dataset` args
- no `_LOCAL_RUNS` or equivalent shadow store survives as authoritative or fallback run truth
- run artifact mirrors and `settings-used.json` exports derive from persisted sqlite-backed run truth
- Phase 4 does not reopen stage, lifecycle, late-stage, or settings-schema ownership

## Acceptance Criteria

1. `src/fitcv_cp/main.py` and `src/fitcv_cp/app.py` no longer parse `FITCV_LANGGRAPH_PROVIDER`, `FITCV_LANGGRAPH_MODEL`, `FITCV_LANGGRAPH_OPENAI_BASE_URL`, or `FITCV_LANGGRAPH_WIRE_API` directly for questions already answerable by shared routing helpers.
2. Run-scoped runtime consumers prefer persisted trigger-time expectation payloads over current process env whenever that snapshot exists.
3. One shared SQLite path resolver exists, and active runtime/control-plane modules stop keeping divergent local path helpers or split settings-path overrides.
4. Direct raw `FITCV_LANGGRAPH_*` reads outside `src/fitcv/config.py`, `src/fitcv/runtime_routing.py`, and env-override tests are removed or explicitly justified as bounded exceptions.
5. Active control-plane sqlite-native persistence calls no longer require fake `client` / `project` / `dataset` plumbing.
6. `ControlPlaneStore._call()` no longer preserves backend compatibility by TypeError injection.
7. `_LOCAL_RUNS` is removed, and run/event/settings truth has no hidden in-memory persistence shadow path.
8. Focused routing, startup, worker, sqlite-store, and settings-store tests prove shared routing truth, persisted runtime-envelope reuse, exact sqlite-path precedence, and one SQLite truth surface.
9. Phase 4 docs describe live routing truth and run-scoped persisted truth without ambiguity.

## Non-Goals

- no redesign of `control_plane.model_routing` schema
- no new routing service class, dependency-injection tree, or provider plugin system
- no reopening of settings-page grouping/card/filter ownership from Phase 3
- no Phase 5 file-splitting or broad monolith reduction work
- no reintroduction of multi-backend control-plane support
- no removal of legitimate domain uses of `BigQuery` in job/taxonomy content

## Risks and Mitigations

- risk: run detail or synonym triage surfaces change behavior when they stop reading live env opportunistically
  - mitigation: add focused tests for persisted-trigger snapshot preference and bounded fallback behavior when old runs lack snapshots
- risk: sqlite-path convergence changes local dev/test assumptions
  - mitigation: keep env override path supported through the shared owner and update docs/tests in same lane
- risk: removing compat signatures breaks mocks and thin helper wiring
  - mitigation: land focused tests for startup, app, worker, sqlite store, and settings store in same patch; delete compat shims only after direct callers migrate
- risk: shadow-cache deletion exposes missing sqlite writes
  - mitigation: use source-search plus focused persistence tests to prove reads and writes still succeed without `_LOCAL_RUNS`

## Validation Plan

- proof target: routing truth is centralized on existing resolvers and shared adapter helpers
  - method: repo search + test
  - evidence: `tests/test_runtime_routing.py`, `tests/test_fitcv_cp/test_control_plane_config.py`, and source-search allowlist proof that raw `FITCV_LANGGRAPH_*` reads remain only in `src/fitcv/config.py`, `src/fitcv/runtime_routing.py`, and env-override tests

- proof target: trigger-time runtime envelope is replay-safe and reused by run-scoped consumers
  - method: test
  - evidence: focused `tests/test_fitcv_cp/test_app.py` and `tests/test_fitcv_cp/test_worker_job.py` cases for persisted runtime snapshot preference and `settings-used.json` truth

- proof target: one SQLite path owner remains across runtime and control-plane modules
  - method: repo search + test
  - evidence: `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_settings_store.py`, `tests/test_fitcv_cp/test_settings_store_sqlite.py`, and tests/source proof for exact precedence `FITCV_CP_SQLITE_PATH` > `control_plane.data_backend.sqlite.path` > `data/fitcv_cp.sqlite3`

- proof target: backend-compat shims are retired from active sqlite-native call surfaces
  - method: repo search + test
  - evidence: no active supported calls pass `project=store_project`, `dataset=store_dataset`, or equivalent fake backend args; startup/app/worker tests remain green

- proof target: persistence truth has no hidden shadow store
  - method: repo search + test
  - evidence: absence of `_LOCAL_RUNS` and focused sqlite-store tests proving persisted read/write behavior without in-memory run mirrors

- proof target: cross-cutting docs are truthful about routing and persistence ownership
  - method: inspection
  - evidence: `docs/architecture.md`, `docs/configuration.md`, and `docs/observability.md` describe one routed owner set and one persisted sqlite truth surface

## Completion Criteria

1. all Key Deliverables are satisfied
2. downstream Phase 4 implementation plan can execute without reopening routing or persistence ownership
3. master spec remains aligned and no longer understates active Phase 4 target surfaces
4. generated planning lineage is refreshed after spec creation/update

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/planning/planning-dispatch.md`
- `scripts/validate_planning_lifecycle.py`
