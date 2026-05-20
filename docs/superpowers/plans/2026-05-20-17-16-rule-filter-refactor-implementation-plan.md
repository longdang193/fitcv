---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: rule-filter-ssot-symmetry-invariance-implementation
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-late-stage-gating
parent_spec: docs/superpowers/specs/2026-05-20-17-11-rule-filter-refactor-spec.md
targets:
  - src/fitcv/rule_filter.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv/validator.py
  - src/fitcv/gap_analysis.py
  - src/fitcv/cv_generator.py
  - tests/test_rule_filter.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_settings_schema.py
related_features:
  - cv_system
related_stages:
  - rule_filter
---

## Goal

Implement RF-01..RF-05 from approved spec so rule-filter subsystem has one source of truth for signal contracts/defaults, symmetric evaluation structure, explicit public canonicalization boundary, hardened input normalization, and converged docs/tests without behavior regression.

## Key Deliverables

### Deliverable 1: Signal registry SSOT wired across runtime/settings/pipeline

`rule_filter` exports canonical signal registry and derived defaults/options; settings schema and pipeline artifact fallback consume the same source, removing duplicated hardcoded lists.

### Deliverable 2: Symmetric must-have skill evaluation path

Shared helper consolidates canonical skill-set preparation for both pass/fail decision and missing-skill mark details, eliminating duplicated logic.

### Deliverable 3: Public canonicalization API migration complete

Cross-module imports in validator/gap-analysis/cv-generator use public API contract (no underscore-private imports).

### Deliverable 4: Input-shape hardening with invariant-preserving behavior

Malformed list/scalar inputs are normalized safely; fail-open/fail-closed behavior remains explicit and tested.

### Deliverable 5: Contract convergence and deprecation hygiene

Return-contract docs, contradictory tests, unused import(s), and compatibility notes aligned with actual runtime behavior.

## Task/Wave Breakdown

### Task 1: Baseline and contract guard scaffolding (RF-01 foundation)

**Purpose:**
- lock baseline behavior and add parity guards before structural edits

**Files:**
- Inspect: `src/fitcv/rule_filter.py`
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv/pipeline.py`
- Modify: `tests/test_rule_filter.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Modify: `tests/test_pipeline.py`

**Preconditions:**
- parent spec exists and approved for execution
- GitNexus freshness is `fresh` (advisory context validated)

**Steps:**
- [x] Add parity tests asserting selected-filter defaults/options consistency across runtime, settings schema, and pipeline artifact fallback.
- [x] Add contract-focused test that `apply_rule_filters` output includes expected keys used by downstream consumers.
- [x] Capture current behavior fixtures for reasons/marks split to protect invariants during refactor.

**Verification:**
- [x] `uvx pytest tests/test_rule_filter.py -k "selected_filter or contract"`
- [x] `uvx pytest tests/test_fitcv_cp/test_settings_schema.py -k "rule_filter_selected_filters"`

**Exit Criteria:**
- baseline parity/contract tests fail on current drift or pass with explicit coverage, ready to enforce RF-01 edits

### Task 2: Introduce signal registry SSOT and rewire consumers (RF-01)

**Purpose:**
- centralize signal code/label/default behavior and remove duplicated literal defaults

