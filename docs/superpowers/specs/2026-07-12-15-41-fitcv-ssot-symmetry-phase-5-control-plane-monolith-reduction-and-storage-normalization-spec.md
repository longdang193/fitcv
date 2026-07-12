---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-ssot-symmetry-phase-5-control-plane-monolith-reduction-and-storage-normalization
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md
  - docs/superpowers/specs/2026-07-12-20-20-fitcv-ssot-symmetry-phase-4-routing-runtime-envelope-persistence-truth-spec.md
  - src/fitcv_cp/app.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/worker_run_support.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/run_artifact_mirror.py
  - docs/architecture.md
  - docs/api.md
  - docs/observability.md
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_store.py
related_features:
  - inspection_debugging
  - trigger_run_management
related_stages:
  - cv_analysis
  - cv_generation
---

# Detailed Spec: FitCV SSOT / symmetry Phase 5 bounded control-plane monolith reduction and optional storage normalization

## Goal

Execute fifth concrete remediation lane from
`docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`:

- reduce control-plane monolith risk only where Phases 1-4 already stabilized ownership
- extract bounded pure/helper clusters from `src/fitcv_cp/app.py` and `src/fitcv_cp/worker_job.py` without changing route contracts, worker entrypoints, or SQLite truth
- normalize touched storage helpers only when that deletion/support cleanup is required by the extraction work

This phase is structure cleanup after owner convergence. It does not reopen stage, lifecycle, settings, routing, or backend-direction decisions.

## Problem

Phases 1-4 converged core owners, but two control-plane entry files still carry too much mixed responsibility.

1. `src/fitcv_cp/app.py` is still monolithic after SSOT cleanup.
   - it owns FastAPI assembly, route declarations, run-detail shaping, artifact download helpers, review-queue shaping, CV review actions, synonym review actions, and persistence-adjacent orchestration in one file
   - ownership is now clearer than before, but future changes still tend to patch nearest giant file instead of stable helper seam

2. `src/fitcv_cp/worker_job.py` still mixes distinct workflow layers.
   - public worker entrypoints, run-attempt lifecycle bookkeeping, checkpoint snapshot persistence, synonym automation, and regenerate-once flow still live in one module
   - the file already has stable helper clusters that can move without changing public worker contract

3. `src/fitcv_cp/sqlite_store.py` still contains optional cleanup residue.
   - repeated JSON-field update shapes and compatibility-shaped leaf signatures remain
   - not all of this must move, but extraction work should not leave duplicated storage helpers in place if one internal helper can delete the overlap

4. Master-spec Phase 5 wording was broad enough to invite drift.
   - bounded control-plane monolith reduction must not turn into repo-wide file-splitting or a late `pipeline.py` rewrite
   - current workstream and source hotspots support a narrower control-plane-only phase, which is safer and consistent with earlier non-goals

## Triage

Layer: change
Feature type: REPLACE
Summary: replace oversized control-plane entry-file structure with bounded helper extraction now that canonical owners are stable, and normalize only the storage helper residue touched by that extraction
Reasoning: ownership drift is largely fixed, so next safe step is structural reduction around current control-plane hotspots instead of new semantic refactors
Invariants:
  - canonical owners from Phases 1-4 remain authoritative
  - FastAPI routes, worker entrypoints, and SQLite truth stay behaviorally stable
  - storage normalization remains subordinate to monolith reduction, not a second semantic lane
Dependencies:
  - docs/superpowers/specs/2026-07-12-09-34-fitcv-ssot-symmetry-phase-1-legacy-surface-and-backend-trim-spec.md
  - docs/superpowers/specs/2026-07-12-13-10-fitcv-ssot-symmetry-phase-2-stage-lifecycle-late-stage-consolidation-spec.md
  - docs/superpowers/specs/2026-07-12-18-35-fitcv-ssot-symmetry-phase-3-settings-schema-native-form-boundary-spec.md
  - docs/superpowers/specs/2026-07-12-20-20-fitcv-ssot-symmetry-phase-4-routing-runtime-envelope-persistence-truth-spec.md
Affected stages:
  - cv_analysis
  - cv_generation
Affected features:
  - inspection_debugging
  - trigger_run_management
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
    - docs/architecture.md
    - docs/api.md
    - docs/observability.md
  readme: none
  generated: none
Generated refresh required: no
Capability IDs:
  - inspection_debugging.prompt-provenance-diagnostics
  - inspection_debugging.settings-used-export
  - trigger_run_management.job-input-modes
  - trigger_run_management.run-owned-artifact-exports
Invariant IDs:
  - none
Spec needed: yes
Plan needed: yes

## Key Deliverables

### Deliverable 1: bounded extraction map is explicit and reuse-first

Phase 5 must name exact extract-now seams, keep-inline seams, and defer seams so implementation does not slide into file-size-aesthetics cleanup.

### Deliverable 2: `app.py` becomes assembly-first instead of helper-first

`src/fitcv_cp/app.py` must keep `create_app(...)`, route registration, and direct HTTP boundary ownership, while bounded pure/helper clusters move out to focused support modules.

