---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: fitcv-llm-runtime-spine-master-symmetry
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - src/fitcv/config.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/openai_compat.py
  - src/fitcv/enrich.py
  - src/fitcv/ai_score.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/cv_generator.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_run_support.py
  - config/runtime/control_plane.yaml
  - docs/configuration.md
  - docs/pipeline.md
  - docs/architecture.md
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/superpowers/specs/2026-07-14-11-47-langgraph-runtime-adapter-only-spec.md
  - tests/test_enrich.py
  - tests/test_ai_score.py
  - tests/test_cv_generator.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_runtime_routing.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - cv_system
  - pipeline_performance
  - settings_system
  - inspection_debugging
  - trigger_run_management
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

# Detailed Spec: FitCV LLM runtime spine master symmetry

## Goal

Define one concrete master architecture for current LLM-backed FitCV work so the
repo uses one SSOT- and symmetry-driven runtime spine across the active routed
LLM surfaces:

- `enrich_extraction`
- `ranking_ai_score`
- `cv_generation_structured_write`

and one stage-owner convergence lane for `cv_analysis`, which is upstream of
CV generation and currently carries duplicated late-stage semantic flow even
though it is not itself a fully active routed LLM surface today.

The target architecture is:

`StageInput -> TaskRequest -> RoutedAdapter -> ParsedResult -> Validator -> Repair/Review -> StageOutput -> ArtifactBundle`

LangGraph is allowed only inside `RoutedAdapter` and optional adapter-local
orchestration. It must not become source of truth for stage semantics, output
schema, validation semantics, retry semantics, or artifact semantics.

This is master-spec scope. It defines final target state, owner surfaces,
ordered remediation lanes, required child detailed specs, and proof gates. It
does not approve big-bang rewrite or implementation planning yet.

## Key Deliverables

### Deliverable 1: one repo-native LLM runtime spine

The repo exposes one boring shared runtime pattern for active LLM surfaces:
request construction, routed provider selection, API-key resolution, response
parse, schema validation, normalized failure taxonomy, provenance, and trace
emission.

### Deliverable 2: one semantic owner per stage

Each stage keeps one repo-native semantic owner:

- `enrich` owns structured job extraction meaning
- `ranking` owns scoring meaning
- `cv_analysis` owns evidence, gap, and fit-gate meaning
- `cv_generation` owns structured write, validation, repair, and artifact meaning

Pipeline and control-plane layers schedule and present. They do not own stage
business logic.

### Deliverable 3: one transition path from dual semantics to adapter-only LangGraph

The repo gets a bounded migration sequence that first collapses duplicated stage
logic, then extracts shared runtime mechanics, then migrates active LLM stages
onto same spine, and finally deletes legacy semantic branch labels and parity
wrappers.

### Deliverable 4: one explicit detailed-spec set for every phase

This master spec must identify the child detailed spec required for each phase
before any implementation plan is authored.

Phase numbering in this section is local to the LLM-runtime-spine remediation
slice. It does not replace the broader July 12 SSOT/symmetry phase numbering.

Required child detailed spec set:

1. **Phase 1 — `cv_analysis` single-owner collapse**
   - required child spec name:
     `fitcv-llm-runtime-spine-phase-1-cv-analysis-single-owner`
   - child spec:
     `docs/superpowers/specs/2026-07-14-12-52-fitcv-llm-runtime-spine-phase-1-cv-analysis-single-owner-spec.md`
   - status: `completed`
   - scope:
     make one canonical `CvAnalysisRecord` owner, delete pipeline and
     stage-runner duplicated analysis semantics, and keep adapter variation
     internal to analyzer boundary only.

2. **Phase 2 — `cv_generation` adapter-only LangGraph boundary**
   - child spec:
     `docs/superpowers/specs/2026-07-14-11-47-langgraph-runtime-adapter-only-spec.md`
   - child spec name:
     `langgraph-runtime-adapter-only-late-stage-cv-generation`
   - status: `completed`
   - scope:
     keep one repo-native late-stage generation contract and demote LangGraph to
     runtime adapter/orchestrator only.

