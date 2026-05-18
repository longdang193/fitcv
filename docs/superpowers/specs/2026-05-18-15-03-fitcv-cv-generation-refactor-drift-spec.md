---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-cv-generation-refactor-and-drift-patch
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-generation-repair
targets:
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/cv_generator.py
related_features:
  - cv_system
related_stages: []
---

## Goal

Define bounded, behavior-preserving refactor and drift-patch design for `src/fitcv/agentic_cv_generation.py` and `src/fitcv/cv_generator.py` that enforces SSOT, structural symmetry, and deterministic validation behavior across live and fallback CV generation paths.

## Key Deliverables

### Deliverable 1: Unified generation pipeline design

Design one shared orchestration pipeline for live-provider and fallback-provider runs, removing duplicated validation/repair/result assembly logic while preserving output contract (`CvGenerationResult`) and runtime provenance semantics.

### Deliverable 2: SSOT policy consolidation

Design one canonical home for:
- candidate-name placeholder policy
- structured CV schema contract used for prompt response shape and validator-required sections
- runtime routing/provider translation from control-plane model routing

### Deliverable 3: Drift patch scope

Define explicit patches for currently observed drifts:
- schema requirement mismatch risk between live JSON schema and config-aware validation
- duplicated placeholder policy logic across modules
- potential runtime provenance/reporting divergence between fallback and control-plane routing
- dead or ambiguous runtime bridge paths that no longer match active orchestration

### Deliverable 4: Verification gate

Define validation evidence proving no external behavior regressions in accepted/validation_failed/generation_failed passthrough and retry outcomes.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- establish exact duplication seams, drift vectors, and coupling boundaries before edits

**Steps:**
- [ ] map long-function and duplicate-logic hotspots in both target modules
- [ ] map caller/callee blast radius for symbols planned for extraction using GitNexus impact/context
- [ ] classify each drift as contract drift, policy drift, or observability drift
- [ ] capture no-change behavioral baselines for key statuses and retry behavior

**Verification:**
- [ ] hotspot inventory, dependency map, and drift taxonomy are recorded and testable

**Exit Criteria:**
- all planned refactors have identified owners, interfaces, and risks

### Wave 2: Decision closure

**Purpose:**
- close design decisions for structure, ownership, and rollout order

**Steps:**
- [ ] define provider strategy interface and shared pipeline API
- [ ] define canonical modules for policy/schema/routing SSOT
- [ ] define decomposition of long functions into pure units
- [ ] define migration order interfaces → implementations → callers → tests

**Verification:**
- [ ] each major design split has rationale, alternatives, and compatibility notes

**Exit Criteria:**
- design supports incremental, reversible commits with green tests at each step

### Wave 3: Validation and approval readiness

**Purpose:**
- specify proof for behavior parity and drift closure

**Steps:**
- [ ] define unit/integration test matrix by status path and retry branch
- [ ] define static checks (`pytest`, `mypy`) and expected pass criteria
- [ ] define post-refactor GitNexus scope verification (`gitnexus_detect_changes`)

**Verification:**
- [ ] validation plan can prove parity and bounded blast radius

**Exit Criteria:**
- spec ready for implementation planning

## Design Decisions

### Decision: Introduce shared `GenerationPipeline` orchestration

- context: `generate_from_analysis` currently duplicates near-identical flow for live and fallback providers
- choice: extract orchestration into shared pipeline with provider-specific strategy methods (`generate_once`, `runtime_provenance`, optional trace hooks)
- alternatives considered:
  - keep current branches and only trim lines
  - move only retry logic without provider abstraction
- impact:
  - reduces branch divergence risk
  - centralizes validation/repair/retry semantics
  - lowers regression probability for status mapping

### Decision: Create SSOT module for candidate-name placeholder policy

- context: placeholder normalization/check logic duplicated in both modules
- choice: move normalization and predicate helpers to one policy module (for example `fitcv/candidate_name_policy.py`)
- alternatives considered:
  - keep duplicate helpers and add comments
- impact:
  - eliminates policy drift
  - simplifies deterministic tests for name enforcement

### Decision: Create SSOT builder for structured CV response schema

- context: live-provider response schema manually encoded separately from config-aware validation contract
- choice: expose one schema builder aligned to required-section logic and reuse it in live prompt/response shape construction
- alternatives considered:
  - keep hand-authored schema in `agentic_cv_generation.py`
- impact:
  - removes schema drift class
  - aligns generation constraints with validator requirements

