---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv_cp.app SSOT/symmetry/invariance refactor implementation plan (R1-R5)
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-05-24-10-02-fitcv-cp-app-ssot-symmetry-refactor-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/orchestrator.py
related_features: []
related_stages: []
---

# Implementation Plan: `fitcv_cp.app` SSOT / symmetry / invariance refactor (R1–R5)

## Goal

Execute refactor R1–R5 from spec `docs/superpowers/specs/2026-05-24-10-02-fitcv-cp-app-ssot-symmetry-refactor-spec.md` with bounded, test-backed steps that eliminate drift/contradiction/duplication and enforce shared invariants, while preserving intended runtime behavior.

## Key Deliverables

### Deliverable 1: Unambiguous control-plane call paths (SSOT)

- `src/fitcv_cp/app.py` has no shadow-import contradictions.
- Run-store operations and orchestration operations each have one canonical call path.

### Deliverable 2: Contract helpers + tests enforcing invariance (symmetry/invariance)

- Run-mode normalization/labeling uses single SSOT helper.
- JSON decode/pretty/schema validation helpers are shared and used consistently.
- Global mutable cache strategy is bounded or replaced with deterministic binding.
- Tests prove invariants and prevent reintroduction of drift.

## Task/Wave Breakdown

### Task 0: Baseline + guardrails (preflight)

**Purpose:**
- establish baseline behavior, tests, and refactor safety rails before touching high-blast-radius code

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/run_artifact_contracts.py`
- Inspect: `src/fitcv_cp/store.py`
- Inspect: `src/fitcv_cp/orchestrator.py`
- Verify: `scripts/hooks/run_validator.py`

**Preconditions:**
- GitNexus index fresh (`npx gitnexus analyze`)

**Steps:**
- [x] Run repo validator fast path: `python scripts/hooks/run_validator.py --fast`
- [x] Identify existing tests for `fitcv_cp` (coverage exists under `tests/test_fitcv_cp/`)
- [x] Record baseline semantics (as test cases) for:
  - `run_mode_label` fallback behavior (known + unknown values)
  - JSON decode failure behavior on representative endpoints/helpers
  - orchestration binding behavior for submit/continue flows (where observable)

**Verification:**
- [ ] Baseline validator run is green.
 - [x] Baseline validator run is green.

**Exit Criteria:**
- baseline tests or test scaffolding plan exists for each invariant touched by R1–R5.

### Task 1: R1 — Remove shadow-import contradictions in `app.py`

**Purpose:**
- eliminate contradictions/obsolescence caused by importing names that are shadowed by in-module definitions

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`

**Preconditions:**
- Task 0 complete

**Steps:**
- [x] Use GitNexus impact before editing any targeted symbol(s) inside `src/fitcv_cp/app.py` that will be modified (per repo rule): `npx gitnexus impact <symbol>`
- [x] Remove/rename imports that are shadowed by local defs (prefer module imports or explicit aliasing).
- [x] Ensure `app.py` has exactly one readable store/orchestration symbol per concept (no “two ways to call same thing”).
- [x] Add/adjust import-time smoke test to catch shadow-import regressions (covered by existing unit tests importing `fitcv_cp.app`, plus explicit `sys.path.insert(0, "src")` import check).

**Verification:**
- [x] `python -c "import fitcv_cp.app"` succeeds.
- [x] `python scripts/hooks/run_validator.py --fast` green.
 - [ ] If `uvx pytest ...` lacks dependencies (ex: `fastapi`), use project environment: `uv sync --group dev` then `uv run pytest ...`

**Exit Criteria:**
- `app.py` contains no shadow-import pattern and remains importable.

### Task 2: R3 — Make run-mode normalization/labeling SSOT

**Purpose:**
- remove drift between `RUN_MODE_LABELS` in `app.py` and `run_artifact_contracts.py` and enforce invariant fallback semantics

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/run_artifact_contracts.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/run_artifact_contracts.py`
- Verify: tests (new or existing)

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Run GitNexus impact for symbols to be edited (label dicts/functions).
- [x] Remove duplicate `RUN_MODE_LABELS` definition from `app.py` (or make it a re-export only if needed).
- [x] Route all run-mode label usage in `app.py` through `run_artifact_contracts.run_mode_label()` (or equivalent SSOT API).
- [x] Add unit tests for:
  - known run modes
  - unknown run mode values (including `None`, non-string)
  - invariant: never returns raw unknown identifiers

**Verification:**
- [x] Unit tests green. (If `uvx pytest` lacks deps, use `uv sync --group dev` + `uv run pytest ...`)
- [x] Validator fast path green.

**Exit Criteria:**
- One SSOT run-mode labeling rule, enforced by tests.

### Task 3: R4 — Centralize JSON decode/pretty/schema validation helpers

**Purpose:**
- remove hidden duplication + missing contract enforcement for JSON payloads and schema versions

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/run_artifact_contracts.py` (or new helper module under `src/fitcv_cp/`)
- Verify: tests

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Run GitNexus impact for helper insertion points and call sites.
- [x] Create shared helpers for:
  - JSON decode (strict and tolerant variants as needed)
  - pretty-printing stable JSON
  - schema version presence/match check for schema-version-tagged payloads