Default extraction owner for this lane:

- `src/fitcv_cp/app_run_support.py`
  - owns run-detail shaping helpers
  - owns artifact download/read-model helpers
  - owns review-queue/read-model helpers
  - may own route-adjacent action helpers only when they are pure/helper-level and not direct FastAPI boundary code

### Deliverable 3: `worker_job.py` becomes entrypoint-first instead of snapshot-first

`src/fitcv_cp/worker_job.py` must keep public worker entrypoints, while checkpoint/snapshot/synonym helper families move behind them into one bounded support surface.

Default extraction owner for this lane:

- `src/fitcv_cp/worker_run_support.py`
  - owns checkpoint snapshot persistence helpers
  - owns synonym snapshot/automation helpers
  - owns late-stage diagnostic support payload helpers
  - does not become a second public worker-entrypoint surface

### Deliverable 4: storage normalization stays optional and support-only

Any `sqlite_store.py` or adjacent storage cleanup in this lane must only delete duplication or compatibility residue exposed by extraction work. It must not redesign persistence contracts, schema, or backend direction.

### Deliverable 5: Phase 5 boundary stays tight

This lane must stay control-plane-only and must not expand into repo-wide monolith splitting, `pipeline.py` restructuring, or a new architecture layer.

## Task/Wave Breakdown

### Wave 1: Source-first extraction inventory

**Purpose:**
- identify exact control-plane hotspots and safest stable seams before any structural change

**Steps:**
- [ ] enumerate current `app.py` helper families and route clusters as `extract-now`, `keep-inline`, or `defer`
- [ ] enumerate current `worker_job.py` helper families and public entrypoints with same classification
- [ ] identify any duplicated storage helper patterns touched directly by those extract-now seams
- [ ] freeze route-path, payload-key, event-stage, artifact-filename, and worker-entrypoint contracts that must not drift during extraction

**Verification:**
- [ ] extraction candidates are justified by responsibility boundaries, not only by file size

**Exit Criteria:**
- no Phase 5 implementation task depends on vague “split the big file” wording

### Wave 2: bounded `app.py` reduction

**Purpose:**
- reduce `app.py` only around stable helper families while keeping FastAPI assembly boring

**Steps:**
- [ ] extract run-detail/read-model and artifact-download helper families from `app.py` into `src/fitcv_cp/app_run_support.py`
- [ ] extract CV review and synonym review orchestration helpers into `src/fitcv_cp/app_run_support.py` only when they are not route-boundary-specific
- [ ] keep `create_app(...)` as the HTTP assembly owner; route decorators stay in `app.py` unless the implementation plan proves a smaller native FastAPI registration shape
- [ ] reuse existing owners such as `settings_schema.py`, `synonym_proposals.py`, `pipeline_contracts.py`, `runtime_contracts.py`, and `run_artifact_mirror.py` instead of creating a new service layer

**Verification:**
- [ ] app tests prove same redirects, response payloads, artifact downloads, and action effects after extraction

**Exit Criteria:**
- `app.py` is materially narrower, and remaining code is mostly assembly, route boundaries, and direct dependency wiring

### Wave 3: bounded `worker_job.py` reduction and optional storage normalization

**Purpose:**
- reduce `worker_job.py` and clean touched storage residue without reopening persistence semantics

**Steps:**
- [ ] extract checkpoint/snapshot/synonym-automation helper families from `worker_job.py` into `src/fitcv_cp/worker_run_support.py`
- [ ] keep `execute_pipeline_run(...)` and `execute_cv_regenerate_once(...)` as public entrypoints in `worker_job.py`
- [ ] if extraction touches duplicated `sqlite_store.py` field-update patterns, collapse them to one internal helper rather than copying another variant
- [ ] remove leftover low-level compatibility-shaped leaf signatures only where all direct callers are local and updated in same patch
- [ ] leave storage schema, persisted JSON contract, and `RunStore` / `ControlPlaneStore` behavioral boundary unchanged

**Verification:**
- [ ] worker, sqlite-store, and store tests prove unchanged behavior and no new parallel persistence owner

**Exit Criteria:**
- `worker_job.py` is entrypoint-first, storage cleanup stays support-only, and no new semantic refactor piggybacks on the lane

## Design Decisions

### Decision: extract pure helper families before moving route decorators

- context: `app.py` is large, but the riskiest churn would be broad FastAPI/router migration rather than helper extraction
- choice: keep `create_app(...)` and route decorators in `app.py` by default, and extract pure/helper families first into `src/fitcv_cp/app_run_support.py`
- alternatives considered:
  - full `APIRouter` breakup of route surfaces
  - leave all helpers inline and accept file sprawl
- impact:
  - lowest framework churn
  - smaller review diff with same behavior contract

### Decision: at most one focused app support module and one focused worker support module in this lane

- context: monolith reduction can create new sprawl if every helper family gets its own file
- choice: keep extraction bounded to one focused app support surface and one focused worker support surface unless source inventory proves a third file is clearly smaller and safer overall
- alternatives considered:
  - many micro-modules
  - no extraction until a full architecture rewrite