### Decision: Centralize runtime routing translation

- context: control-plane route resolution and env/client mapping split across modules
- choice: create one routing translation layer that resolves provider/model/base_url/wire_api/timeouts and returns structured runtime config
- alternatives considered:
  - leave env-building and client-building separate
- impact:
  - consistent runtime provenance reporting
  - single failure surface for provider misconfiguration

### Decision: Table-driven section normalization and prompt-context decomposition

- context: `_normalize_structured_cv` and `_build_generation_prompt_context` are large multi-responsibility functions
- choice: split into section handlers and focused pure builders (constraints, evidence summary, section hints, analysis summary)
- alternatives considered:
  - partial extraction of only smallest loops
- impact:
  - improved testability
  - easier extension of section policies without monolithic edits

### Decision: Remove or reintegrate ambiguous dead runtime bridge paths

- context: runtime bridge helper path appears partially redundant against active live path
- choice: either remove unused bridge helpers or rewire call sites so one runtime load path is canonical
- alternatives considered:
  - keep dormant helper for future use
- impact:
  - reduces maintenance ambiguity
  - avoids silent divergence in future edits

## Invariants

- external output contract of `generate_from_analysis` remains backward compatible (`CvGenerationResult` keys/status semantics unchanged)
- passthrough behavior for non-ready analysis status remains unchanged
- validation and repair semantics remain deterministic:
  - candidate-name placeholder repair only when strict conditions met
  - missing/shallow section retry logic unchanged in meaning
- live and fallback providers must use same post-generation validation and repair pipeline
- required structured CV sections remain config-aware and validator-aligned
- control-plane routing remains authoritative source for provider/model/base_url/wire_api mapping
- no private/public boundary violations introduced

## Acceptance Criteria

1. `generate_from_analysis` complexity reduced by extracting shared pipeline and provider strategy with no status/output regressions.
2. Candidate-name placeholder policy exists in one canonical module and both target files consume it.
3. Structured CV response schema used by live generation is produced from canonical contract logic aligned with `validate_structured_cv` and config-required sections.
4. Runtime routing translation is centralized; runtime provenance for fallback/live paths is consistent with resolved routing.
5. Long-function decomposition completed for:
   - `generate_from_analysis`
   - `_build_generation_prompt_context`
   - `_normalize_structured_cv`
6. Drift patch closes four identified drift classes (schema, policy, provenance, dead-path ambiguity).

## Non-Goals

- changing product behavior of CV quality scoring, evidence ranking, or fit classification logic
- redesigning prompt content strategy beyond structural extraction and SSOT normalization
- introducing new external APIs or changing persisted result schema names
- broad cross-repo refactors outside two target modules and newly introduced helper modules required by this spec

## Risks and Mitigations

- risk: hidden behavior drift during extraction
  - mitigation: characterize current behavior with targeted tests before refactor; keep small commits
- risk: cross-module import cycles from new SSOT helpers
  - mitigation: place helpers in low-level policy/contract modules with no higher-level orchestration imports
- risk: schema over-tightening breaks provider output parsing
  - mitigation: parity tests for representative live/fallback payloads and controlled coercion behavior
- risk: refactor affects upstream callers unexpectedly
  - mitigation: run GitNexus impact/context on extracted symbols before edits and `gitnexus_detect_changes` before commit

## Validation Plan

- proof target: behavior parity for non-ready passthrough statuses
  - method: unit tests covering each passthrough status mapping and error payload handling
  - evidence: passing tests validating unchanged `CvGenerationResult.status` and `outcome_reason/error`

- proof target: behavior parity for live/fallback accepted and failed outcomes
  - method: integration-style tests with provider stubs for accepted, validation failure, generation failure, retry success/failure
  - evidence: snapshot/assertion parity on status, repair metadata, runtime provenance, trace payload fields

- proof target: SSOT consolidation correctness
  - method: unit tests for candidate-name policy module and schema builder module
  - evidence: no duplicate helper definitions in target files; tests proving shared helper behavior

- proof target: drift patch closure
  - method: targeted assertions for config-aware required-sections schema parity and provenance consistency
  - evidence: tests asserting schema required sections match validator-required sections for multiple config compositions

- proof target: static safety and bounded impact
  - method: `uvx pytest tests/`, `uvx mypy src --show-error-codes`, `gitnexus_detect_changes()` pre-commit
  - evidence: green test/type checks and expected symbol/process impact only

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
