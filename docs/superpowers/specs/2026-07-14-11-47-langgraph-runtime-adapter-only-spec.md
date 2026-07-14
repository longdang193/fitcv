---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: langgraph-runtime-adapter-only-late-stage-cv-generation
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - src/fitcv/runtime_routing.py
  - src/fitcv/cv_generator.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_run_support.py
  - config/runtime/control_plane.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/configuration.md
  - docs/pipeline.md
  - tests/test_cv_generator.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - cv_system
  - settings_system
  - trigger_run_management
  - inspection_debugging
related_stages:
  - cv_analysis
  - cv_generation
---

# Detailed Spec: LangGraph as runtime adapter only for late-stage CV generation

## Goal

Define concrete SSOT and symmetry contract for late-stage CV generation so the
repo keeps one semantic generation method and one stage-owned meaning model,
while LangGraph remains only runtime adapter/orchestrator for provider calls,
tracing, repair-loop execution, and optional tool-driven runtime behavior.

This spec collapses the current split between built-in and LangGraph late-stage
semantic methods into one canonical contract:

`cv_analysis record -> write request -> writer adapter -> validation -> repair -> render -> persist`

The spec is bounded to `cv_generation` runtime ownership. It does not redesign
`cv_analysis`, ranking policy, or unrelated control-plane lifecycle surfaces.

## Key Deliverables

### Deliverable 1: one late-stage semantic contract

The repo defines one canonical late-stage CV-generation state machine and one
set of stage-owned meanings for admissible cases including fresh run, replay,
stage-by-stage resume, validation retry, and review-required outcomes.

### Deliverable 2: one routing and adapter boundary

`src/fitcv/runtime_routing.py` and `config/runtime/control_plane.yaml` remain
sole owners of provider/model/base_url/wire_api resolution, while LangGraph is
reduced to one adapter implementation behind that routed contract.

### Deliverable 3: one artifact and provenance shape

Both built-in and LangGraph-backed execution produce the same externally visible
status vocabulary, trace summary shape, validation shape, repair shape, and
artifact bundle shape. Provider differences stay internal to adapter runtime
metadata only.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- freeze current owner surfaces and exact symmetry violations before choosing
  collapse shape

**Steps:**
- [ ] confirm current stage contract and feature contract for `cv_generation`
- [ ] inventory current dual-path ownership in `pipeline.py`, `cv_generator.py`,
      and `agentic_cv_generation.py`
- [ ] inventory all places where `agentic` vs `non_agentic` still affects
      semantic behavior instead of pure runtime execution details
- [ ] inventory all externally visible payloads that mention late-stage mode,
      runtime provenance, validation, repair, or generated artifact status

**Verification:**
- [ ] current split is explicit enough to remove without hidden semantic owners

**Exit Criteria:**
- no collapse decision depends on guessed current behavior

### Wave 2: Decision closure

**Purpose:**
- resolve final owner split and reject unnecessary second-method semantics

**Steps:**
- [ ] define canonical late-stage request/result contract
- [ ] define adapter boundary and allowed LangGraph responsibilities
- [ ] define forbidden duplicate meaning ownership outside canonical contract
- [ ] define transition semantics for existing built-in path and existing
      LangGraph path

**Verification:**
- [ ] each ownership question has one explicit owner and one explicit non-owner

**Exit Criteria:**
- design is coherent, bounded, and symmetry-first

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof of SSOT and symmetry executable before implementation planning

**Steps:**
- [ ] define grep/test evidence for removal of semantic branch split
- [ ] define parity evidence for built-in and LangGraph adapter outputs during
      transition window
- [ ] define final removal gate for second semantic method
- [ ] define docs/settings evidence for one runtime-authoritative explanation

**Verification:**
- [ ] validation plan can reject any implementation that keeps two meaning
      owners alive

**Exit Criteria:**
- spec is ready for implementation planning

## Design Decisions

### Decision: one semantic generation method, many runtime adapters

- context: `pipeline.py` still holds `_run_non_agentic_cv_generation(...)` and
  `_run_agentic_cv_generation(...)`, which keeps two semantic methods alive even
  though routing SSOT and mode truth already trend unified.
- choice: keep one semantic generation method for `cv_generation`; runtime may
  select among adapter implementations, but adapter selection must not alter
  stage meaning, request shape, validation rules, repair semantics, or artifact
  semantics.
- alternatives considered:
  - keep both methods and declare them equivalent
  - hard-delete built-in path immediately and make LangGraph own all semantics
- impact:
  - `pipeline.py` stops owning decision-critical branch meaning
  - tests move from path-parity framing to owner-contract framing
  - future document products can reuse one contract with different adapters

### Decision: LangGraph is runtime adapter/orchestrator, not meaning owner

- context: `agentic_cv_generation.py` currently mixes adapter work with part of
  late-stage semantic ownership, including provider loading, request shaping,
  validation-repair orchestration, and status/result assembly.
- choice: LangGraph may own runtime orchestration mechanics only:
  provider client setup, node sequencing, trace capture, tool invocation,
  bounded retry execution, and adapter-local telemetry.
- alternatives considered:
  - let LangGraph own full late-stage semantics
  - remove LangGraph entirely
- impact:
  - LangGraph stays easy to extend without becoming second source of truth
  - stage meaning remains owned in repo-native contract surfaces
  - future non-LangGraph adapter can reuse same contract safely

### Decision: built-in writer contract remains canonical request/result shape

- context: `cv_generator.py` already exposes repo-native structured generation
  prompt building, normalization, and markdown rendering, while
  `runtime_routing.py` already owns routed provider resolution.
- choice: canonical request/result contract stays repo-native and stable even if
  implementation later delegates all provider execution to LangGraph.