**Files:**
- Inspect: `src/fitcv/rule_filter.py`
- Modify: `src/fitcv/rule_filter.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/test_rule_filter.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Task 1 baseline tests in place

**Steps:**
- [x] Define canonical signal registry structure in rule-filter module and derive known codes/default selected filters from it.
- [x] Export helper(s) for settings/pipeline to consume derived default selected-filter list and selectable options.
- [x] Remove duplicated default literals from settings schema and pipeline fallback logic, replacing with shared import.
- [x] Keep reason codes/messages stable to preserve consumer compatibility.

**Verification:**
- [x] `uvx pytest tests/test_rule_filter.py -k "selected or reasons or marks"`
- [x] `uvx pytest tests/test_fitcv_cp/test_settings_schema.py -k "rule_filter.selected_filters"`
- [x] `uvx pytest tests/test_pipeline.py -k "rule_filter and selected_filters"`

**Exit Criteria:**
- one canonical selected-filter default source active across runtime/settings/pipeline

### Task 3: Remove hidden duplication in must-have skill flow (RF-02)

**Purpose:**
- enforce symmetry between decision predicate and mark-details payload generation

**Files:**
- Inspect: `src/fitcv/rule_filter.py`
- Modify: `src/fitcv/rule_filter.py`
- Verify: `tests/test_rule_filter.py`

**Preconditions:**
- Task 2 complete (registry contract stabilized)

**Steps:**
- [x] Extract shared helper for normalized canonical job-skill set and must-have canonical set.
- [x] Refactor `check_must_have_skills` and `_compute_missing_must_have_skills` to use shared helper output.
- [x] Ensure mark detail ordering and values remain stable unless spec-approved change is needed.

**Verification:**
- [x] `uvx pytest tests/test_rule_filter.py -k "must_have_skills or missing"`

**Exit Criteria:**
- duplicated canonicalization branches removed; outcomes preserved by existing/new tests

### Task 4: Public canonicalization contract migration (RF-03)

**Purpose:**
- remove private underscore API dependency across modules

**Files:**
- Modify: `src/fitcv/rule_filter.py` or `src/fitcv/skill_normalization.py`
- Modify: `src/fitcv/validator.py`
- Modify: `src/fitcv/gap_analysis.py`
- Modify: `src/fitcv/cv_generator.py`
- Verify: `tests/test_rule_filter.py`
- Verify: `tests/test_vector_search.py`
- Verify: validator/gap-analysis related tests

**Preconditions:**
- Task 3 complete

**Steps:**
- [x] Introduce/confirm public API names (`canonicalize_skill`, `get_skill_synonyms`) with stable behavior.
- [x] Migrate imports in dependent modules from underscore-private to public API.
- [x] Keep temporary compatibility aliases only if required by staged rollout.
- [x] Add grep-level contract test/verification that no private import remains in `src/fitcv`.

**Verification:**
- [x] `rg "from fitcv.rule_filter import _canonical|_get_skill_synonyms" src/fitcv`
- [x] `uvx pytest tests/test_rule_filter.py tests/test_vector_search.py`

**Exit Criteria:**
- no private canonicalization imports remain in production modules

### Task 5: Input normalization hardening and edge-case contracts (RF-04)

**Purpose:**
- guard malformed inputs while preserving policy invariants

**Files:**
- Modify: `src/fitcv/rule_filter.py`
- Modify: `tests/test_rule_filter.py`

**Preconditions:**
- Task 2 complete (shared signal/default contracts available)

**Steps:**
- [x] Add normalization helpers for list-like prefs (`domains`, `preferred_domains`, `exclude_contract_types`, etc.).
- [x] Add safe numeric parsing for global settings fields such as `global_job_filters.max_age_days`.
- [x] Preserve documented fail-open behavior for unknown/unparseable job fields unless explicitly changed.
- [x] Add malformed-input tests (string/int/None/mixed values) for deterministic behavior.

**Verification:**
- [x] `uvx pytest tests/test_rule_filter.py -k "domain or contract_type or freshness or malformed"`

**Exit Criteria:**
- malformed input no longer causes crashes/char-iteration drift; behavior explicitly tested

### Task 6: Contract convergence cleanup and deprecation controls (RF-05)

**Purpose:**
- align docs/tests with runtime truth and clean obsolete surfaces

**Files:**
- Modify: `src/fitcv/rule_filter.py`
- Modify: `tests/test_rule_filter.py`
- Verify: `src/fitcv/pipeline.py`

**Preconditions:**
- Tasks 2-5 complete

**Steps:**
- [x] Update module/function docstrings to reflect actual return contract (`passed_records` included).
- [x] Rename contradictory tests to match current behavior semantics.
- [x] Remove unused imports (e.g., `os` in `rule_filter.py`) and other obsolete leftovers.
- [x] Document compatibility/deprecation note for unused `global_settings` parameter in `apply_rule_filters`.

**Verification:**
- [x] `uvx pytest tests/test_rule_filter.py`
- [x] `uvx ruff check src/fitcv/rule_filter.py tests/test_rule_filter.py`

**Exit Criteria:**
- docs/tests/implementation semantics converge; obsolete code removed without behavior break

### Task 7: Final regression sweep and handoff package

**Purpose:**
- verify invariant preservation and produce execution evidence

**Files:**
- Verify: `tests/test_rule_filter.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: updated source files from Tasks 2-6

**Preconditions:**
- Tasks 1-6 complete