3. **Phase 3 — shared LLM runtime spine extraction**
   - required child spec name:
     `fitcv-llm-runtime-spine-phase-3-shared-runtime-contract`
   - child spec:
     `docs/superpowers/specs/2026-07-14-17-39-fitcv-llm-runtime-spine-phase-3-shared-runtime-contract-spec.md`
   - status: `completed`
   - scope:
     define smallest shared runtime contract for request construction, routed
     adapter call, parse, validation, normalized failure taxonomy, normalized
     provenance, and fake-adapter testing surface.

4. **Phase 4 — `enrich` and `ranking` migration onto shared spine**
   - required child spec name:
     `fitcv-llm-runtime-spine-phase-4-enrich-ranking-migration`
   - child spec:
     `docs/superpowers/specs/2026-07-14-19-22-fitcv-llm-runtime-spine-phase-4-enrich-ranking-migration-spec.md`
   - status: `completed`
   - scope:
     migrate `enrich_extraction` and `ranking_ai_score` onto the shared runtime
     spine without changing stage semantics.

5. **Phase 5 — observability, parity, and legacy-label closeout**
   - required child spec name:
     `fitcv-llm-runtime-spine-phase-5-observability-parity-closeout`
   - child spec:
     `docs/superpowers/specs/2026-07-14-20-40-fitcv-llm-runtime-spine-phase-5-observability-parity-closeout-spec.md`
   - status: `completed`
   - scope:
     converge artifact/provenance/failure-taxonomy surfaces, lock adapter
     parity tests, and delete residual semantic labels such as runtime-mode
     branch framing once no longer needed.

No implementation plan should be authored for any phase until its child
detailed spec exists and is accepted as the bounded design authority for that
phase.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- freeze exact current owners and separate semantic duplication from pure
  transport/orchestration duplication

**Steps:**
- [x] confirm current routed LLM parts in `config/runtime/control_plane.yaml`
- [x] inventory current client-builder, parser, routing, and provenance logic
      across `enrich.py`, `ai_score.py`, `cv_generator.py`, and related helpers
- [x] inventory stage-owned semantic duplication in `pipeline.py` and
      `pipeline_stage_runner.py` for `cv_analysis` and `cv_generation`
- [x] classify each duplication as `stage meaning`, `runtime adapter`,
      `diagnostic projection`, or `legacy compatibility baggage`

**Verification:**
- [x] no remediation lane depends on guessed ownership

**Exit Criteria:**
- current-state split is explicit enough to design ordered collapse

### Wave 2: Decision closure

**Purpose:**
- lock final SSOT owner split and remediation order

**Steps:**
- [x] define one shared LLM runtime spine contract
- [x] define one repo-native semantic owner for each active LLM-adjacent stage
- [x] define LangGraph responsibilities and explicit non-responsibilities
- [x] define ordered migration lanes, child detailed specs, and deletion gates

**Verification:**
- [x] every meaningful semantic fact has one owner and one non-owner

**Exit Criteria:**
- implementation planning can proceed without reopening core owner boundaries

### Wave 3: Validation and approval readiness

**Purpose:**
- make SSOT and symmetry proof executable

**Steps:**
- [x] define parity tests for enrich, ranking, and CV generation
- [x] define stage-owner tests for `cv_analysis` and `cv_generation`
- [x] define residue grep gates for deleted branch labels and duplicated helper
      logic
- [x] define exact child detailed spec inventory and phase handoff rules
- [x] define docs/settings proof for one runtime-authoritative explanation

**Verification:**
- [x] validation plan can fail any partial migration that keeps two meaning
      owners alive

**Exit Criteria:**
- spec is ready to drive phase specs and implementation plans

## Design Decisions

### Decision: build one shared runtime spine, not four local mini-frameworks

- context: current routed LLM surfaces already share provider/model routing
  intent, but still duplicate pieces of client construction, parsing,
  provenance, and error handling in stage-local code.
- choice: define one repo-native runtime spine used by active LLM surfaces:
  `TaskRequest -> RoutedAdapter -> ParsedResult -> Validator -> Repair/Review -> StageOutput`.
- alternatives considered:
  - keep per-stage local mechanics and chase parity with tests only
  - create large service/repository framework before collapsing ownership
- impact:
  - smaller, reusable, source-first convergence
  - new LLM task can reuse contract instead of cloning mechanics
  - tests can use one fake adapter surface across stages

### Decision: LangGraph is adapter-only everywhere

- context: LangGraph is attractive for orchestration and trace richness, but it
  becomes symmetry debt if it also owns business meaning.
