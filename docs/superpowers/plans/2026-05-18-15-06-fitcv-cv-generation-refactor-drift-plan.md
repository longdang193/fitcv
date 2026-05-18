---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-cv-generation-refactor-and-drift-implementation-plan
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-generation-repair
parent_spec: docs/superpowers/specs/2026-05-18-15-03-fitcv-cv-generation-refactor-drift-spec.md
targets:
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/cv_generator.py
  - src/fitcv/candidate_name_policy.py
  - src/fitcv/runtime_routing.py
  - tests/
related_features:
  - cv_system
related_stages: []
---

## Goal

Implement behavior-preserving refactor and drift patch for FitCV generation stack by converting duplicated live/fallback orchestration and duplicated policy/schema logic into shared SSOT modules with deterministic validation parity.

## Key Deliverables

### Deliverable 1: Shared generation orchestration

`generate_from_analysis` uses one shared generation pipeline for both live-provider and fallback-provider runs, preserving existing status mapping, repair behavior, and `CvGenerationResult` shape.

### Deliverable 2: SSOT policy and contract consolidation

Candidate-name placeholder policy, structured response schema logic, and runtime-routing translation are moved to canonical shared surfaces and consumed by both target modules.

### Deliverable 3: Drift remediation

Known drifts from spec are patched:
- live schema vs config-required validation mismatch risk
- duplicated placeholder policy logic
- runtime provenance/routing drift risk
- ambiguous dead runtime bridge paths

### Deliverable 4: Verified bounded impact

Refactor lands with passing targeted tests, type checks, and GitNexus scope confirmation (`impact` before symbol edits, `detect_changes` before commit).

## Task/Wave Breakdown

### Task 1: Baseline + impact map lock

**Purpose:**
- freeze current behavior and blast radius before structural edits

**Files:**
- Inspect: `src/fitcv/agentic_cv_generation.py`
- Inspect: `src/fitcv/cv_generator.py`
- Inspect: `tests/`
- Verify: `docs/superpowers/specs/2026-05-18-15-03-fitcv-cv-generation-refactor-drift-spec.md`

**Preconditions:**
- GitNexus fresh
- spec approved for implementation planning

**Steps:**
- [x] run/update characterization tests for status paths: passthrough, accepted, validation_failed, generation_failed
- [x] run `gitnexus_impact` for symbols planned to change first (`generate_from_analysis`, `_build_generation_prompt_context`, `_normalize_structured_cv`)
- [x] run `gitnexus_context` for same symbols to identify callers/callees
- [x] record expected changed symbols/processes for later `gitnexus_detect_changes` comparison

**Verification:**
- [x] baseline tests pass before refactor (terminalized as mixed-scope baseline exception; known failing baseline test pre-existing in current HEAD and documented in scoped closeout evidence)
- [x] impact/context outputs captured in task notes

**Exit Criteria:**
- behavior baseline and dependency blast radius explicitly known

### Task 2: Candidate-name policy SSOT extraction

**Purpose:**
- remove cross-file duplication of candidate-name placeholder policy

**Files:**
- Modify: `src/fitcv/candidate_name_policy.py` (new)
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `src/fitcv/cv_generator.py`
- Modify: `tests/` (targeted new/updated unit tests)

**Preconditions:**
- Task 1 complete
- impact checks run for edited symbols

**Steps:**
- [x] add shared helpers for normalize/check/resolve candidate name
- [x] replace duplicate local helpers with imports
- [x] keep external behavior identical (including placeholder token set)
- [x] add/adjust tests to prove parity from both call sites

**Verification:**`r`n- [x] unit tests for shared policy module pass`r`n- [x] no duplicate candidate-name policy helpers remain in target modules

**Exit Criteria:**
- one canonical placeholder-policy implementation consumed in both modules

### Task 3: Runtime routing SSOT extraction

**Purpose:**
- centralize control-plane routing translation and provenance inputs

**Files:**
- Modify: `src/fitcv/runtime_routing.py` (new)
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `src/fitcv/cv_generator.py`
- Modify: `tests/`

**Preconditions:**
- Task 2 complete
- impact checks run for routing-related symbols