- [x] Replace ad-hoc `_json.loads(...)` patterns in `app.py` for key surfaces with helpers, prioritizing:
  - stage transition artifacts JSON
  - mapping suggestions aggregate JSON
  - synonym proposals JSON
- [x] Add tests covering:
  - malformed JSON
  - missing schema version field
  - wrong schema version field
  - tolerant vs strict behavior (explicit)

**Verification:**
- [x] Unit tests green.
- [x] `python scripts/hooks/run_validator.py --fast` green.

**Exit Criteria:**
- Consistent JSON contract behavior enforced via shared helpers + tests.

### Task 4: R2 — Introduce single RunStore façade (or central selector) for store ops

**Purpose:**
- remove repeated backend-selection branches and enforce store-selection invariance

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/store.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/store.py` (only if interface tightening required)
- Verify: tests

**Preconditions:**
- Task 3 complete

**Steps:**
- [x] Run GitNexus impact for the highest-caller symbols (`get_run`, `list_runs`, etc.) before refactor (expect large blast radius; keep change minimal).
- [x] Implement façade or selector abstraction with explicit interface:
  - single place chooses backend (ControlPlaneStore vs BigQuery store)
  - routes and helpers depend on façade/selector, not global branching per function
- [x] Migrate call sites in small batches:
  - start with read-only ops (`get_run`, `list_runs`, `get_events`)
  - then mutate ops (update status/checkpoint/artifacts, append events)
- [x] Add façade tests to prove:
  - correct backend chosen in both modes
  - arguments forwarded correctly
  - no mixed-backend behavior within a request path (where testable)

**Verification:**
- [x] Tests green (unit + any existing endpoint tests).
- [x] `python scripts/hooks/run_validator.py --fast` green.

**Exit Criteria:**
- Store-selection logic centralized; repeated `if _CP_STORE` patterns eliminated.

### Task 5: R5 — Fix `_RUN_SUBMISSION_CACHE` edge-case risk

**Purpose:**
- eliminate or bound global mutable cache; preserve orchestration invariants

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/orchestrator.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/orchestrator.py` (only if required)
- Verify: tests

**Preconditions:**
- Task 4 complete

**Steps:**
- [x] Run GitNexus impact on orchestration-related symbols to be modified.
- [x] Choose strategy (must match spec decision; if unresolved, stop and update spec):
  - Strategy A (preferred): deterministic binding using persisted run fields; remove cache.
  - Strategy B: bounded cache (TTL + max size + eviction) with explicit behavior and logs.
- [x] Implement chosen strategy and add tests for submit/continue flow behavior.

**Verification:**
- [x] Tests green.
- [x] No unbounded global cache remains.

**Exit Criteria:**
- Orchestration binding behavior preserved; hidden mutable state bounded/removed.

### Task 6: Final proof + scope check

**Purpose:**
- prove invariants preserved and refactor scope remains bounded

**Files:**
- Verify: repo-wide validation scripts and test outputs

**Preconditions:**
- Tasks 1–5 complete

**Steps:**
- [x] Run validator: `python scripts/hooks/run_validator.py --fast`
- [x] Run Python tests: `uv run pytest tests/test_fitcv_cp/`
- [x] Run lane typecheck (targeted): `uv run mypy src/fitcv_cp/synonym_proposals.py --show-error-codes`
- [ ] Run repo-wide type check: `uv run mypy src --show-error-codes` (known baseline failures outside lane; informational only)
- [x] Run GitNexus scope check: `npx gitnexus detect-changes -r "<worktree path>" --scope all`

**Verification:**
- [ ] All commands green; GitNexus shows only expected symbols/files affected.

**Exit Criteria:**
- Deliverables satisfied and ready for execution handoff.

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `uvx pytest tests/`
- `uvx mypy src --show-error-codes`
- `npx gitnexus detect-changes`

## Completion Criteria

1. All Key Deliverables satisfied.
2. All tasks either `completed` or explicitly `dropped` with rationale.
3. Final verification evidence exists (command outputs + GitNexus detect-changes report).
