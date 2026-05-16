---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: input-data-contract-symmetry-option-c
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-input-mode-parity
targets:
  - src/fitcv_cp/app.py
  - src/fitcv/candidate.py
  - src/fitcv/config.py
  - src/fitcv_cp/templates/runs_list.html
  - tests/test_fitcv_cp/test_app.py
related_features: []
related_stages:
  - normalize
  - enrich
  - rule_filter
---

## Goal

Define a unified per-artifact input contract for trigger-time inputs (`jobs`, `candidate profile`, `synonym overlay`) so acceptance depends on artifact schema semantics, not selected input mode (`path`, `upload`, `paste`, `default_config`).

## Key Deliverables

### Canonical artifact contract definition

A single parse-validate-normalize contract is defined per artifact:
- jobs input
- candidate profile
- synonym overlay

Each contract explicitly states accepted representation formats and canonical runtime representation.

### Mode routing contract

All trigger modes route through the artifact-level contract path, removing mode-specific parser divergence.

### Validation proof contract

A mode-by-mode validation matrix and runtime snapshot invariance checks are defined for implementation handoff.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm current mode/format behavior and existing runtime envelope surfaces before finalizing Option C boundaries

**Steps:**
- [ ] confirm current trigger mode branches in control-plane upload trigger path
- [ ] confirm current candidate parsing split (YAML default path vs JSON upload/paste)
- [ ] confirm synonym overlay normalization and merge behavior
- [ ] confirm runtime envelope fields used as downstream source for inputs

**Verification:**
- [ ] current-state behavior is recorded with no unresolved ambiguity on mode-dependent parser behavior

**Exit Criteria:**
- mode-dependent asymmetry and canonical downstream representations are both explicit

### Wave 2: Decision closure

**Purpose:**
- close Option C design decisions for symmetry, invariance, equivalence, and scope razor

**Steps:**
- [ ] define per-artifact canonical contract surfaces
- [ ] define unified mode-routing requirement for each artifact
- [ ] define format-equivalence rule for candidate profile representations
- [ ] define UI language contract so user-facing labels do not encode parser asymmetry

**Verification:**
- [ ] each core contract question has one chosen decision and one bounded non-goal

**Exit Criteria:**
- design is coherent, bounded, and implementation-plannable

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof expectations concrete for implementation planning

**Steps:**
- [ ] define acceptance criteria as observable input/output behavior
- [ ] define risk and mitigation checks for regression and scope creep
- [ ] define targeted verification evidence expected from tests and runtime snapshot inspection

**Verification:**
- [ ] validation plan can prove contract equivalence and invariance across modes

**Exit Criteria:**
- spec is ready for implementation plan drafting

## Design Decisions

### Decision: Per-artifact canonical parser pipeline

- context: current behavior uses mode-specific parser branches, causing asymmetry and drift risk
- choice: define one parser/validator/normalizer contract per artifact; mode selects source only, never parsing semantics
- alternatives considered:
  - keep status quo mode-specific parsing
  - candidate-only patch (partial symmetry)
- impact:
  - contracts move from mode-centric to artifact-centric
  - reduces duplicated parser rules and inconsistent error behavior

### Decision: Canonical runtime representation invariance

- context: downstream runtime currently relies on normalized snapshots (`jobs_input_json`, `candidate_profile_json`) and normalized synonym runtime payloads
- choice: preserve single canonical representation per artifact regardless of ingest mode
- alternatives considered:
  - preserve mode-specific internal representations
  - store dual raw-format payloads as parallel truth
- impact:
  - downstream behavior remains stable while ingest flexibility increases
  - avoids dual-truth drift

### Decision: Candidate profile representation equivalence

- context: default candidate mode currently resolves from YAML path, upload/paste currently require JSON
- choice: candidate artifact contract must treat YAML and JSON as representation-equivalent when semantic payload matches schema
- alternatives considered:
  - enforce JSON-only across all candidate modes
  - enforce YAML-only across all candidate modes
- impact:
  - removes user-visible inconsistency and contract branching by mode

### Decision: UI contract neutrality

- context: current UI labels encode asymmetry (`Upload JSON` / `Paste JSON` vs default YAML path note)
- choice: UI labels and helper text must describe artifact semantics and accepted representations without mode-biased wording
- alternatives considered:
  - leave current wording and rely on backend behavior changes only
- impact:
  - user expectation aligns with backend equivalence contract

## Invariants

- Acceptance or rejection for an artifact must depend on artifact schema validity, not selected input mode.
- Equivalent semantic payloads for candidate profile must produce equivalent canonical runtime payloads independent of source representation.
- Trigger-time runtime envelope must remain the downstream source of truth for run-scoped inputs.
- Synonym overlay normalization semantics (including section-aware normalization and merge behavior) remain preserved.
- Input-contract refactor must not alter unrelated pipeline stage semantics.

## Acceptance Criteria

1. For each artifact, all supported modes are validated by same artifact-level contract path (no mode-specific parser divergence).
2. Candidate profile payloads that are semantically equal in YAML and JSON are both accepted and produce equal canonical runtime candidate snapshot payloads.
3. Jobs and candidate runtime snapshots remain canonical JSON snapshots in runtime envelope.
4. Synonym overlay input still normalizes to the existing normalized overlay structure and preserves runtime merge semantics.
5. UI text and file accept hints no longer imply contradictory format restrictions relative to backend contract.

## Non-Goals

- Rewriting downstream ranking, enrichment, or CV-generation logic.
- Introducing new pipeline stages or changing stage ordering.
- Defining full implementation task sequencing (belongs to implementation plan).
- Changing persistence schema beyond what is needed to preserve existing canonical runtime input snapshot behavior.

## Risks and Mitigations

- Risk: regression across legacy trigger paths.
  - mitigation: mode-by-mode regression tests for jobs, candidate, and synonyms.
- Risk: scope creep from contract unification into unrelated config/policy refactors.
  - mitigation: strict boundary to input parse/validate/normalize + UI contract + tests.
- Risk: ambiguous mixed-format failure messages after parser unification.
  - mitigation: define and enforce one artifact-level error contract per input channel.

## Validation Plan

- proof target: mode routing no longer changes parsing semantics for each artifact
  - method: inspection + tests
  - evidence: updated trigger-path tests asserting shared artifact-level contract behavior across modes

- proof target: candidate YAML/JSON representation equivalence
  - method: comparison test
  - evidence: tests showing equal canonical `candidate_profile_json` runtime snapshot for equivalent YAML and JSON payloads

- proof target: runtime invariance for jobs and candidate snapshots
  - method: inspection + tests
  - evidence: effective settings/runtime envelope assertions for `jobs_input_json` and `candidate_profile_json`

- proof target: synonym overlay normalization/merge invariance remains intact
  - method: tests
  - evidence: tests asserting normalized overlay structure and expected merged runtime sections

- proof target: UI contract aligns with backend acceptance contract
  - method: inspection + UI template test/assertions
  - evidence: template expectations for neutral format labeling and accepted file types

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
