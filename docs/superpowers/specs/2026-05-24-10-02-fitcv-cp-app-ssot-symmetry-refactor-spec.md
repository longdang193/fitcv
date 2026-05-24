---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv_cp.app SSOT/symmetry/invariance refactor (R1-R5)
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/orchestrator.py
related_features: []
related_stages: []
---

# Detailed Spec: `fitcv_cp.app` SSOT / symmetry / invariance refactor (R1–R5)

## Goal

Refactor `src/fitcv_cp/app.py` to remove contradictions, drift, and hidden duplication by enforcing:

- **SSOT:** one canonical implementation per concept (store ops, orchestration ops, labeling/contract helpers).
- **Symmetry:** equivalent flows (UI, downloads, persistence, event surfaces) use equivalent structure and normalization rules.
- **Invariance:** shared rules/defaults/contracts stay consistent across surfaces, and are enforced via shared helpers + tests.

Scope bounded to improving structure and contract enforcement without intended behavior change, except where current behavior is inconsistent/undefined (those changes must be explicitly decided and validated).

## Key Deliverables

### Deliverable 1: Single-source runtime façade surfaces

Define explicit module-level SSOT boundaries so `app.py` routes depend on:

- a single run-store façade (ControlPlaneStore vs BigQuery store selection),
- a single orchestration façade (`ORCHESTRATION_ADAPTER`),
- shared contract helpers (run-mode normalization/labeling, JSON decode/pretty/schema validation).

### Deliverable 2: Drift/contradiction elimination with acceptance proofs

Eliminate:

- shadow-import contradictions (importing symbols that are immediately shadowed by local definitions),
- drift between `RUN_MODE_LABELS` rules in different modules,
- ad-hoc JSON decoding/pretty-print patterns without shared invariants,
- global mutable caches without explicit safety bounds.

Provide acceptance criteria and validation evidence for each.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- define current behavior, boundaries, and constraints inside `src/fitcv_cp/app.py` and directly related helper modules

**Steps:**
- [ ] inventory equivalent concepts inside `app.py`:
  - run store ops (`get_run`, `list_runs`, mutators, event append)
  - orchestration ops (`enqueue_run`, `cancel_queued_run`, status)
  - labeling/contract dicts (`RUN_MODE_LABELS`, stage download labels, decision-chain labels)
  - JSON payload decode/pretty patterns
  - global state (`_CP_STORE`, `_RUN_SUBMISSION_CACHE`)
- [ ] map each concept to existing “other” implementations (if present), and identify drift/contradiction
- [ ] document current fallback semantics for:
  - unknown `run_mode`
  - malformed/missing JSON
  - absent artifacts / schema versions
  - missing `_CP_STORE` / missing cached submission bindings

**Verification:**
- [ ] for each concept, current SSOT location and call path is explicitly recorded

**Exit Criteria:**
- no decision depends on an unstated assumption about normalization or storage/orchestration behavior

### Wave 2: Decision closure

**Purpose:**
- resolve SSOT boundaries and normalization contracts

**Steps:**
- [ ] lock SSOT choices (Decisions section)
- [ ] define migration steps and compatibility rules for any behavior currently inconsistent
- [ ] define required tests/contracts

**Verification:**
- [ ] each drift/contradiction finding has a chosen remediation path and acceptance proof

**Exit Criteria:**
- design internally coherent and bounded to R1–R5

### Wave 3: Validation and approval readiness

**Purpose:**
- make proofs explicit for refactor safety

**Steps:**
- [ ] define invariant checklist for store selection, labeling, JSON contract enforcement, orchestration binding
- [ ] define evidence expectations (tests, inspections, diff checks, GitNexus checks)

**Verification:**
- [ ] validation plan provides concrete evidence artifacts for each acceptance claim

**Exit Criteria:**
- spec ready for approval and implementation planning handoff

## Design Decisions

### Decision: Remove shadow-import contradictions (R1)

- context: `src/fitcv_cp/app.py` imports `fitcv_cp.bq_store` symbols and `fitcv_cp.queue` symbols, then re-defines same-named functions locally (shadowing). This creates contradiction and ambiguity for readers/tooling.
- choice: enforce “no shadow-import” rule in `app.py`:
  - do not import names that will be redefined in-module
  - prefer importing modules (`import fitcv_cp.bq_store as bq_store_module`) or renaming imports explicitly when needed
