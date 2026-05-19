---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: runtime-throughput-ssot-symmetry-invariance-optimization-spec
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract

targets:
  - src/fitcv/pipeline.py
  - src/fitcv/ai_score.py
  - src/fitcv/enrich.py
  - src/fitcv_cp/templates/admin_pipeline_settings.html
  - src/fitcv_cp/static/js/admin_pipeline_settings.js
  - src/fitcv/config.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_ai_score.py
  - docs/configuration.md
related_features:
  - settings_system
  - inspection_debugging
  - pipeline_performance
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Define one canonical, symmetric, and invariant runtime-throughput design across `enrich`, `ranking`, `cv_analysis`, and `cv_generation` so stage concurrency behavior, configuration ownership, and observability contracts are consistent and operator-facing UX has one editable source of truth.

## Key Deliverables

### Deliverable 1: Canonical throughput contract

A single stage-scoped runtime contract defines throughput knobs (`concurrency`, `batch_size`, `sleep_secs`, optional stage timeout/retry knobs) with canonical ownership in runtime config and compatibility projection as read-only bridge only.

### Deliverable 2: Symmetric stage execution model

Equivalent late-stage work units use equivalent bounded-parallel execution structure, including deterministic output ordering and per-unit failure isolation.

### Deliverable 3: Invariant observability + status semantics

Stage decision/status/event payload semantics are normalized so equivalent outcomes use equivalent status keys and equivalent telemetry shape.

### Deliverable 4: SSOT settings UX

Control-plane settings expose one canonical editable surface (`Runtime Throughput`), while legacy aliases move to read-only compatibility mapping and migration status.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current behavior, drift edges, and boundary constraints before design closure

**Steps:**
- [x] confirm stage execution behavior in source (`pipeline.py`, `ai_score.py`, `enrich.py`)
- [x] confirm current config compatibility bridges and canonical runtime config intent
- [x] confirm control-plane duplication concern (canonical vs legacy surfaces)
- [x] record GitNexus freshness state and constrain to advisory-only conclusions

**Verification:**
- [x] current state captures where execution is truly parallel vs only configured/telemetry-labelled

**Exit Criteria:**
- no optimization decision depends on unstated current-state assumptions

### Wave 2: Decision closure

**Purpose:**
- resolve architecture for SSOT/symmetry/invariance optimization

**Steps:**
- [x] define canonical throughput contract by stage
- [x] define shared bounded-parallel runner design for equivalent stage units
- [x] define status/event invariance rules across affected stages
- [x] define compatibility-surface rules for UX and config migration

**Verification:**
- [x] each non-obvious design choice records alternatives and rationale

**Exit Criteria:**
- design internally coherent and implementation-bounded

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof and handoff expectations explicit before plan drafting

**Steps:**
- [x] define acceptance criteria and measurable validation evidence
- [x] define risk/mitigation set for provider-rate, ordering, and migration drift
- [x] define explicit non-goals to prevent scope bleed into unrelated lane work

**Verification:**
- [x] validation plan can prove both correctness and invariance preservation

**Exit Criteria:**
- spec ready for implementation planning

## Design Decisions

### Decision: Canonical throughput contract is `stage_runtime` first-class

- context: runtime knobs still partially read from legacy keys (`rerank_sleep_secs`, legacy compatibility projections), creating SSOT ambiguity.
- choice: treat `stage_runtime.<stage>` as canonical runtime-throughput owner for all affected stages.
- alternatives considered:
  - keep dual-write mutable legacy + canonical surfaces
  - migrate by stage-specific ad hoc rules
- impact:
  - runtime reads become uniform by stage
  - compatibility projection remains read-only bridge until retirement
  - docs and settings UI point to one editable source

### Decision: Shared bounded-parallel execution contract for equivalent units

- context: `cv_analysis` has executor-based concurrency while `cv_generation` and `ranking` remain sequential bottlenecks.
- choice: define reusable bounded-parallel unit executor contract, applied to `ranking` and `cv_generation` (and aligned with `cv_analysis` behavior).
- alternatives considered:
  - leave each stage bespoke
  - fully async end-to-end refactor now
- impact:
  - symmetry across equivalent unit-of-work lanes
  - simpler reasoning for retries, ordering, and telemetry
  - lower regression risk than full async rewrite

### Decision: Deterministic ordering preserved under parallelism

- context: parallel execution can reorder completion and destabilize outputs/artifacts.
- choice: parallel execution allowed, but publish/store/debug order must be stable by canonical input index.
- alternatives considered:
  - completion-order output
  - stage-specific ordering exceptions
- impact:
  - reproducible artifacts
  - stable downstream expectations/tests
  - easier run diff/review

### Decision: Unified event and status semantics across late stages

