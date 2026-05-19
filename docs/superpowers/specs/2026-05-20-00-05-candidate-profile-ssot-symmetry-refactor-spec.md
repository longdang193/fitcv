---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: candidate-profile-ssot-symmetry-refactor
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-phase-2-source-of-truth-boundary
targets:
  - src/fitcv/candidate.py
  - src/fitcv/vector_search.py
  - src/fitcv/ranking.py
  - src/fitcv/evidence.py
  - tests/test_candidate.py
  - tests/test_vector_search.py
  - tests/test_ranking.py
  - tests/test_evidence.py
related_features:
  - cv_system
related_stages: []
---

## Goal

Define bounded refactor and issue-patch design for candidate profile normalization and inference so equivalent concepts across `candidate`, `vector_search`, `ranking`, and `evidence` share single source of truth, symmetric structure, and invariant behavior without changing external product behavior.

## Key Deliverables

### Deliverable 1: Candidate Contract SSOT

Specify single canonical normalization and validation contract for candidate profile ingestion, including loader parity and typed shape expectations for mixed list/dict profile fields.

### Deliverable 2: Symmetric Role/Domain Inference Surface

Specify shared role/domain inference behavior and config threading so retrieval/query/ranking/evidence surfaces derive equivalent canonical values.

### Deliverable 3: Bounded Issue Patch Set

Specify minimal-risk issue patches for runtime edge cases (mixed shapes, missing type guards, stale helper drift) with explicit compatibility rules.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm current behavior and drift points in scoped runtime module and equivalent downstream consumers

**Steps:**
- [ ] freeze baseline behavior for `load_profile_yaml`, `load_profile_text`, `validate_profile`, `infer_effective_preferences`, `flatten_skills`, `prepare_profile_rows`
- [ ] map equivalent normalization/inference logic in `vector_search`, `ranking`, `evidence`
- [ ] confirm caller blast radius for targeted symbols using GitNexus (`gitnexus_impact`, `gitnexus_context`)

**Verification:**
- [ ] drift inventory lists contradictions, hidden duplication, and edge-case failure paths with file evidence

**Exit Criteria:**
- every proposed refactor maps to explicit source drift or defect

### Wave 2: Decision closure

**Purpose:**
- finalize SSOT/symmetry/invariance decisions and bounded patch ordering

**Steps:**
- [ ] define canonical candidate profile adapter boundary
- [ ] define normalization symmetry model for text/list/role/domain
- [ ] define patch sequencing: contract hardening first, cross-module convergence second

**Verification:**
- [ ] each design decision includes alternatives and dependency order

**Exit Criteria:**
- implementation can proceed in incremental patches without unresolved design branches

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof obligations, regression guardrails, and rollback path

**Steps:**
- [ ] define new/updated tests for loader parity, shape guards, canonicalization parity, and inference parity
- [ ] define compatibility behavior for legacy payload shapes
- [ ] define containment and rollback controls per patch wave

**Verification:**
- [ ] validation plan proves behavior preservation plus issue closure

**Exit Criteria:**
- spec ready for implementation-plan handoff

## Design Decisions

### Decision: Introduce candidate profile contract adapter before broader refactor

- context: current loader/validator paths enforce inconsistent strictness, causing possible runtime and ingestion drift
- choice: centralize profile payload coercion + validation in one adapter function reused by all loaders before profile use
- alternatives considered:
  - patch each loader independently (rejected: drift likely reappears)
  - enforce only at downstream callsites (rejected: too late, inconsistent error semantics)
- impact:
  - unifies ingestion behavior
  - enables safe later extraction of shared normalization utilities

### Decision: Preserve external behavior, tighten internal guardrails

- context: refactor must optimize structure without changing visible runtime policy unexpectedly
- choice: keep existing preference inference priorities and output keys; add deterministic guards for invalid shapes
- alternatives considered:
  - hard schema rejection for all legacy loose payloads (deferred; higher compatibility risk)
- impact:
  - fixes crash-prone paths while maintaining current expected outputs

### Decision: Symmetry by extraction of shared canonicalization utilities

- context: duplicate/near-duplicate normalization exists across `candidate`, `ranking`, `evidence`, `vector_search`
- choice: define one shared normalization utility surface for text/list canonicalization and role-family inference plumbing
- alternatives considered:
  - keep per-module local helpers with comments (rejected: not SSOT)
- impact:
  - lower maintenance overhead, fewer contradiction bugs, higher testability