- alternatives considered:
  - keep shadowing but add comments (rejected: does not remove ambiguity)
  - split wrappers into a separate module but keep imports (defer: higher scope; allowed in R2+ if needed)
- impact:
  - makes store/orchestration call paths unambiguous
  - reduces dead imports and accidental “wrong symbol” usage

### Decision: Introduce a RunStore façade object for store selection (R2)

- context: repeated `if _CP_STORE is not None: ... else: bq_store_module...` logic exists across many wrapper functions.
- choice: create a single façade instance used by all routes and helpers:
  - façade implements run-store interface (get/list/mutate/event append, etc.)
  - façade chooses backend once (ControlPlaneStore configured vs BigQuery module)
  - façade used by routes instead of scattered wrapper functions
- alternatives considered:
  - keep wrapper functions but centralize selector helper (acceptable fallback if façade requires too broad signature churn)
- impact:
  - symmetry: all store ops follow same pattern
  - invariance: store selection rules can be tested once

### Decision: Move run-mode normalization + labeling to SSOT helper (R3)

- context: `RUN_MODE_LABELS` appears in `src/fitcv_cp/app.py` and `src/fitcv_cp/run_artifact_contracts.py`, but normalization fallback differs (`.get(..., raw)` vs defaulting to `"run_all"`).
- choice: `src/fitcv_cp/run_artifact_contracts.py` is SSOT for:
  - `normalized_run_mode(value)`
  - `run_mode_label(value)`
  - (optional) any other run artifact label helpers that are used outside `app.py`
- alternatives considered:
  - make `app.py` SSOT (rejected: helper module already exists with better invariants)
- impact:
  - invariance: unknown run modes never leak raw strings to UI/artifacts
  - symmetry: labeling consistent across UI/download/persistence surfaces

### Decision: Centralize JSON decode/pretty + schema validation helpers (R4)

- context: `app.py` decodes JSON in many places with varying assumptions and error handling. Some payloads stamp schema versions; others do not enforce schema/version presence.
- choice: create shared helpers (location decision):
  - primary location: `src/fitcv_cp/run_artifact_contracts.py` (if scope remains run-artifact centric), OR
  - a new dedicated helper module under `src/fitcv_cp/` (if broader than artifacts).
  - helpers provide:
    - `decode_json_object_or_none(raw: str | None) -> dict[str, Any] | None` (and/or strict variants)
    - `pretty_json(raw: str) -> str` with stable formatting and safe failure mode
    - `require_schema_version(payload: dict, expected: str) -> None` (or returns bool + reason)
- alternatives considered:
  - keep ad-hoc loads/dumps (rejected: perpetuates hidden duplication and edge-case divergence)
- impact:
  - symmetry: all JSON surfaces share same safety behavior
  - invariance: schema-version enforcement becomes testable and consistent

### Decision: Replace `_RUN_SUBMISSION_CACHE` with bounded/explicit strategy (R5)

- context: module-level dict cache risks unbounded growth and unclear lifecycle across app instances.
- choice: pick one bounded strategy:
  - (preferred) remove cache and derive binding deterministically from persisted run fields; OR
  - keep cache but enforce TTL/max-size with explicit eviction and metrics/logging.
- alternatives considered:
  - “do nothing” (rejected: edge-case + operational risk)
- impact:
  - reduces hidden state coupling, improves testability, reduces risk in long-running server

## Invariants

- No intended user-visible behavior changes except where current behavior is contradictory/undefined; any change must be enumerated and validated.
- Store-selection invariance:
  - if ControlPlaneStore configured, store ops consistently use it
  - otherwise, store ops consistently use BigQuery store module
  - no mixed backend usage for same request path unless explicitly designed
- Run-mode invariance:
  - unknown/invalid values normalize to canonical default (`"run_all"`)
  - label function never returns raw unknown identifiers
- Artifact contract invariance:
  - when a payload is claimed to have schema version X, schema version X is present and validated
  - JSON decode failures do not silently produce invalid artifacts
- Observability invariance:
  - existing observability events remain emitted for same runtime events (no regressions in event names/keys without explicit decision)
- Orchestration invariance:
  - continue/submit flows preserve their current external behavior (queue job id binding, backend routing) while eliminating unsafe hidden state.