- choice: LangGraph may own transport/orchestration concerns only:
  provider client setup, graph node sequencing, tool usage, trace capture,
  bounded retry execution, and adapter-local telemetry.
- alternatives considered:
  - let LangGraph own full stage semantics where present
  - remove LangGraph entirely
- impact:
  - LangGraph stays reusable without becoming second source of truth
  - repo-native stage contracts remain stable even if adapter changes

### Decision: stage modules own meaning; pipeline owns scheduling only

- context: `pipeline.py` and `pipeline_stage_runner.py` still hold duplicated
  branch logic for `cv_analysis` and `cv_generation`, which breaks symmetry and
  makes tests path-oriented instead of contract-oriented.
- choice: stage modules become sole business entrypoints; pipeline and control
  plane call them, persist outputs, and emit observations only.
- alternatives considered:
  - keep pipeline as semantic orchestrator with stage modules as helpers
- impact:
  - replay, resume, and review flows consume one stage contract
  - parity tests move to stage outputs instead of branch placement

### Decision: `cv_analysis` gets owner collapse before shared spine extraction

- context: `cv_analysis` is upstream of `cv_generation` and already has a usable
  canonical entrypoint in `agentic_cv_analysis.py`, while pipeline and
  stage-runner still duplicate analysis flow.
- choice: collapse `cv_analysis` to one `CvAnalysisRecord` owner first, even
  though it is not the main active routed LLM surface today.
- alternatives considered:
  - postpone `cv_analysis` until after enrich/ranking/CV generation runtime
    spine work
- impact:
  - late-stage semantics stabilize before adapter extraction
  - downstream CV-generation contract stops depending on split upstream logic

### Decision: `cv_generation` keeps one semantic contract and many adapters

- context: current late-stage generation still has semantic split between
  built-in and LangGraph-flavored paths.
- choice: keep one repo-native `cv_generation` contract and let adapters vary
  only by runtime mechanics.
- alternatives considered:
  - hard-switch all semantics directly into LangGraph
  - keep dual semantic methods and call them equivalent
- impact:
  - bounded cv-generation adapter-only spec becomes one child lane under this
    master spec
  - external payloads stabilize across provider swaps

### Decision: `enrich` and `ranking` migrate after late-stage owner collapse

- context: enrich and ranking are active routed LLM surfaces, but their value
  comes from shared runtime mechanics more than from stage-owner collapse.
- choice: migrate them onto shared runtime spine after `cv_analysis` and
  `cv_generation` owner collapse establishes pattern.
- alternatives considered:
  - start with enrich because it is smaller
  - migrate all LLM surfaces in one pass
- impact:
  - shared spine is extracted from proven late-stage owner boundaries, not from
    guessed abstraction
  - enrich/ranking migration becomes simpler and more uniform

### Decision: master spec names child detailed specs before any plan handoff

- context: turning master-level direction into implementation plan now would
  skip bounded design authority for each migration phase and invite scope blur.
- choice: this master spec names one required child detailed spec per phase and
  blocks implementation planning until those child specs exist.
- alternatives considered:
  - write one umbrella implementation plan directly from master spec
  - defer child spec naming until execution starts
- impact:
  - each phase gets bounded design authority
  - plans stay phase-local and executable
  - master spec remains routing authority, not execution checklist

### Decision: observational mode labels are compatibility-only and temporary

- context: `late_stage_mode`, `agentic_late_stage_enabled`, and similar labels
  already drift toward unified runtime truth but still frame some code/tests as
  if there were multiple semantic methods.
- choice: keep these fields only as temporary observational compatibility
  payloads; they must never select semantic behavior and must be removable after
  migration.
- alternatives considered:
  - preserve them as supported semantic routing knobs
  - delete them before contract collapse
- impact:
  - UI/test migration can stay bounded
  - semantic cleanup can land before full payload cleanup

## Invariants

- `config/runtime/control_plane.yaml` remains canonical owner of active LLM
  routing part declarations.
- `runtime_routing.py` remains canonical owner of routed provider/model/base_url/
  wire_api resolution and stage-visible runtime provenance.
- LangGraph never becomes source of truth for stage semantics, status meaning,
  schema meaning, validation meaning, or repair meaning.
- `enrich`, `ranking`, `cv_analysis`, and `cv_generation` each expose one
  canonical repo-native business entrypoint.