### Decision: Phase refactor into bounded issue-patch waves

- context: cross-module change has medium-high regression risk
- choice: ordered waves
  - wave A: contract hardening and issue patches in `candidate.py`
  - wave B: config-threading/inference symmetry in `vector_search.py`
  - wave C: shared canonicalization extraction and callsite convergence
- alternatives considered:
  - one-shot refactor (rejected: rollback and diagnosis difficult)
- impact:
  - safer rollout and clear stop points

## Invariants

- `infer_effective_preferences` output contract remains keys: `preferences`, `inferred_preferences`, `effective_preferences`, `preference_sources`
- profile required sections remain enforced: `experiences`, `skills`, `projects`, `achievements`, `preferences`
- role/domain canonical values remain deterministic for identical input and config
- no BigQuery row contract key removal in `prepare_profile_rows`
- no net expansion of public API surface without explicit follow-up spec

## Acceptance Criteria

- all loader entry points apply equivalent validation semantics for profile object shape
- invalid mixed-shape payloads return deterministic `ValueError` or validation errors, not `AttributeError`
- role-family inference path in candidate query construction uses config-aware behavior consistent with candidate/ranking policies
- canonicalization parity tests pass across candidate/ranking/evidence/vector_search for shared concepts
- existing behavior-focused tests remain green unless explicitly updated by approved contract change

## Non-Goals

- redesign of candidate business semantics (ranking policy, scoring weights, domain taxonomies)
- wholesale migration to strict external schema library (pydantic/marshmallow) in this thread
- refactor of unrelated modules outside scoped symbol dependents
- BigQuery schema redesign or storage migration

## Risks and Mitigations

- risk: hidden downstream reliance on permissive payload shapes
  - mitigation: explicit compatibility tests for legacy string/dict skill forms before stricter guards
- risk: cross-module normalization extraction changes token canonicalization subtly
  - mitigation: snapshot/parity tests against current expected normalized outputs
- risk: inference symmetry changes retrieval composition
  - mitigation: add side-by-side tests for candidate query component generation with representative config
- risk: broad caller impact from shared helper changes
  - mitigation: run GitNexus impact and caller-aware test subset before each wave merge

## Validation Plan

- proof target: loader parity invariant across YAML/JSON/text entry paths
  - method: unit tests for `load_profile_yaml`, `load_profile_json_text`, `load_profile_text`
  - evidence: passing tests in `tests/test_candidate.py` covering same invalid/valid payload corpus

- proof target: issue patch closes runtime crash edge cases
  - method: negative-shape tests (non-dict list entries in skills/achievements/experiences)
  - evidence: deterministic validation errors, no `AttributeError` traces

- proof target: canonicalization/inference symmetry across modules
  - method: parity tests for role/domain/list canonicalization and config-aware family inference
  - evidence: passing assertions in `tests/test_candidate.py`, `tests/test_vector_search.py`, `tests/test_ranking.py`, `tests/test_evidence.py`

- proof target: no unintended refactor blast radius
  - method: GitNexus `gitnexus_detect_changes()` after implementation waves
  - evidence: changed symbols/processes align with approved wave scope

- proof target: repo contract safety unchanged
  - method: validator + targeted runtime tests
  - evidence: `python scripts/hooks/run_validator.py --fast` and focused pytest suite pass

## Completion Criteria

1. all Key Deliverables defined in this spec are implemented or explicitly deferred with rationale
2. wave A/B/C patch sequence is completed with per-wave verification evidence
3. all acceptance criteria and invariants are satisfied
4. no unresolved high-risk contradiction remains in scoped modules

## Triage

Layer: change  
Feature type: MODIFY  
Summary: Refactor and patch candidate-profile normalization/inference surfaces for SSOT, symmetry, invariance.  
Reasoning: Work is bounded runtime change inside existing feature capabilities with no intent/operating-system contract change.  
Invariants:
- Preserve external behavior contracts listed above.
Dependencies:
- Existing candidate/ranking/vector_search/evidence tests.
Affected stages:
- none
Affected features:
- cv_system.stage-artifact-diagnostics
Primary lens:
- cross-cutting
Affected docs:
- cross_cutting_docs:
  - docs/superpowers/specs/2026-05-20-00-05-candidate-profile-ssot-symmetry-refactor-spec.md
Generated refresh required:
- no
Capability IDs:
- none
Invariant IDs:
- none
Spec needed:
- yes
Plan needed:
- yes