- alternatives considered:
  - rebase all request/result shapes around LangGraph-specific node payloads
- impact:
  - docs, tests, and stage contracts depend on repo contract, not graph internals
  - LangGraph can be swapped or extended without breaking external semantics

### Decision: stage mode becomes observational only, never semantic owner

- context: control-plane payloads still expose `late_stage_mode` and
  `agentic_late_stage_enabled`; some code already hard-flips these toward
  unified runtime while older semantics still exist in tests and branch names.
- choice: late-stage mode may remain as backward-compatible observational
  metadata during transition, but it must never select different late-stage
  semantic behavior.
- alternatives considered:
  - preserve mode toggle as supported semantic branch selector
  - delete all mode payloads in same patch
- impact:
  - UI can keep stable fields temporarily
  - runtime branch collapse can happen before payload cleanup
  - future cleanup can remove stale labels once consumers are migrated

### Decision: provider routing stays single-owner in runtime routing plus config

- context: routed provider/model/base_url/wire_api already resolve through
  `runtime_routing.py` and `config/runtime/control_plane.yaml`, while
  LangGraph-specific env values still exist as compatibility overrides.
- choice: keep `runtime_routing.py` plus `config/runtime/control_plane.yaml` as
  sole routing owners; LangGraph consumes resolved routing, not independent
  routing truth.
- alternatives considered:
  - let LangGraph env become primary routing source
  - duplicate routing config inside graph package
- impact:
  - one routing truth across built-in and LangGraph-backed execution
  - provider swaps remain stage-symmetric
  - drift checks stay meaningful and bounded

## Invariants

- `cv_generation` owns one semantic state machine for all admissible cases.
- `cv_analysis` remains sole owner of evidence retrieval, gap analysis, and fit
  gate meaning.
- LangGraph never becomes source of truth for stage semantics, status meaning,
  validation rules, repair rules, or artifact schema.
- `runtime_routing.py` and `config/runtime/control_plane.yaml` remain sole
  owners of runtime provider/model/base_url/wire_api resolution.
- Externally visible late-stage outputs use one canonical status vocabulary.
- Externally visible validation payloads use one canonical field set.
- Externally visible repair payloads use one canonical field set.
- Externally visible runtime provenance may vary by provider, but not by stage
  meaning.
- Resume, replay, and review-required flows reuse same semantic contract as
  fresh runs.
- Adapter-local trace richness may differ, but absence or presence of trace data
  must not change acceptance semantics.

## Acceptance Criteria

- `pipeline.py` no longer owns separate semantic methods for non-agentic and
  agentic late-stage generation.
- LangGraph-backed execution consumes canonical repo-native write request and
  returns canonical repo-native result payload.
- Built-in and LangGraph-backed transition execution produce identical external
  statuses, validation payload keys, repair payload keys, and artifact keys for
  same deterministic fixtures.
- `late_stage_mode` and related payloads, if retained, do not affect semantic
  branching.
- `cv_generation` docs explain one stage contract and one runtime routing owner.
- Tests can fail if any new branch reintroduces separate semantic ownership by
  mode or by adapter family.

## Non-Goals

- redesigning `cv_analysis` evidence selection or fit-gate policy
- changing business acceptance thresholds or validation math
- deleting LangGraph tracing/tooling value
- redesigning provider catalogs or unrelated AI-stage routing outside bounded
  late-stage CV generation needs
- rewriting all control-plane observability payloads in same spec

## Risks and Mitigations

- Risk: hidden tests or UI surfaces still assume `agentic` vs `non_agentic`
  semantic differences.
  - mitigation: retain observational payload compatibility during transition,
    but add tests that semantic outputs are adapter-invariant.
- Risk: LangGraph runtime currently owns useful retry/trace behavior that could
  get lost in collapse.
  - mitigation: keep runtime orchestration allowance explicit at adapter layer
    and test trace-preservation separately from stage meaning.
- Risk: built-in and LangGraph request/response shapes differ in edge cases.
  - mitigation: define one canonical request/result contract first; adapters
    must normalize at boundary.
- Risk: provider/env override drift leaks second routing owner back in.
  - mitigation: preserve routed snapshot and drift validation as explicit proof
    target.

## Validation Plan

- proof target: semantic branch split is removed from late-stage pipeline owner
  - method: inspection plus targeted grep over `src/fitcv/pipeline.py`
  - evidence: no decision-critical branch between separate non-agentic and
    agentic generation methods remains

- proof target: LangGraph is adapter-only, not second meaning owner
  - method: inspection of `src/fitcv/agentic_cv_generation.py` and related
    contract imports
  - evidence: status meaning, validation meaning, and repair meaning import from
    canonical repo owners instead of being redefined locally

- proof target: routing remains SSOT-owned outside LangGraph
  - method: inspection plus unit tests around runtime routing snapshot and drift
  - evidence: routed provider/model/base_url/wire_api resolve from
    `src/fitcv/runtime_routing.py` and `config/runtime/control_plane.yaml`, with
    LangGraph consuming resolved values only

- proof target: external late-stage outputs are adapter-invariant
  - method: deterministic fixture comparison tests across built-in transition
    adapter and LangGraph adapter
  - evidence: equal status, validation keys, repair keys, markdown presence, and
    artifact-bundle keys after normalizing allowed provider-only provenance
    fields

- proof target: observational mode payload is no longer semantic owner
  - method: control-plane payload tests and pipeline tests
  - evidence: toggled or retained `late_stage_mode` fields do not change late-stage
    semantic outcomes for identical deterministic inputs

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\docs\operating_system\governance\repo-governance.md`
- `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\scripts\validate_planning_lifecycle.py`
</LINK>
