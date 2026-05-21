---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: cross-stage-reuse-policy-implementation
parent_workstream: none
parent_spec: docs/superpowers/specs/2026-05-21-15-17-cross-stage-reuse-policy-spec.md
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - config/runtime/pipeline.yaml
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - none
related_stages:
  - enrich
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Implement stage-symmetric reuse controls with SSOT policy ownership, normalized reuse status semantics, and migration-safe diagnostics so existing behavior remains stable while enabling controlled CV-generation reuse.

## Key Deliverables

### Canonical Reuse Policy Surface

Introduce reusable per-stage policy keys (enabled/policy/max_age and safeguards where needed) in runtime config and settings schema, with defaults preserving current effective behavior and CV-generation reuse default-disabled.

### Reuse Diagnostics and Metrics Symmetry

Deliver normalized reuse status vocabulary and per-stage reused/fresh accounting across artifacts and run detail, with backward-compatible handling for existing late-stage payload consumers.

### Verified Rollout Safety

Ship contract and integration tests proving toggle behavior, diagnostics shape, and no-regression defaults before any optional CV-generation reuse enablement.

## Task/Wave Breakdown

### Task 1: Baseline reuse inventory and policy matrix

**Purpose:**
- lock implementation against current real behavior and avoid accidental semantics drift

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/pipeline_stage_runner.py`
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv_cp/app.py`
- Verify: `docs/superpowers/specs/2026-05-21-15-17-cross-stage-reuse-policy-spec.md`

**Preconditions:**
- parent spec approved for execution planning
- GitNexus index treated as advisory if stale

**Steps:**
- [ ] Capture stage-by-stage baseline matrix: stage, current reuse source, status field, configurability, evidence payload surface.
- [ ] Confirm default-preservation targets for existing stages (enrich/embedding/query/ranking/cv_analysis).
- [ ] Confirm CV-generation gap boundaries and required safeguards from spec.

**Verification:**
- [ ] Inspection notes map every targeted stage to exact source symbols and expected default behavior.

**Exit Criteria:**
- no implementation task proceeds with ambiguous baseline semantics.

### Task 2: Add canonical reuse policy keys and settings schema wiring

**Purpose:**
- establish SSOT policy surface before behavior rewiring