- Pipeline and control-plane code may schedule, persist, and present stage
  outputs, but must not re-own stage business logic.
- Active LLM surfaces use one normalized failure taxonomy and one normalized
  provenance shape.
- Adapter-local trace richness may differ, but externally visible stage outputs
  must not differ semantically because of adapter choice.
- Resume, replay, retry, and review-required flows must reuse same stage
  contracts as fresh execution.
- New LLM surfaces must plug into shared spine before introducing stage-local
  runtime mechanics.
- No implementation plan may skip child phase-spec authoring when that phase
  does not already have an accepted detailed spec.

## Acceptance Criteria

- Current routed LLM surfaces (`enrich_extraction`, `ranking_ai_score`,
  `cv_generation_structured_write`) resolve provider/model through one routing
  contract only.
- `cv_analysis` has one canonical `CvAnalysisRecord` owner and pipeline no
  longer duplicates its semantic flow.
- `cv_generation` has one canonical semantic contract and pipeline no longer
  owns separate built-in versus agentic semantic methods.
- Enrich, ranking, and CV generation can all run through one fake adapter in
  deterministic tests after normalizing allowed provider-only diffs.
- External payloads expose one normalized provenance shape and one normalized
  failure taxonomy across active LLM stages.
- Retained compatibility labels such as `late_stage_mode` are observational only
  and do not alter semantic behavior.
- Every migration phase has one named child detailed spec before planning
  begins for that phase.

## Non-Goals

- redesigning business scoring math or job-fit policy
- redesigning candidate evidence policy beyond owner collapse needed for
  `cv_analysis`
- replacing FastAPI, SQLite, or current control-plane stack
- expanding scope to dormant or hypothetical future routed LLM surfaces before
  active ones converge
- forcing every deterministic helper into LangGraph
- writing umbrella implementation plans directly from this master spec

## Risks and Mitigations

- Risk: extracting shared runtime spine too early creates framework slop.
  - mitigation: collapse `cv_analysis` and `cv_generation` owners first; then
    extract only mechanics repeated in real code.
- Risk: tests still encode branch placement instead of contract behavior.
  - mitigation: move tests to stage-entrypoint outputs, normalized provenance,
    and allowed diff sets.
- Risk: enrich or ranking have hidden local assumptions about parsing or failure
  handling.
  - mitigation: migrate them one at a time behind shared fake adapter and
    preserve stage-output contract tests.
- Risk: LangGraph env compatibility overrides reintroduce second routing owner.
  - mitigation: keep drift checks and routed snapshot assertions as explicit
    proof targets.

## Validation Plan

- proof target: child phase-spec set is complete before planning handoff
  - method: inspection of this master spec plus presence check for named child
    detailed specs
  - evidence: Phase 1-5 child spec inventory is explicit here, and any phase
    entering planning has its detailed spec present at canonical path

- proof target: one routing SSOT exists for active routed LLM surfaces
  - method: config/inspection tests and runtime routing tests
  - evidence: active stages resolve provider/model/base_url/wire_api from
    `config/runtime/control_plane.yaml` through `runtime_routing.py` only

- proof target: `cv_analysis` owner collapse is real
  - method: pipeline/stage-runner residue grep plus stage-entrypoint tests
  - evidence: pipeline no longer duplicates evidence-selection/gap/fit semantic
    flow and `analyze_ranked_job(...)` is sole business owner

- proof target: `cv_generation` uses adapter-only LangGraph boundary
  - method: residue grep plus deterministic parity tests for normalized outputs
  - evidence: no decision-critical built-in versus agentic semantic branch
    remains outside adapter seam

- proof target: enrich, ranking, and CV generation share one runtime spine
  - method: targeted unit tests with one fake adapter surface and normalized
    provenance assertions
  - evidence: same request/parse/validate/provenance/error-taxonomy skeleton is
    exercised across all three active routed LLM surfaces

- proof target: compatibility labels are observational only
  - method: control-plane payload tests and pipeline tests
  - evidence: retained mode labels do not change semantic outputs for identical
    deterministic inputs

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

For this master spec, downstream child items include the explicit Phase 1-5
child detailed specs named above.

Canonical source-of-truth:

<LINK>
- `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\docs\operating_system\governance\repo-governance.md`
- `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\scripts\validate_planning_lifecycle.py`
</LINK>