- context: similar outcomes currently emitted through partly divergent payload/status shapes.
- choice: enforce canonical status vocabulary and payload core fields for equivalent event families.
- alternatives considered:
  - keep stage-local payload dialects
- impact:
  - simpler observability consumers
  - lower contract drift risk
  - cleaner cross-stage diagnostics

### Decision: One editable settings surface, compatibility read-only

- context: duplicate UX controls violate SSOT and cause operator confusion.
- choice: keep only canonical runtime-throughput editor; legacy compatibility section becomes collapsed read-only alias mapping + migration/status indicators.
- alternatives considered:
  - preserve both editable surfaces with sync logic
- impact:
  - no split-brain configuration edits
  - explicit migration posture

## Invariants

- Canonical runtime-throughput edits happen in one place only.
- Compatibility/legacy aliases are non-authoritative and read-only in operator UX.
- Equivalent stage concepts (`concurrency`, per-unit timeout/retry semantics, status lifecycle) use equivalent structure and naming.
- Parallel execution must preserve deterministic output order by canonical index.
- Per-unit failure isolation remains; one unit failure does not collapse whole stage unless explicit stage guard criterion fails.
- Observability payload minimum fields for started/result events remain invariant across affected stages:
  - `configured_concurrency`
  - `worker_slot`
  - `started_at`
  - `finished_at`
  - `attempt_count`
  - `retry_count`
- Source-of-truth boundaries remain explicit: runtime code reads canonical config; docs and UI do not introduce parallel writable truth.

## Acceptance Criteria

- `ranking`, `cv_analysis`, and `cv_generation` all implement bounded concurrency using a consistent execution contract shape.
- `cv_generation` and `ranking` no longer use purely sequential item loop for configured parallel mode.
- Deterministic ordering is preserved and covered by tests for parallel paths.
- Settings UI exposes one canonical editable throughput surface; compatibility panel is read-only and collapsed by default.
- Runtime config reads for affected throughput knobs are canonicalized to `stage_runtime` paths; legacy reads (if retained) are compatibility-only and explicitly tagged.
- Event/status schema checks pass for equivalent outcomes across affected stages.

## Non-Goals

- No full rewrite to asyncio/event-loop runtime.
- No redesign of enrichment model prompts or ranking rubric logic.
- No change to domain decision policies (fit thresholds, acceptance policy semantics) beyond contract normalization needed for invariance.
- No repo-wide settings IA redesign outside scoped runtime-throughput + compatibility surfaces.
- No public-repo publication workflow changes.

## Risks and Mitigations

- Risk: provider/API rate pressure increases under new parallel paths.
  - mitigation: bounded concurrency caps, conservative defaults, retry/backoff policy, canary rollouts.
- Risk: hidden ordering dependencies break downstream artifacts.
  - mitigation: explicit index-based ordering contract + regression tests.
- Risk: compatibility drift between canonical and legacy aliases during migration window.
  - mitigation: read-only compatibility mapping + migration status diagnostics + deprecation warnings.
- Risk: observability consumer breakage due to payload contract changes.
  - mitigation: additive-first payload transition, schema tests, staged removal of legacy fields.
- Risk: stale architecture assumptions from GitNexus.
  - mitigation: advisory-only GitNexus usage when stale; source/test truth precedence.

## Validation Plan

- proof target: canonical stage-throughput SSOT enforced
  - method: config-loading and settings-surface inspection tests
  - evidence: updated tests in `tests/test_config.py` + settings template/js assertions + docs alignment

- proof target: bounded parallelism active in `ranking` and `cv_generation`
  - method: unit/integration tests with controlled delays and overlap assertions
  - evidence: `tests/test_ai_score.py`, `tests/test_pipeline.py`, `tests/test_pipeline_agentic_late_stage.py` showing overlapping execution and configured worker caps

- proof target: deterministic order invariant under parallel completion
  - method: concurrency tests with out-of-order completion simulation
  - evidence: stable output sequence assertions by canonical rank/input index

- proof target: event/status invariance across affected stages
  - method: event payload schema assertions and table-driven status transition tests
  - evidence: reporter-event assertions containing invariant payload fields and canonical status vocabulary

- proof target: compatibility surface is read-only and collapsed
  - method: UI render + interaction checks
  - evidence: template/js tests or functional checks proving no editable legacy knobs and default collapsed state

- proof target: no regression in existing late-stage behavior contracts
  - method: targeted pytest subset + existing stage artifact checks
  - evidence: pass logs for current pipeline late-stage and artifact contract tests

## Completion Criteria

1. all Key Deliverables are satisfied
2. downstream implementation plan exists and references this spec as source design
3. validation evidence is attached for each proof target
4. remaining legacy compatibility items (if any) are explicitly tracked with terminal disposition (`retained-temporary`, `removed`, or `superseded`)

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
