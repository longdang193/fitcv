---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: docs-lifecycle-alignment-plan
parent_thread: workstream-agentic-observability.agentic-observability-shared-trace-standard
parent_spec: docs/superpowers/specs/2026-05-02-observability-evidence-control-docs-alignment-spec.md
targets:
  - docs/api.md
  - docs/architecture.md
  - docs/component_boundaries.md
  - docs/configuration.md
  - docs/fitcv-control-plane-setup.md
  - docs/FitCV-pipeline.md
  - docs/observability.md
  - docs/pipeline.md
  - docs/setup.md
  - docs/usage.md
related_features:
  - inspection_debugging
  - trigger_run_management
  - settings_system
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Bring scoped root documentation into strict alignment with shipped implementation and intended outcomes so docs remain accurate, navigable, and maintainable under repository lifecycle governance.

## Key Deliverables

### Deliverable 1: Evidence-backed drift audit across scoped docs

Produce claim-level drift audit for all scoped docs against current source code, runtime config, scripts, and tests, with each claim classified as `accurate`, `stale`, `ambiguous`, or `unsupported`.

### Deliverable 2: Scoped documentation reconciliation without feature invention

Apply bounded updates to scoped docs only, removing speculative language, correcting stale commands/routes/env variables, and marking unresolved behavior as explicit pending items with blockers.

### Deliverable 3: Cross-doc consistency and navigation normalization

Normalize terminology, section framing, and cross-links across scoped docs so operator and developer flows are coherent and non-contradictory.

### Deliverable 4: Validation-backed closeout report

Deliver closeout summary including modified files, evidence map, pending gaps, risk assumptions, and verification command outputs required by repository governance.

## Task/Wave Breakdown

### Task 1: Build drift-audit evidence matrix

**Purpose:**
- Establish implementation-truth baseline before editing docs.

**Files:**
- Inspect: `docs/api.md`
- Inspect: `docs/architecture.md`
- Inspect: `docs/component_boundaries.md`
- Inspect: `docs/configuration.md`
- Inspect: `docs/fitcv-control-plane-setup.md`
- Inspect: `docs/FitCV-pipeline.md`
- Inspect: `docs/observability.md`
- Inspect: `docs/pipeline.md`
- Inspect: `docs/setup.md`
- Inspect: `docs/usage.md`
- Inspect: `src/fitcv/**`
- Inspect: `src/fitcv_cp/**`
- Inspect: `configs/**`
- Inspect: `scripts/**`
- Inspect: `tests/**`
- Inspect: `docs/intent/**`
- Modify: `docs/superpowers/plans/audit/2026-05-11-docs-lifecycle-drift-audit.md`
- Verify: `docs/superpowers/plans/audit/2026-05-11-docs-lifecycle-drift-audit.md`

**Preconditions:**
- Scope fixed to listed 10 docs.
- Validator baseline currently green.

**Steps:**
- [x] Extract major claims and operational snippets from each scoped doc.
- [x] Map each claim/snippet to concrete implementation evidence path(s).
- [x] Classify drift status per claim (`accurate`/`stale`/`ambiguous`/`unsupported`).
- [x] Record unresolved claims with blockers and required follow-up owner.

**Verification:**
- [x] Audit file exists and includes all 10 scoped docs.
- [x] Every flagged claim includes at least one evidence path.

**Exit Criteria:**
- Audit matrix complete and usable as sole input for patch pass.

### Task 2: Reconcile docs to implementation truth

**Purpose:**
- Patch scoped docs to remove drift while preserving repo documentation contracts.

**Files:**
- Modify: `docs/api.md`
- Modify: `docs/architecture.md`
- Modify: `docs/component_boundaries.md`
- Modify: `docs/configuration.md`
- Modify: `docs/fitcv-control-plane-setup.md`
- Modify: `docs/FitCV-pipeline.md`
- Modify: `docs/observability.md`
- Modify: `docs/pipeline.md`
- Modify: `docs/setup.md`
- Modify: `docs/usage.md`
- Verify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv_cp/worker_job.py`
- Verify: `src/fitcv_cp/backend_runtime.py`
- Verify: `scripts/check_outbox_replay_health.py`

**Preconditions:**
- Task 1 audit matrix approved for execution.

**Steps:**
- [x] Update stale/incorrect route, command, env var, and file-path claims.
- [x] Remove or reframe speculative text not backed by shipped behavior.
- [x] Add explicit `Pending` callouts where behavior cannot be verified in-source.
- [x] Keep README out of scope unless explicitly requested.

**Verification:**
- [x] All modified claims trace to implementation evidence from Task 1.
- [x] No newly added behavior lacks source/test/config proof.

**Exit Criteria:**
- Scoped docs no longer conflict with implementation-truth audit.

### Task 3: Normalize cross-doc terminology and link integrity

**Purpose:**
- Ensure docs read as single coherent suite, not isolated pages.

**Files:**
- Modify: `docs/api.md`
- Modify: `docs/architecture.md`
- Modify: `docs/configuration.md`
- Modify: `docs/observability.md`
- Modify: `docs/pipeline.md`
- Modify: `docs/setup.md`
- Modify: `docs/usage.md`
- Verify: `docs/FitCV-pipeline.md`

**Preconditions:**
- Task 2 updates applied.

**Steps:**
- [x] Align canonical terms (run truth, stage-owned artifacts, operator surfaces, execution modes).
- [x] Resolve duplicate/conflicting explanations between `pipeline.md` and `FitCV-pipeline.md`.
- [x] Validate cross-links and related-doc pointers remain accurate.
- [x] Ensure command snippets match current runtime entrypoints and paths.

**Verification:**
- [x] Spot-check each doc `Related Docs` section for valid targets.
- [x] Confirm no contradictory definitions across scoped pages.

**Exit Criteria:**
- Cross-doc navigation and terminology consistent across scoped suite.

### Task 4: Run validators and produce closeout evidence

**Purpose:**
- Prove lifecycle compliance and preserve validator-green status.

**Files:**
- Verify: `scripts/sync_architecture_docs.py`
- Verify: `scripts/validate_repo_contracts.py`
- Modify: `docs/superpowers/plans/audit/2026-05-11-docs-lifecycle-closeout-report.md`

**Preconditions:**
- Tasks 1-3 complete.

**Steps:**
- [x] Run architecture sync/check commands if generated surfaces impacted.
- [x] Run repository contract validation fast path.
- [x] Capture command outputs and map to deliverables.
- [x] Write closeout report with edited files, unresolved gaps, and risk assumptions.

**Verification:**
- [x] `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- [x] `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- Validation commands pass and closeout report complete.

## Verification

- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`
- `.\.venv\Scripts\python.exe -m pytest -q`

## Completion Criteria

1. All Key Deliverables satisfied with evidence.
2. Scoped docs updated to implementation-truth without feature invention.
3. Validator suite returns green after changes.
4. Pending gaps documented with explicit blockers and follow-up owners.

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