## Acceptance Criteria

- R1:
  - `src/fitcv_cp/app.py` contains no imports that are later shadowed by same-named local definitions.
  - Store/orchestration call paths are unambiguous by inspection.
- R2:
  - all run-store operations used by routes go through exactly one façade (or one central selector) rather than repeated `if _CP_STORE`.
  - façade behavior has unit tests covering both backends.
- R3:
  - `RUN_MODE_LABELS` exists in exactly one SSOT location.
  - UI label output for unknown run_mode is consistent across all surfaces.
- R4:
  - JSON decode/pretty/schema validation helpers exist and are used across `app.py` for all relevant surfaces.
  - schema-version-tagged payloads are validated (at least presence + exact match).
- R5:
  - no unbounded global cache remains for run submission binding.
  - selected strategy (deterministic binding or bounded cache) is tested and documented.

## Non-Goals

- No changes to BigQuery schema, persistence formats, or external API routes unless required to resolve contradictions (if required, must be split into a separate spec).
- No large-scale module re-architecture beyond `fitcv_cp` control-plane surfaces (no refactor of `fitcv.pipeline` internals here).
- No UI redesign; only contract/structure refactor and invariance enforcement.

## Risks and Mitigations

- Risk: high blast radius for `get_run`-adjacent changes (many callers).
  - Mitigation: stage changes behind façade introduction with targeted tests; avoid renames until GitNexus impact confirms low/known scope.
- Risk: behavior change for unknown `run_mode` (raw string vs default).
  - Mitigation: treat as explicit decision; validate with golden outputs for representative runs.
- Risk: stricter JSON validation breaks tolerant paths that previously “worked by accident”.
  - Mitigation: start with non-fatal validation (warn + degrade) where required; add strictness only after confirming artifacts include versions.
- Risk: removing cache changes orchestration binding behavior.
  - Mitigation: specify binding invariants; create flow-level tests; consider intermediate bounded cache before full removal.

## Migration and Safety Controls

- Backward compatibility:
  - keep accepting legacy JSON payloads where schema version missing, but surface structured warnings and mark payload as “legacy/no-version” unless spec explicitly upgrades payload writers first.
  - preserve existing route shapes and response fields.
- Deprecation/removal path:
  - introduce new helper functions first; keep old ad-hoc patterns temporarily with TODO + lint/test enforcement window.
  - for `_RUN_SUBMISSION_CACHE`, add bounded behavior first (TTL/max size) before removal if deterministic binding requires broader changes.
- Rollback/containment:
  - keep refactor as isolated commits grouped by R1→R5 ordering.
  - ensure each step has green tests so revert can be surgical.

## Validation Plan

- proof target: R1 removes shadow-import contradictions in `src/fitcv_cp/app.py`
  - method: inspection + lints (if configured) + import-time smoke test
  - evidence: `python -c "import fitcv_cp.app"` succeeds; code inspection shows no shadow-import patterns
- proof target: store-selection invariance preserved (R2)
  - method: unit tests for façade/selector with `_CP_STORE` set/unset (or injected)
  - evidence: test output + coverage on both backend branches
- proof target: run-mode label normalization invariant (R3)
  - method: unit tests for `normalized_run_mode()` / `run_mode_label()`
  - evidence: test cases include unknown values, `None`, and known values
- proof target: JSON decode/pretty/schema-version validation consistency (R4)
  - method: unit tests for helpers; endpoint smoke tests for representative download/admin endpoints
  - evidence: tests show consistent failures/warnings and stable pretty formatting
- proof target: orchestration binding safe and bounded (R5)
  - method: flow-level test for submit→continue; memory-bound check if cache retained
  - evidence: tests + assertion that cache bounded or absent; no regression in emitted observability events
- proof target: refactor does not expand unintended scope
  - method: GitNexus `detect_changes` + git diff review
  - evidence: GitNexus report shows only expected symbols/files; no surprise affected processes

## Completion Criteria

1. All Acceptance Criteria satisfied for R1–R5.
2. Validation Plan evidence collected and stored as:
   - test output logs (CI/local) and/or referenced test files,
   - GitNexus `detect_changes` report for final diff.
3. Any deferred items are explicitly moved into follow-up spec(s) or dropped with rationale.