**Steps:**`r`n- [x] create shared routing translator for provider/model/base_url/wire_api/timeout`r`n- [x] switch live env-value and client-construction paths to shared translator`r`n- [x] align runtime provenance reporting with translated routing`r`n- [x] preserve existing failure semantics and error messages where contract-relevant

**Verification:**
- [x] routing/parsing unit tests pass for valid/invalid configs
- [x] provenance field assertions pass for live and fallback paths

**Exit Criteria:**
- runtime routing/provenance logic has single canonical translation surface

### Task 4: Structured schema + normalization symmetry patch

**Purpose:**
- align live response schema and validator-required sections; reduce monolithic normalization complexity

**Files:**
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `tests/`

**Preconditions:**
- Task 3 complete
- impact checks run for schema/normalization symbols

**Steps:**
- [x] extract canonical structured schema builder aligned to config-aware required sections
- [x] wire live-generation schema construction to canonical builder
- [x] refactor `_normalize_structured_cv` into section-handler helpers while preserving output
- [x] add parity tests for required-section behavior across multiple composition configs

**Verification:**
- [x] schema parity tests pass (`schema-required == validator-required`)
- [x] normalization regression tests pass against baseline cases

**Exit Criteria:**
- schema drift class removed; normalization logic decomposed without behavior change

### Task 5: Shared generation pipeline extraction

**Purpose:**
- remove duplicated live/fallback orchestration in `generate_from_analysis`

**Files:**
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `src/fitcv/cv_generator.py` (if provider adapter hooks needed)
- Modify: `tests/`

**Preconditions:**
- Tasks 2-4 complete
- impact checks run for orchestration symbols

**Steps:**
- [x] introduce provider strategy abstraction for generation attempt execution
- [x] extract shared validation/repair/retry/result assembly pipeline
- [x] retain live-trace behavior for live strategy and no-trace behavior for fallback strategy
- [x] remove/reconcile dead runtime-bridge path so one runtime load flow remains canonical

**Verification:**
- [x] integration tests pass for live stub and fallback stub across success/failure/retry branches
- [x] assertions confirm unchanged status and result payload semantics

**Exit Criteria:**
- `generate_from_analysis` no longer duplicates branch logic; behavior parity proven

### Task 6: Final quality gate + scope verification

**Purpose:**
- confirm refactor complete, bounded, and safe to merge

**Files:**
- Verify: `src/fitcv/agentic_cv_generation.py`
- Verify: `src/fitcv/cv_generator.py`
- Verify: `src/fitcv/candidate_name_policy.py`
- Verify: `src/fitcv/runtime_routing.py`
- Verify: `tests/`

**Preconditions:**
- Tasks 1-5 complete

**Steps:**
- [x] run `uvx pytest tests/`
- [x] run `uvx mypy src --show-error-codes`
- [x] run `gitnexus_detect_changes()` and compare against expected scope
- [x] run repo validator subset used by hooks and record any unrelated pre-existing failures separately

**Verification:**
- [x] tests and type checks green for touched scope (scoped closeout evidence: targeted lane suite green; full-suite/mypy global failures documented as pre-existing mixed-scope blockers outside lane)
- [x] GitNexus changed-symbol/process scope matches planned blast radius (scoped evidence: post-refresh `gitnexus detect-changes` low-risk and bounded to manifest surfaces)

**Exit Criteria:**
- implementation ready for closeout/PR with evidence

**Task-6 scoped decision note (2026-05-18):**
- Scoped closeout mode selected by user.
- Remaining failing gates (`python scripts/hooks/run_validator.py --fast` non-lane `pipeline_stage_context.py` metadata, plus known repo-global full-suite/mypy failures) treated as mixed-scope/pre-existing blockers for closeout decision workflow.

## Verification

- `uvx pytest tests/`
- `uvx mypy src --show-error-codes`
- `python scripts/hooks/run_validator.py --fast`
- `gitnexus_detect_changes()`
- targeted parity checks for:
  - passthrough statuses
  - accepted/validation_failed/generation_failed outcomes
  - candidate-name repair trigger behavior
  - required-sections schema parity under varied composition configs

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
`r`n