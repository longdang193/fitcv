---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: telemetry-ssot-symmetry-refactor
parent_thread: workstream-agentic-observability.agentic-observability-shared-trace-standard
targets:
  - src/fitcv/telemetry.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_observability.py
  - src/fitcv_cp/reporter.py
  - tests/test_fitcv/test_telemetry.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_reporter.py
related_features:
  - cv_system
related_stages:
  - cv_analysis
---

## Goal

Define bounded refactor patch set (RF-01, RF-02, RF-03, RF-04, RF-05) that removes telemetry drift/duplication/contract contradictions while preserving external runtime behavior and trace artifact compatibility.

## Key Deliverables

### D1: Telemetry contract SSOT

Single shared contract surface for telemetry status values, degradation reasons, and Langfuse/OTel env parsing semantics.

### D2: Symmetric observation and event payload construction

Equivalent event/observation concepts (analysis/generation; pipeline/reporter) use equivalent structure, bounded rules, and status vocabulary.

### D3: Invariant-safe migration path

Refactor sequence with explicit compatibility guardrails, verification evidence, and rollback boundaries.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current contract behavior before edits

**Steps:**
- [ ] freeze baseline behavior for telemetry and reporter status outputs
- [ ] capture current payload shapes for:
  - `build_langfuse_item_observation_attributes`
  - `_bounded_event_payload` and `build_bounded_event_payload`
- [ ] map current finding categories to code locations:
  - drift, contradiction, obsolete/unused, hidden duplication, missing contract, risky edge case

**Verification:**
- [ ] baseline fixtures/golden assertions exist for all touched contracts

**Exit Criteria:**
- no refactor decision depends on implicit behavior assumptions

### Wave 2: Decision closure

**Purpose:**
- define exact patch boundaries for RF-01..RF-05

**Steps:**
- [ ] RF-01 define constants/enums and contract module scope in `telemetry.py`
- [ ] RF-02 unify bounded serialization pipeline into one recursive engine with configurable limits
- [ ] RF-03 extract shared error-summary normalizer used by analysis/generation render paths
- [ ] RF-04 replace `pipeline.py` local event payload clone with canonical `pipeline_observability.build_bounded_event_payload`
- [ ] RF-05 fix observation type/name contradiction in item envelope assembly and call contracts

**Verification:**
- [ ] every finding category maps to at least one RF action

**Exit Criteria:**
- design decisions are concrete enough for implementation plan handoff

### Wave 3: Validation and approval readiness

**Purpose:**
- prove invariance and compatibility envelope

**Steps:**
- [ ] define acceptance criteria for each RF action
- [ ] define regression tests and schema checks
- [ ] define rollback containment boundaries per RF action

**Verification:**
- [ ] validation plan provides objective evidence paths

**Exit Criteria:**
- spec is implementation-plan ready

## Design Decisions

### Decision: RF-01 telemetry contract constants become SSOT

- context: status/degradation vocab duplicated and drift-prone across telemetry and reporter surfaces
- choice: introduce canonical constants (or enum-like module constants) in `src/fitcv/telemetry.py` and consume from all in-scope callers
- alternatives considered:
  - leave strings inline and add docs only
  - create new module for contracts now
- impact:
  - removes missing-contract class for status/reason vocab
  - creates one edit surface for future status expansion

### Decision: RF-02 bounded serialization engine merged

- context: `_bounded_langfuse_value` and `_bounded_langfuse_item_value` are structurally duplicate with different defaults
- choice: one recursive bounded serializer with explicit profile knobs (`max_chars`, `collection_limit`, `mapping_limit`, `text_limit`)
- alternatives considered:
  - keep both and add comments
  - merge partially by wrapper indirection only
- impact:
  - eliminates hidden duplication and symmetry drift
  - raises medium/high migration risk for payload shape if defaults mismatch; mitigated by fixtures

### Decision: RF-03 shared error summary extractor

- context: same error reduction logic repeated in multiple rendering paths
- choice: one helper function for dict/string/None error payloads with bounded excerpt
- alternatives considered:
  - keep repeated logic for local readability
- impact:
  - low-risk dedup
  - foundation for RF-05 consistency

### Decision: RF-04 event payload builder canonicalization