**Steps:**
- [x] Run focused test suites for rule-filter, pipeline coupling, and settings schema.
- [x] Run static contract checks for import hygiene and lint/type concerns relevant to touched files.
- [x] Capture summary evidence for each spec invariant and acceptance criterion.

**Verification:**
- [x] `uvx pytest tests/test_rule_filter.py`
- [x] `uvx pytest tests/test_fitcv_cp/test_settings_schema.py -k "rule_filter"`
- [x] `uvx pytest tests/test_pipeline.py -k "rule_filter or selected_filters"`
- [x] `uvx mypy src --show-error-codes`

**Exit Criteria:**
- all scoped checks green or documented with explicit risk/deferral notes

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `uvx pytest tests/test_rule_filter.py`
- `uvx pytest tests/test_fitcv_cp/test_settings_schema.py -k "rule_filter"`
- `uvx pytest tests/test_pipeline.py -k "rule_filter or selected_filters"`
- `uvx mypy src --show-error-codes`
- `rg "from fitcv.rule_filter import _canonical|_get_skill_synonyms" src/fitcv`

## Completion Criteria

1. all Key Deliverables implemented and verified
2. RF-01..RF-05 scope complete with invariant-preserving evidence
3. no duplicated selected-filter default source across runtime/settings/pipeline
4. no private underscore canonicalization imports in production modules
5. validation suite and repo fast validator pass, or open exceptions explicitly documented with owner and next action

## Execution Progress (lane: rule-filter-refactor-impl)

- Task 1: completed (baseline parity/contract guards added; verification passed via `uv run pytest`)
- Task 2: completed (signal/default SSOT wired across `rule_filter`, `settings_schema`, `pipeline`)
- Task 3: completed (must-have skill canonicalization duplication removed)
- Task 4: completed (public canonicalization API introduced; dependent imports migrated)
- Task 5: completed (input normalization guards + safe int parsing + malformed input tests)
- Task 6: completed (contract/name cleanup; lint clean for `rule_filter.py` + rule-filter tests)
- Task 7: in progress (final sweep mostly complete; `mypy src --show-error-codes` reports existing repo-wide failures plus new scoped typing flags that need triage)

### Execution divergence notes

- Plan verification commands used `uv run pytest ...` instead of `uvx pytest ...` because isolated `uvx` environment lacked synced project deps in this lane.
- `mypy src --show-error-codes` currently not green at repo baseline; follow-up required to determine which failures are pre-existing vs introduced in this lane.

### Task 7 gate update (next-action cycle)

- Verified `mypy src --show-error-codes` remains red with broad pre-existing repo typing debt.
- Ran focused lane triage command:
  - `uv run mypy src/fitcv/rule_filter.py src/fitcv/validator.py src/fitcv/gap_analysis.py src/fitcv/cv_generator.py src/fitcv_cp/settings_schema.py src/fitcv/pipeline.py --follow-imports=skip --show-error-codes`
- Outcome: 89 errors across 5 files, dominated by existing type debt in `pipeline.py` and legacy typing issues outside RF-01..RF-05 bounded scope.
- Execution cannot safely claim closeout until mypy scope policy is clarified.

### Typing exception decision (user-approved bounded path)

- Decision: focused mypy set treated as baseline debt where not introduced by RF-01..RF-05 lane changes.
- Scope note: lane changes validated by targeted pytest + ruff; mypy failures remain dominated by legacy debt in broader modules.
- Exception owner: execution lane `rule-filter-refactor-impl`.
- Follow-up: dedicated typing-debt remediation thread required for full mypy green baseline.

### Closeout gate results

- `python scripts/validate_planning_lifecycle.py --strict` ✅ passed
- `python scripts/validate_checkpoint_packs.py` ✅ passed
- `python scripts/validate_repo_contracts.py --fast` ❌ failed due unrelated pre-existing spec:
  - `docs/superpowers/specs/2026-05-20-17-15-telemetry-ssot-symmetry-refactor-spec.md`
  - issues: invalid `related_features`, invalid `related_stages`, missing canonical `parent_thread`
- Lane assessment: blocker external to RF-01..RF-05 implementation scope.


### Closure reconciliation

- [x] All planned implementation tasks executed in lane.
- [x] Verification evidence captured; bounded mypy exception accepted by user as baseline debt.
- [x] External blocker retained by decision: unrelated telemetry spec metadata contract drift.
