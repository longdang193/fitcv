---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-ssot-symmetry-phase-2-stage-lifecycle-late-stage-consolidation
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md
  - docs/superpowers/specs/2026-07-12-09-34-fitcv-ssot-symmetry-phase-1-legacy-surface-and-backend-trim-spec.md
  - docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md
  - docs/superpowers/specs/2026-04-23-02-05-run-lifecycle-stage-participation-spec.md
  - src/fitcv/pipeline_contracts.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/run_lifecycle.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/reconciler_service.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/templates/run_detail.html
  - docs/architecture.md
  - docs/api.md
  - docs/pipeline.md
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_pipeline_status_registry.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_queue.py
  - tests/test_fitcv_cp/test_reconciler.py
  - tests/test_fitcv_cp/test_run_lifecycle.py
related_features: []
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Detailed Spec: FitCV SSOT / symmetry Phase 2 stage, lifecycle, and late-stage consolidation

## Goal

Execute second concrete remediation lane from
`docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`:

- move runtime stage truth onto one owner in `src/fitcv/pipeline_contracts.py`
- move run lifecycle capability and transition truth onto one callable helper
- make `src/fitcv/late_stage_contract.py` sole owner for late-stage status
  literals and interpretation

This phase is owner-convergence first. It deletes duplicated literals, maps,
and parity wrappers. It does not yet finish settings-schema convergence,
routing cleanup, or remaining Phase 1 backend-compat shim retirement.

## Problem

Current repo still has three live Phase 2 drift classes:

1. stage-equivalent runtime facts have multiple active owners:
   - `src/fitcv/pipeline.py` owns `PIPELINE_STAGE_SEQUENCE`
   - `src/fitcv_cp/app.py` also owns `STAGE_SEQUENCE`,
     `TIMELINE_STAGE_LABELS`, `TIMELINE_STAGE_DOWNLOADS`,
     `TIMELINE_STAGE_DOWNLOADABLE_EVENTS`, `STAGE_DOWNLOAD_LABELS`,
     `BUNDLE_STAGE_IDS`, and `BUNDLE_ARTIFACT_FILENAMES`
2. lifecycle capability truth is split between enum values and route-local
   helpers:
   - `RunStatus` lives in `src/fitcv_cp/models.py`
   - raw capability checks and stale-cancelling logic live in
     `src/fitcv_cp/app.py`
   - worker/store/reconciler paths still use scattered status-set checks for
     action eligibility and timeout/cancellation interpretation
3. late-stage outcome meaning already has partial owner in
   `src/fitcv/late_stage_contract.py`, but duplicate constants and helper
   functions still survive in `src/fitcv/pipeline.py` and
   `src/fitcv/agentic_cv_analysis.py` / `src/fitcv/agentic_cv_generation.py`

Until this lane lands, Phase 3 and Phase 4 would build on duplicated semantic
facts instead of stable owners.

## Relationship To Existing Specs

This Phase 2 spec is authoritative only for bounded runtime-contract
consolidation after Phase 1.

- `docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`
  remains parent authority for phase order, final architecture, and cross-phase
  invariants.
- `docs/superpowers/specs/2026-07-12-09-34-fitcv-ssot-symmetry-phase-1-legacy-surface-and-backend-trim-spec.md`
  remains the precondition lane that removed dead surfaces and tightened active
  backend truth. Any temporary Phase 1 boundary shims that remain are not
  reopened here unless Phase 2 touches them directly for stage/lifecycle call
  routing.
- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`
  remains useful semantic background for which stage owns which decision family,
  but this Phase 2 spec is the concrete runtime-owner contract for code.
- `docs/superpowers/specs/2026-04-23-02-05-run-lifecycle-stage-participation-spec.md`
  remains metadata guidance for architecture docs. This Phase 2 spec owns the
  executable lifecycle policy surface.

## Triage

Layer: change
Feature type: REPLACE
Summary: replace duplicate stage maps, route-local status policy, and
late-stage parity wrappers with one runtime stage registry, one lifecycle
policy helper, and one late-stage contract
Reasoning: Phase 2 should stabilize semantic runtime owners before settings or
routing cleanup depends on them
Invariants:
  - executable stage truth has one runtime owner in `src/fitcv/pipeline_contracts.py`
  - executable lifecycle truth has one callable policy surface plus `RunStatus`
  - late-stage literals and interpretation come only from `src/fitcv/late_stage_contract.py`
  - boundary adapters may format labels or payloads, but must not recreate
    stage order, lifecycle rules, or late-stage meaning locally
  - no new service object, registry tree, or abstraction layer is introduced
Dependencies:
  - Phase 1 legacy-surface and backend trim
  - current `RunStatus`, `late_stage_contract.py`, and `pipeline_contracts.py`
    surfaces
Affected stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
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
    - docs/architecture.md
    - docs/api.md
    - docs/pipeline.md
  readme: none
  generated: []
Generated refresh required: yes
Capability IDs:
  - none
Invariant IDs:
  - none
Spec needed: yes
Plan needed: yes

## Key Deliverables

### Deliverable 1: `pipeline_contracts.py` owns runtime stage registry

Phase 2 must expand `src/fitcv/pipeline_contracts.py` into the one runtime
owner for:

- stage ID
- stage order
- stage display label
- timeline event to canonical stage mapping
- stage-download eligibility
- stage artifact filename
- artifact-bundle membership

Implementation shape stays boring:

- one immutable module-level registry
- plain data entries and pure helper functions
- no registry class hierarchy, no plugin loader, no second stage package

`src/fitcv/pipeline.py` and `src/fitcv_cp/app.py` may keep only derived imports
or thin compatibility re-exports during same patch if needed. They must not own
local literal copies.

### Deliverable 2: one callable lifecycle policy surface exists

Phase 2 must add one shared helper module in `src/fitcv_cp/`.

Concrete owner split:

- `src/fitcv_cp/models.py`
  - keeps `RunStatus`
- `src/fitcv_cp/run_lifecycle.py`
  - owns status groups, allowed UI actions, target-status interpretation for
    lifecycle commands, archive/unarchive eligibility, stale-cancelling
    detection, timeout target-status selection, and shared status projection
    helpers

HTTP routes, worker, reconciler, and persistence-facing control-plane code must
call this helper for lifecycle policy instead of restating status-set logic
inline.

Lifecycle policy scope is intentionally narrow. `run_lifecycle.py` owns only:

- action eligibility
- lifecycle command target-status selection
- lifecycle status grouping/projection
- stale-cancelling detection
- timeout target-status interpretation

It does not own unrelated domain gates such as export availability,
stage-artifact presence, synonym workflow policy, or CV review payload rules.

No framework object or policy class. Pure functions only.

### Lifecycle command contract

Phase 2 must make this command contract explicit and executable:

| Command | Allowed source status | Target status / effect | Extra invariant |
|---|---|---|---|
| `cancel` | `queued`, `running`, `awaiting_continue` | `cancelled` for queue-safe immediate cancel; otherwise `cancelling` until worker/store completes terminal transition | audit event/result must stay explicit |
| `continue` | `awaiting_continue` | `queued` | next-stage provenance stays preserved |
| `retry` | `failed`, `queued`, `running` only where current product truth already allows it | `queued` | no new retry semantics invented in Phase 2 |
| `archive` | `succeeded`, `failed`, `cancelled` and not archived | archive marker only | status value unchanged |
| `unarchive` | archived runs | archive marker cleared | status value unchanged |
| `repair_stale_cancelling` | stale `cancelling` per shared helper | `cancelled` | only for stale-not-started or shared-helper-admissible cases |

If live code reveals one route currently behaves differently, Phase 2 must
either preserve that as explicit current-product contract or narrow the spec
before implementation. It must not silently invent broader lifecycle behavior.

### Deliverable 3: `late_stage_contract.py` becomes sole late-stage owner

Phase 2 must move remaining late-stage status ownership and interpretation to
`src/fitcv/late_stage_contract.py`.

This includes:

- analysis status literals
- generation status literals
- deterministic truth mapping
- validation-status mapping
- analysis-to-generation handoff mapping
- shortlist-origin interpretation already living there

`src/fitcv/pipeline.py`, `src/fitcv/agentic_cv_analysis.py`, and
`src/fitcv/agentic_cv_generation.py` must import these owners rather than
define parity copies.

### Deliverable 4: parity wrappers and parity-only duplication tests are retired

Phase 2 must delete duplicate helper wrappers that exist only to mirror the
shared owners.

Examples in scope:

- `src/fitcv/pipeline.py`
  - `_validation_status_for_cv_status`
  - `_deterministic_truth_fields`
  - `_cv_generation_status_for_analysis_status`
- local constant ownership for late-stage statuses in `pipeline.py` and
  `agentic_cv_generation.py`

Tests must shift from "owner equals duplicate" parity checks toward direct
owner tests plus focused route/worker integration tests.

## Design Decisions

### Decision: runtime stage registry lives in existing `pipeline_contracts.py`

- context: repo already has `pipeline_contracts.py`; `app.py` and `pipeline.py`
  are duplicating stage facts around it
- choice: expand current module instead of creating new `stage_registry.py` or
  package tree
- consequences:
  - shortest SSOT path
  - app boundary can derive labels, filenames, and timeline download affordance
    from one owner
  - stage resume helpers can migrate out of `pipeline.py` only if that reduces
    duplication; otherwise thin imports are acceptable

### Decision: lifecycle helper is new file, not new subsystem

- context: `RunStatus` enum exists but executable policy does not
- choice: add one `src/fitcv_cp/run_lifecycle.py` file with pure functions and
  import it where needed
- consequences:
  - keeps `models.py` simple
  - removes route-local policy drift without introducing service objects
  - creates one obvious owner for UI/action symmetry tests

### Decision: late-stage contract expands, pipeline copies die

- context: `late_stage_contract.py` already owns part of the meaning
- choice: move remaining literal ownership there and delete duplicate helpers
- consequences:
  - parity tests stop guarding duplicated implementations
  - pipeline, analysis, and generation code import one status family

### Decision: boundary formatting stays at boundary, meaning stays in contract

- context: run-detail pages and artifact downloads need labels and file names,
  but should not own semantic stage logic
- choice: app/template code may format UI strings, but underlying stage ID,
  event alias, downloadability, and artifact-file identity must come from the
  stage registry
- consequences:
  - native templates stay thin
  - no second UI-only stage metadata map survives

## Task/Wave Breakdown

### Wave 1: Source-first owner map

**Purpose:**
- confirm exact duplicate owners and narrow replacement path before planning

**Steps:**
- [x] confirm stage-literal duplication across `pipeline.py` and `app.py`
- [x] confirm lifecycle-policy duplication across `models.py`, `app.py`,
  worker, reconciler, and sqlite store
- [x] confirm late-stage duplicate literals and parity wrappers across
  `late_stage_contract.py`, `pipeline.py`, and generation/analysis modules
- [x] confirm smallest canonical owner set needed for Phase 2

**Verification:**
- [x] every concrete drift named in this spec maps to one existing or newly
  bounded owner

**Exit Criteria:**
- no planned Phase 2 task depends on unknown semantic ownership

### Wave 2: Decision closure

**Purpose:**
- lock runtime-owner boundaries so implementation plan does not reopen design

**Steps:**
- [x] define stage-registry owner and allowed projections
- [x] define lifecycle helper owner split between `RunStatus` and callable
  policy functions
- [x] define late-stage contract expansion and duplicate-wrapper deletion rule
- [x] define explicit out-of-scope boundaries for settings, routing, and Phase 1
  shim retirement

**Verification:**
- [x] each Phase 2 change area has one owner and one boundary rule

**Exit Criteria:**
- implementation plan can stay bounded to stage/lifecycle/late-stage runtime
  consolidation

### Wave 3: Validation and handoff readiness

**Purpose:**
- leave proof targets and commands ready for plan drafting and execution

**Steps:**
- [x] define residue-search checks for stage literals, lifecycle helpers, and
  late-stage duplicates
- [x] define focused pytest set for stage, lifecycle, app, and worker surfaces
- [x] define planning-lineage and validator refresh steps

**Verification:**
- [x] spec includes executable proof commands and completion gates

**Exit Criteria:**
- spec is ready for Phase 2 implementation-plan drafting

## Invariants

- runtime stage order, aliasing, downloadability, and artifact identity derive
  from one executable registry
- run lifecycle capability checks and state projections derive from one
  callable helper plus `RunStatus`
- late-stage status literals and interpretation helpers derive from one shared
  contract
- app/template/UI boundaries may adapt owner data, but may not redefine owner
  semantics locally
- Phase 2 may add one helper module, but may not add a new subsystem,
  framework layer, or abstraction tree

## Concrete Scope

### Stage registry consolidation

Phase 2 implementation must cover these concrete drifts:

- move `PIPELINE_STAGE_SEQUENCE` ownership out of `src/fitcv/pipeline.py`
- remove local stage literals from `src/fitcv_cp/app.py` for:
  - `STAGE_SEQUENCE`
  - `TIMELINE_STAGE_LABELS`
  - `TIMELINE_STAGE_DOWNLOADS`
  - `TIMELINE_STAGE_DOWNLOADABLE_EVENTS`
  - `STAGE_DOWNLOAD_LABELS`
  - `BUNDLE_STAGE_IDS`
  - `BUNDLE_ARTIFACT_FILENAMES`
- route these app helpers through canonical contract helpers:
  - `_timeline_stage_download_for_event(...)`
  - `_timeline_event_allows_stage_download(...)`
  - `_timeline_stage_label(...)`
  - `_build_available_run_artifact_files(...)`
  - `_run_has_stage_artifact(...)`
  - `_run_has_reached_stage(...)`

### Lifecycle-policy consolidation

Phase 2 implementation must cover these concrete drifts:

- remove local ownership in `src/fitcv_cp/app.py` for:
  - `RUN_STATUS_GROUPS`
  - `_run_status_projection(...)`
  - `_can_cancel_run(...)`
  - `_can_archive_run(...)`
  - `_can_unarchive_run(...)`
  - `_is_stale_cancelling(...)`
- route lifecycle-policy checks used by app, worker, reconciler, and sqlite
  store through one helper surface
- keep non-lifecycle `RunStatus` reads local where they are merely domain or
  export guards, not command/transition policy
- keep store/repository writes defensive, but make command eligibility and
  status interpretation derive from same owner

### Late-stage consolidation

Phase 2 implementation must cover these concrete drifts:

- remove remaining status-literal ownership from `src/fitcv/pipeline.py`
  where it duplicates `late_stage_contract.py`
- remove remaining late-stage helper duplication from
  `src/fitcv/agentic_cv_analysis.py`
- remove remaining status-literal ownership from
  `src/fitcv/agentic_cv_generation.py` where it duplicates the contract
- replace pipeline parity helper wrappers with direct imports or delete them
  outright
- keep output payload shape stable unless duplicate meaning forced drift before

## Non-Goals

- no settings-schema expansion in this phase
- no routing or runtime-envelope cleanup in this phase
- no broad `app.py` / `pipeline.py` file split for aesthetics
- no architecture-doc generator migration
- no Phase 1 backend-compat boundary shim retirement unless directly required
  by touched stage/lifecycle call paths
- no recreation of stage registry in docs, templates, or JavaScript

## Risks and Mitigations

- risk: stage registry scope expands into docs/governance migration
  - mitigation: Phase 2 owns runtime executable truth only; docs stay derived or
    explanatory
- risk: lifecycle helper becomes a mini-framework
  - mitigation: pure functions only; no classes, dependency injection layer, or
    registry object
- risk: deleting parity wrappers hides behavior drift
  - mitigation: replace wrapper-parity tests with direct owner tests and route /
    worker integration assertions
- risk: app artifact downloads accidentally change filenames or availability
  - mitigation: keep file names and eligibility behavior stable; only owner path
    changes
- risk: residual Phase 1 boundary shims distract this lane
  - mitigation: touch only shims needed to reroute stage/lifecycle call sites;
    broader shim retirement stays Phase 4 per master spec

## Validation Plan

- proof target: runtime stage registry has one owner
  - method: repo search + focused tests
  - evidence: `pipeline.py` and `app.py` no longer define local stage-sequence,
    stage-download, or artifact-bundle literal owners; stage resume and app
    artifact tests pass

- proof target: lifecycle action and state interpretation are symmetric
  - method: unit test + focused app/worker tests
  - evidence: one lifecycle helper test file covers action eligibility and
    stale-cancelling logic plus command target-status rules; app and worker
    tests assert same behavior without route-local policy copies

- proof target: late-stage meaning has one owner
  - method: repo search + focused tests
  - evidence: duplicate late-stage status helpers/constant owners disappear from
    pipeline and generation modules; direct contract tests and pipeline late-
    stage tests remain green

- proof target: Phase 2 stays bounded
  - method: inspection + repo search
  - evidence: no settings-schema or routing cleanup gets mixed into the patch
    beyond imports forced by touched stage/lifecycle code

### Required commands

```powershell
rg -n "^PIPELINE_STAGE_SEQUENCE =|^STAGE_SEQUENCE:|^TIMELINE_STAGE_LABELS:|^TIMELINE_STAGE_DOWNLOADS:|^TIMELINE_STAGE_DOWNLOADABLE_EVENTS:|^STAGE_DOWNLOAD_LABELS:|^BUNDLE_STAGE_IDS:|^BUNDLE_ARTIFACT_FILENAMES:" src/fitcv/pipeline.py src/fitcv_cp/app.py
rg -n "^RUN_STATUS_GROUPS =|def _run_status_projection|def _can_cancel_run|def _can_archive_run|def _can_unarchive_run|def _is_stale_cancelling" src/fitcv_cp/app.py
rg -n "^CV_ANALYSIS_.*STATUS =|^CV_GENERATION_.*STATUS =|def _validation_status_for_cv_status|def _deterministic_truth_fields|def _cv_generation_status_for_analysis_status" src/fitcv/pipeline.py src/fitcv/agentic_cv_analysis.py src/fitcv/agentic_cv_generation.py
py -3 -m pytest tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_status_registry.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_run_lifecycle.py -q
py -3 scripts/generate_planning_lineage.py
py -3 scripts/hooks/run_validator.py --fast
```

These grep commands prove duplicate owner removal only for the named local
helpers/maps. They are not approval gates against legitimate downstream use of
`RunStatus` enum values or direct imports from canonical owners.

- proof target: planning and docs stay coherent after new spec
  - method: generation + validator run
  - evidence: `py -3 scripts/generate_planning_lineage.py` and
    `py -3 scripts/hooks/run_validator.py --fast` both pass

## Completion Criteria

1. all Key Deliverables are satisfied
2. `pipeline_contracts.py` is executable runtime owner for stage-equivalent
   facts named in this spec
3. `run_lifecycle.py` exists and app/worker/reconciler/store code stop owning
   route-local lifecycle policy copies
4. `late_stage_contract.py` is sole owner for late-stage status literals and
   interpretation helpers
5. Phase 3 can build on stable stage/lifecycle/late-stage owners without
   reopening them

Canonical source-of-truth:

- `docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`
- `src/fitcv/pipeline_contracts.py`
- `src/fitcv/late_stage_contract.py`
- `src/fitcv_cp/models.py`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