- context: `pipeline.py` duplicates builder logic already present in `pipeline_observability.py`
- choice: route all pipeline event payload creation through `build_bounded_event_payload` and remove local clone
- alternatives considered:
  - maintain two builders + parity tests
- impact:
  - removes drift and contradiction risk in optional fields/normalization
  - reduces long-term maintenance surface

### Decision: RF-05 observation type/name contract correction

- context: item envelope currently receives `observation_type=observation_name` while caller also passes logical type
- choice: preserve semantic split:
  - `observation_name`: concrete operation id (`cv_analysis_item`, `cv_generation_item`)
  - `observation_type`: contract category (`generation`, etc.)
- alternatives considered:
  - collapse to single field
- impact:
  - resolves contradiction category
  - may affect downstream dashboards relying on previous overwritten value; handled by compatibility migration note

## Invariants

- trace context fallback ids remain OTel-compatible lengths (`trace_id`=32, `span_id`=16, `parent_span_id`=16)
- telemetry disabled/degraded/export_enabled behavior semantics remain stable
- no manual edits to unrelated feature/stage generated contracts
- event payload required keys remain stable for existing reporter consumers
- Langfuse markdown/json bounding remains deterministic and truncation marker-stable
- `fitcv` pipeline control flow and stage outcomes unchanged by refactor

## Acceptance Criteria

1. RF-01:
- all status/degradation reason string literals in scoped files replaced by contract constants except externally mandated literal protocol fields

2. RF-02:
- one canonical bounded serialization function family used by all Langfuse payload builders in `telemetry.py`
- baseline fixture diff only in explicitly approved fields

3. RF-03:
- no duplicated error-summary extraction branches remain in `pipeline_observability.py`

4. RF-04:
- `_bounded_event_payload` removed from `pipeline.py` and behavior delegated to `pipeline_observability.build_bounded_event_payload`

5. RF-05:
- item envelope preserves caller-provided `observation_type`
- tests assert `observation_name` and `observation_type` are distinct and correct

6. Finding-category coverage:
- each category (drift, contradiction, obsolete/unused, hidden duplication, missing contract, edge case) mapped to an implemented patch or explicit deferred note

## Non-Goals

- no OTel exporter architecture redesign
- no Langfuse ingestion protocol redesign in `fitcv_cp/reporter.py`
- no new external telemetry sinks
- no broad cross-repo rename outside scoped telemetry/observability surfaces
- no implementation plan generation in this artifact

## Risks and Mitigations

- risk: silent payload contract drift after RF-02/RF-04
  - mitigation: golden payload tests before/after; approve deltas explicitly

- risk: dashboard/analytics dependency on previous `observation_type` overwrite behavior
  - mitigation: compatibility note + transitional alias field if needed

- risk: accidental behavior change from status literal centralization
  - mitigation: constants map exactly to existing strings; no semantic rename in same patch

- risk: hidden call sites in unscoped modules
  - mitigation: repo grep + GitNexus impact checks for touched symbols before edits

## Validation Plan

- proof target: RF-01 central status/degradation SSOT adopted
  - method: inspection + unit tests
  - evidence: no disallowed inline literals in scoped files; passing status contract tests

- proof target: RF-02 unified bounded serializer preserves invariants
  - method: fixture comparison + unit tests
  - evidence: passing `tests/test_fitcv/test_telemetry.py` with added golden payload cases

- proof target: RF-03 duplicate error-summary logic removed
  - method: inspection + targeted tests
  - evidence: single helper usage across analysis/generation renderers

- proof target: RF-04 event payload symmetry enforced
  - method: integration-level pipeline tests
  - evidence: passing relevant `tests/test_pipeline.py` event-emission assertions

- proof target: RF-05 observation contract corrected without regressions
  - method: unit tests + reporter integration assertions
  - evidence: `tests/test_fitcv/test_telemetry.py` and `tests/test_fitcv_cp/test_reporter.py` pass with explicit name/type assertions

- proof target: finding categories fully addressed
  - method: traceability matrix in implementation PR
  - evidence: matrix row per category linked to RF action and test evidence

## Completion Criteria

1. all Key Deliverables are satisfied
2. RF-01..RF-05 decisions are unchanged or explicitly superseded by approved follow-up spec
3. acceptance criteria are fully testable and mapped to validation evidence
4. implementation handoff can proceed to `skill-writing-plans` without unresolved design ambiguity