**Files:**
- Modify: `config/runtime/pipeline.yaml`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/settings.html` (if needed for IA grouping parity)
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- Task 1 baseline matrix complete

**Steps:**
- [ ] Add canonical reuse namespace entries for targeted stages:
  - `reuse.enrich.*`
  - `reuse.shortlist_embeddings.*`
  - `reuse.shortlist_query_embedding.*`
  - `reuse.ranking_ai_score.*`
  - `reuse.cv_analysis.*`
  - `reuse.cv_generation.*`
- [ ] Define defaults preserving current behavior for existing reuse-enabled paths.
- [ ] Set `reuse.cv_generation.enabled=false` by default.
- [ ] Register schema metadata (stage mapping, risk, labels, defaults, sources).
- [ ] Ensure settings read/write path resolves new keys without breaking existing controls.

**Verification:**
- [ ] `pytest -q tests/test_fitcv_cp/test_settings_schema.py`
- [ ] Settings page renders canonical keys without duplicate alias drift.

**Exit Criteria:**
- reuse policy keys are schema-valid, visible, and default-safe.

### Task 3: Normalize reuse status vocabulary and compatibility mapping

**Purpose:**
- create invariant reuse-status semantics for telemetry, artifacts, and UI

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_runner.py`
- Modify: `src/fitcv/pipeline_observability.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] Introduce canonical status mapping utility for stage reuse outcomes.
- [ ] Map existing stage-specific statuses into canonical vocabulary where emitted to diagnostics/summary paths.
- [ ] Preserve backward compatibility for legacy status consumers with explicit fallback mapping.
- [ ] Ensure “reuse disabled” and “fingerprint mismatch” reasons are emitted when applicable.

**Verification:**
- [ ] `pytest -q tests/test_pipeline.py -k "reuse_status or reused_exact_match or late_stage_reuse"`

**Exit Criteria:**
- diagnostics emit consistent status semantics without breaking legacy assertions.

### Task 4: Extend reuse diagnostics envelope beyond late-stage-only payload

**Purpose:**
- unify evidence shape for cross-stage reuse auditing

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [ ] Define versioned reuse diagnostics envelope (v2) with stage-specific sections.
- [ ] Keep read compatibility for existing `late_stage_reuse_v1` payloads.
- [ ] Wire run summary and run-detail metric extraction to v2-first, v1-fallback parsing.
- [ ] Ensure reused/fresh totals remain deterministic across envelopes.

**Verification:**
- [ ] `pytest -q tests/test_fitcv_cp/test_worker_job.py -k "late_stage_reuse_snapshots"`
- [ ] `pytest -q tests/test_fitcv_cp/test_app.py -k "late_stage_reuse or run_health"`

**Exit Criteria:**
- run diagnostics support both old and new payloads with stable metrics.

### Task 5: Implement CV-generation reuse path behind default-disabled guard

**Purpose:**
- close stage symmetry gap safely without changing default runtime behavior

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_runner.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Tasks 2-4 complete
- canonical fingerprint inputs defined and documented

**Steps:**
- [ ] Add CV-generation input fingerprint composition using required invariants (job/profile/model/preset/sections/template-version).
- [ ] Add reuse lookup/write path for CV-generation records in diagnostics envelope.
- [ ] Enforce policy gate: if `reuse.cv_generation.enabled=false`, always fresh generate.
- [ ] Emit canonical generation reuse status and reason codes.

**Verification:**
- [ ] `pytest -q tests/test_pipeline.py -k "cv_generation and reuse"`
- [ ] Negative-path test proves fresh compute when generation reuse disabled.

**Exit Criteria:**
- CV-generation reuse logic exists, is policy-gated, and inert by default.

### Task 6: UI and reporting parity for cross-stage reuse controls/metrics

**Purpose:**
- expose new controls and results clearly for operators

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 4 complete (metrics/parsing stable)

**Steps:**
- [ ] Group new reuse controls in settings IA with stage-appropriate risk/help copy.
- [ ] Extend run-detail reuse metrics rendering to include configured stage reuse rows.
- [ ] Ensure copy clarifies configured policy vs runtime effective outcomes.

**Verification:**
- [ ] `pytest -q tests/test_fitcv_cp/test_app.py -k "settings or reuse metrics or run_detail"`

**Exit Criteria:**
- operator can configure reuse policies and observe outcomes consistently.

### Task 7: End-to-end regression and rollout readiness gate

**Purpose:**
- prove no regressions and readiness for implementation handoff/merge

**Files:**
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `scripts/validate_repo_contracts.py`

**Preconditions:**
- Tasks 1-6 complete

**Steps:**
- [ ] Run targeted suites for reuse behavior and UI.
- [ ] Run repo contract validation in fast mode.
- [ ] Capture before/after behavior summary for defaults and toggle impacts.
- [ ] Record rollback strategy (disable new reuse toggles, rely on fresh compute paths).

**Verification:**
- [ ] `pytest -q tests/test_pipeline.py -k "reuse or cv_analysis or cv_generation"`
- [ ] `pytest -q tests/test_fitcv_cp/test_worker_job.py -k "reuse"`
- [ ] `pytest -q tests/test_fitcv_cp/test_app.py -k "reuse or settings"`
- [ ] `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- all targeted verification passes and rollout defaults remain behavior-preserving.

## Verification

- `pytest -q tests/test_fitcv_cp/test_settings_schema.py`
- `pytest -q tests/test_pipeline.py -k "reuse or cv_analysis or cv_generation"`
- `pytest -q tests/test_fitcv_cp/test_worker_job.py -k "reuse"`
- `pytest -q tests/test_fitcv_cp/test_app.py -k "reuse or settings or run_detail"`
- `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`

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