- impact:
  - fewer files
  - clearer plan boundaries

### Decision: storage normalization is subordinate, not co-equal

- context: master spec marks storage normalization optional, and Phase 4 already landed the semantic persistence cleanup
- choice: normalize only the storage helper residue directly touched by Phase 5 extraction or clearly blocking testability
- alternatives considered:
  - separate broad storage refactor in same lane
  - forbid any storage cleanup at all
- impact:
  - no reopened persistence-design debate
  - extraction can still delete duplicated leaf code when it is already in hand

### Decision: `pipeline.py` and repo-wide monolith work stay out of scope

- context: master-spec wording could be read too broadly, but current workstream and hotspot evidence are control-plane-specific
- choice: Phase 5 is control-plane-only; `src/fitcv/pipeline.py` and other non-control-plane large files are explicit non-goals here
- alternatives considered:
  - repo-wide monolith reduction sweep
  - include `pipeline.py` because it is large
- impact:
  - safer bounded lane
  - less chance of mixing structural cleanup with unrelated semantics

## Invariants

- canonical owners from Phases 1-4 remain authoritative; Phase 5 moves code location, not semantic ownership
- `create_app(...)`, `execute_pipeline_run(...)`, `execute_cv_regenerate_once(...)`, `RunStore`, and `ControlPlaneStore` remain stable public entrypoints/boundaries
- route paths, query parameters, form fields, payload keys, event stage names, and artifact filenames stay stable unless a doc-backed contract change is explicitly approved
- SQLite remains sole supported control-plane backend
- Phase 5 adds no new service layer, dependency-injection tree, or parallel metadata registry
- extracted helpers must be pure or boundary-local; no hidden global state or fallback cache may be introduced
- optional storage normalization must not change database schema or persisted JSON contract

## Acceptance Criteria

1. A concrete extraction map exists that classifies current `app.py` and `worker_job.py` families as `extract-now`, `keep-inline`, or `defer`.
2. `src/fitcv_cp/app.py` no longer owns the extracted run-detail/download and review helper families inline.
3. `src/fitcv_cp/worker_job.py` no longer owns the extracted checkpoint/snapshot/synonym helper families inline.
4. `create_app(...)`, route URLs, response/redirect behavior, artifact download endpoints, and worker public entrypoints remain behaviorally unchanged.
5. A native FastAPI route-manifest check proves the post-extraction app preserves `(path, methods, name)` for every admin route.
6. Any storage normalization landed in this lane is internal/support-only and does not reopen backend semantics, schema, or persisted payload contracts.
7. No new broad architecture layer, service tree, or repo-wide file-splitting campaign is introduced.
8. Phase 5 scope is explicit enough that a later implementation plan can name exact files and verification commands without redefining architecture.

## Non-Goals

- no repo-wide monolith reduction sweep
- no `src/fitcv/pipeline.py` split in this lane
- no new `APIRouter` package tree unless extraction inventory proves it is smaller and safer than keeping decorators in `app.py`
- no new domain/application/infrastructure layer stack
- no storage schema migration, backend reintroduction, or persistence-contract redesign
- no reopening of stage, lifecycle, settings, routing, or late-stage owner decisions from Phases 1-4

## Risks and Mitigations

- risk: structural cleanup quietly changes HTTP behavior
  - mitigation: keep route decorators and boundary tests intact; move pure helpers first
- risk: extraction creates too many tiny files and new navigation cost
  - mitigation: cap this lane to one focused app support module and one focused worker support module by default
- risk: storage cleanup expands into a second persistence refactor
  - mitigation: allow only support-only normalization that deletion or extraction already requires
- risk: future edits start patching new helper files plus old entry files inconsistently
  - mitigation: keep entrypoint ownership explicit in spec and implementation plan, with route/worker boundaries named up front

## Validation Plan

- proof target: Phase 5 remains control-plane-only and structurally bounded
  - method: inspection
  - evidence: approved Phase 5 spec plus implementation plan that names only control-plane targets and excludes `src/fitcv/pipeline.py`

- proof target: `app.py` helper extraction preserves HTTP behavior
  - method: test
  - evidence: `tests/test_fitcv_cp/test_app.py` passes with unchanged route/redirect/download assertions

- proof target: FastAPI native route contract is unchanged
  - method: test
  - evidence: `tests/test_fitcv_cp/test_app.py` includes one route-manifest assertion over `create_app().routes` covering `(path, methods, name)` for admin routes

- proof target: `worker_job.py` helper extraction preserves worker behavior
  - method: test
  - evidence: `tests/test_fitcv_cp/test_worker_job.py` and related worker suites pass with unchanged entrypoint behavior

- proof target: optional storage normalization does not change store semantics
  - method: test + inspection
  - evidence: `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_store.py`, and review of unchanged schema/persisted payload contracts

- proof target: Phase 5 does not reintroduce parallel owners or architecture sprawl
  - method: inspection + repo search
  - evidence: extracted helper modules reuse existing owners and no new service-layer tree or repo-wide split appears

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
