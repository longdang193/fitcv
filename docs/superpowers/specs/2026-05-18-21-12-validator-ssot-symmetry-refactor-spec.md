---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: validator-ssot-symmetry-refactor-spec
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-generation-repair
targets:
  - src/fitcv/validator.py
  - src/fitcv/cv_generator.py
  - src/fitcv/section_policy.py
  - src/fitcv/candidate_name_policy.py
  - tests/test_validator.py
related_features: []
related_stages: []
---

## Goal

Define bounded refactor and issues patch for `src/fitcv/validator.py` that enforces SSOT, symmetry, invariance without changing external validation schema contract.

## Key Deliverables

### Selected-Evidence Grounding Contract Closure

Specify strict filtering model so selected-evidence checks evaluate only selected evidence rows, not broad payload fallback rows.

### Shared Validation Policy Surfaces

Specify policy extraction boundaries for placeholder normalization and candidate-name placeholder detection so generator/validator/policy modules consume one canonical contract.

### Synthetic Entry Symmetry

Specify parity between generation-time sanitize and validation-time reject checks for equivalent structured sections.

### Regression-Proof Validation Gate

Specify test and typecheck evidence needed to prove no schema/regression drift in validator outputs and downstream callers.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current behavior, dependency boundaries, and defects before edits

**Steps:**
- [x] analyze `src/fitcv/validator.py` equivalence clusters (placeholder, grounding, synthetic, section parsing)
- [x] compare equivalent logic in `src/fitcv/cv_generator.py`, `src/fitcv/section_policy.py`, `src/fitcv/candidate_name_policy.py`
- [x] run GitNexus freshness + impact/context checks for `run_all_validations` and `_normalize_analysis_grounding`

**Verification:**
- [x] symbol blast radius captured (`run_all_validations`, `_normalize_analysis_grounding`: LOW risk)
- [x] contradiction list captured with line-level references

**Exit Criteria:**
- defect and refactor targets bounded to validator-centered patch set

### Wave 2: Decision closure

**Purpose:**
- resolve refactor shape and patch order for minimum-risk rollout

**Steps:**
- [ ] finalize strict selected-evidence filter semantics
- [ ] define placeholder-policy SSOT extraction contract
- [ ] define synthetic-entry symmetry scope (include `experience` parity)
- [ ] lock sequencing: interfaces/policy helpers -> validator internals -> tests

**Verification:**
- [ ] each decision ties to explicit invariant and acceptance criterion

**Exit Criteria:**
- implementation-ready spec with no unresolved correctness ambiguity

### Wave 3: Validation and approval readiness

**Purpose:**
- define executable proof expectations before implementation plan

**Steps:**
- [ ] enumerate unit tests for each contradiction/drift class
- [ ] define typecheck gate and affected-process smoke checks
- [ ] define rollback containment for grounding behavior change

**Verification:**
- [ ] all proof targets have method + evidence artifact

**Exit Criteria:**
- spec ready for handoff to implementation plan

## Design Decisions

### Decision: Selected-evidence checks must be selection-scoped only

- context: `_normalize_analysis_grounding` currently ingests `evidence_payload or evidence_used` and may include rows not explicitly selected.
- choice: build selected set first (`selected_evidence_ids`), then include only rows with matching `evidence_id`; apply explicit fallback mode only when selected set empty and feature flag allows compatibility.
- alternatives considered:
  - keep broad payload inclusion and rely on later relaxations
  - infer selection from row order without IDs
- impact:
  - affects `run_all_validations` grounding behavior
  - requires deterministic tests for selected/unselected mixed payload

### Decision: Placeholder normalization must be SSOT helper

- context: placeholder token logic duplicated across validator/generator/section policy with drift risk.
- choice: extract shared helper module (or centralize in existing policy module) with canonical normalize/check APIs for placeholder tokens.
- alternatives considered:
  - keep per-module copies and synchronize manually
- impact:
  - reduces divergent token vocabulary risk
  - requires parity tests across callers

### Decision: Candidate-name placeholder checks should consume candidate_name_policy

- context: validator has local normalization + token set duplicating `candidate_name_policy`.
- choice: validator imports and uses `is_candidate_name_placeholder` (and helper normalization only if needed for messages).
- alternatives considered:
  - keep local copy for isolation
- impact:
  - removes contradiction risk between generation and validation flows

### Decision: Synthetic section parity must include experience

- context: generator sanitizes synthetic `experience`, validator synthetic non-education checks currently skip `experience`.
- choice: extend validator synthetic checks to include experience with equivalent criteria or shared checker reuse.
- alternatives considered:
  - accept asymmetry as intentional
