---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: config-ssot-overlap-dead-settings-remediation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-05-16-19-40-config-ssot-overlap-dead-settings-remediation-spec.md
targets:
  - config/env.yaml
  - config/env.private.yaml
  - config/live_smoke.yaml
  - config/runtime/control_plane.yaml
  - src/fitcv/config.py
  - docs/configuration.md
  - tests/test_config.py
related_features:
  - settings_system
  - cv_system
  - admin_control_plane_core
related_stages:
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Execute bounded config-SSOT remediation so overlapping ownership and dead config surfaces are removed or explicitly compatibility-scoped, while preserving runtime behavior and live-run stability.

## Key Deliverables

### Deliverable 1: `env.yaml` ownership collisions removed

`config/env.yaml` contains no duplicate top-level declarations and no in-scope canonical-owner overlaps except explicit compatibility keys retained by plan decision.

### Deliverable 2: Dead/misleading config surfaces resolved

Unused config entries/files in scope are removed or reclassified with explicit rationale and no false runtime configurability.

### Deliverable 3: Compatibility boundary codified

Retained legacy compatibility keys are explicitly bounded in loader/docs with clear deprecation conditions and no silent bidirectional drift expansion.

### Deliverable 4: Runtime and validator evidence green

Static validators, targeted config tests, and live-run artifacts confirm non-regressive behavior after SSOT cleanup.

## Task/Wave Breakdown

### Task 1: Lock in-scope ownership matrix and removal decisions

**Purpose:**
- freeze exact keep/remove/reclassify decisions before editing config contracts

**Files:**
- Inspect: `config/env.yaml`
- Inspect: `config/env.private.yaml`
- Inspect: `config/live_smoke.yaml`
- Inspect: `config/runtime/control_plane.yaml`
- Inspect: `src/fitcv/config.py`
- Modify: `docs/configuration.md`

**Preconditions:**
- parent spec approved for bounded SSOT remediation

**Steps:**
- [ ] Step 1: produce explicit decision table for each in-scope overlap/dead candidate (keep as compat, remove, or reclassify).
- [ ] Step 2: document canonical owner per key-family in `docs/configuration.md`.
- [ ] Step 3: confirm decisions align with current runtime consumers in `src/`.

**Verification:**
- [ ] `rg -n "cv_acceptance_policy|max_cv_jobs|cv_analysis_min_score|required_skill_overlap_min|preferred_skill_overlap_min|language_match_min|summary_quality_min|seniority_ladder|application_statuses|cv_analysis_semantic_alignment|live_smoke|env.private" config src docs/configuration.md`

**Exit Criteria:**
- each in-scope key/file has one explicit lifecycle decision and owner

### Task 2: Remove duplicate/overlap declarations and dead routing surface

**Purpose:**
- apply minimal config contract edits that eliminate proven SSOT violations

**Files:**
- Modify: `config/env.yaml`
- Modify: `config/runtime/control_plane.yaml`
- Modify: `config/live_smoke.yaml` (remove or reclassify per Task 1 decision)
- Modify: `config/env.private.yaml` (remove or reclassify per Task 1 decision)
- Modify: `src/fitcv/config.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: resolve duplicate `cv_acceptance_policy` declaration in `config/env.yaml` to single canonical block.
- [ ] Step 2: drain in-scope canonical-owner overlaps from `config/env.yaml` while preserving explicit compatibility keys required by active consumers.
- [ ] Step 3: remove `control_plane.model_routing.parts.cv_analysis_semantic_alignment` unless consumer implementation is intentionally added in scope.
- [ ] Step 4: apply Task 1 decision for `live_smoke.yaml` and `env.private.yaml` (retire or explicit non-runtime classification).
- [ ] Step 5: tighten `src/fitcv/config.py` overlap/compatibility handling to prevent silent re-expansion of removed overlaps.

**Verification:**
- [ ] `rg -n "^cv_acceptance_policy:" config/env.yaml`
- [ ] `rg -n "cv_analysis_semantic_alignment" config/runtime/control_plane.yaml src`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- duplicate key declaration removed and dead routing/config surfaces resolved per decisions

### Task 3: Add/adjust regression coverage for config contract invariants

**Purpose:**
- prevent SSOT regression and document compatibility boundary in tests

**Files:**
- Modify: `tests/test_config.py`
- Modify: `src/fitcv/config.py` (only if needed for testable invariant hooks)

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] Step 1: add test for duplicate-key/overlap handling outcome on `env` load path.
- [ ] Step 2: add test that removed dead routing key is not required by runtime loaders.
- [ ] Step 3: add test that retained compatibility keys still map to active runtime consumers where intentionally preserved.

**Verification:**
- [ ] `pytest -q tests/test_config.py -k "ssot or overlap or compatibility or control_plane"`

**Exit Criteria:**
- config SSOT boundary and compatibility rules are enforced by tests

### Task 4: Runtime proof and closeout evidence

**Purpose:**
- prove runtime behavior remains stable after config cleanup

**Files:**
- Modify: `docs/configuration.md`
- Modify: `docs/superpowers/execution_context_packs/<lane-id>/latest.md` (if execution lane in use)
- Inspect: `logs/fitcv-run-*/settings-used.json`
- Inspect: `logs/fitcv-run-*/cv_analysis.json`

**Preconditions:**
- Task 3 complete

**Steps:**
- [ ] Step 1: run bounded live run (`run_all`) and capture run id, status, checkpoint status.
- [ ] Step 2: confirm settings/artifact evidence shows expected config behavior and no failed/degraded stage markers.
- [ ] Step 3: record evidence + residual risk disposition in plan/context artifacts.

**Verification:**
- [ ] `python scripts/hooks/run_validator.py --fast`
- [ ] live-run evidence: `GET /runs/{run_id}`, `GET /admin/runs/{run_id}/settings-used.json`, `GET /admin/runs/{run_id}/stage-artifacts/cv_analysis.json`

**Exit Criteria:**
- validator and runtime evidence support deliverable-level closure

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `pytest -q tests/test_config.py -k "ssot or overlap or compatibility or control_plane"`
- `py scripts/validate_planning_lifecycle.py --strict`
- `py scripts/validate_checkpoint_packs.py`
- live-run artifact checks for updated config behavior (`settings-used.json`, `cv_analysis.json`)

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