- impact:
  - stronger invariance for structured CV integrity

### Decision: Preserve public validation schema and downstream call contract

- context: `run_all_validations` consumed by pipeline and agentic generation.
- choice: keep output keys and warning/blocking semantics stable; change internals only.
- alternatives considered:
  - introduce new schema fields for every new internal state
- impact:
  - minimizes caller changes and migration risk

## Invariants

- `run_all_validations` return schema keys remain backward-compatible.
- Missing required sections, grounding violations, skill violations still gate `valid` exactly as before unless explicitly changed in this spec.
- Selected-evidence mode must never admit unselected employer/project/skill support.
- Equivalent placeholder semantics must remain identical across validator/generator/section policy/candidate-name policy surfaces.
- Refactor must not introduce broader file-scope behavior changes outside validation domain.

## Acceptance Criteria

- mixed selected/unselected evidence payload test proves unselected rows do not provide support.
- empty selected-evidence metadata behavior is explicit and tested (compat or strict mode decided and enforced).
- candidate-name placeholder checks in validator route through `candidate_name_policy` API.
- synthetic `experience` placeholder rows are handled symmetrically with generator behavior.
- full `tests/test_validator.py` passes after patch.
- mypy pass on `src` succeeds for touched signatures.

## Non-Goals

- no redesign of full CV policy engine.
- no changes to external pipeline status taxonomy.
- no broad renaming or module moves beyond bounded helper extraction.
- no rewrite of soft-claim similarity heuristics beyond selection-scope correctness.

## Risks and Mitigations

- risk: stricter selected-evidence filter increases validation failures for previously tolerated payloads.
  - mitigation: add compatibility switch path, log support_source_summary mode, rollout with focused regression tests.
- risk: shared placeholder helper changes token behavior unexpectedly.
  - mitigation: introduce parity tests reproducing old accepted/rejected samples before swap.
- risk: downstream callers rely on edge-case warning text.
  - mitigation: preserve canonical message prefixes where feasible; assert key message fragments in tests.

## Validation Plan

- proof target: upstream impact remains bounded for `run_all_validations`
  - method: `npx gitnexus impact -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT" "run_all_validations"`
  - evidence: impact report `risk: LOW`, direct callers list unchanged or intentionally updated

- proof target: `_normalize_analysis_grounding` changes stay local to validator flow
  - method: `npx gitnexus impact -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT" "_normalize_analysis_grounding"`
  - evidence: upstream path remains through `run_all_validations`

- proof target: selected-evidence contradiction fixed
  - method: unit tests in `tests/test_validator.py` for mixed payload selection
  - evidence: deterministic pass/fail assertions on deterministic grounding violations

- proof target: placeholder SSOT and symmetry preserved
  - method: unit tests covering candidate-name + generic placeholder checks in validator/generator-aligned cases
  - evidence: tests pass; no divergent behavior for shared fixture cases

- proof target: no regression in validator public contract
  - method: `uvx pytest tests/test_validator.py`
  - evidence: passing test run with unchanged schema-key assertions

- proof target: type safety preserved after refactor
  - method: `uvx mypy src --show-error-codes`
  - evidence: no new errors in touched modules

## Completion Criteria

1. all Key Deliverables satisfied
2. all implementation tasks derived from this spec reach terminal status (`completed` or explicit `dropped`)
3. validator behavior changes are backed by test evidence and GitNexus scope checks
4. downstream handoff package includes implementation plan reference and verification outputs

## Triage

Layer: change
Feature type: MODIFY
Summary: Refactor validator grounding and policy symmetry contracts with bounded correctness patch.
Reasoning: Defects and drift are implementation-level within existing validation subsystem; no intent/workstream reshaping required.
Invariants:
- preserve validator output schema and caller contract
- preserve warning vs blocking semantics unless explicitly specified
Dependencies:
- fresh GitNexus index for high-trust impact analysis
- existing policy modules (`section_policy`, `candidate_name_policy`, `rule_filter`)
Affected stages:
- none
Affected features:
- cv_system.stage-artifact-diagnostics
Primary lens: cross-cutting
Affected docs:
  feature_source: none
  feature_yaml: none
  feature_lineage: none
  feature_history: none
  stage_source: none
  stage_contract: none
  feature_docs:
    - none
  cross_cutting_docs:
    - docs/superpowers/specs/2026-05-18-21-12-validator-ssot-symmetry-refactor-spec.md
  readme: none
  generated:
    - none
Generated refresh required: no
Capability IDs:
- cv_system.stage-artifact-diagnostics
Invariant IDs:
- none
Spec needed: yes
Plan needed: yes
