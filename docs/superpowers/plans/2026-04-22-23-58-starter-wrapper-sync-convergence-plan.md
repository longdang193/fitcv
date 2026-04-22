---
layer: operating_system
artifact_type: plan
status: proposed
parent_workstream: none
targets:
  - scripts/sync_architecture_docs.py
  - scripts/validate_repo_contracts.py
  - repo_config/adoption-mode.yaml
  - docs/operating_system/feature-lifecycle.md
  - docs/operating_system/doc-system-lifecycle.md
  - AGENTS.md
  - tests/test_validate_adoption_shape.py
  - tests/test_validate_repo_contracts.py
related_features: []
related_stages: []
---

# Starter Wrapper Sync Convergence Implementation Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-23-55-starter-wrapper-sync-convergence-spec.md`  
**Type:** modify  
**Plan Layer:** operating_system  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Migrate JOB-PROJECT toward the current `project-OS-starter` wrapper model for architecture sync and repo-contract orchestration, while keeping only narrow truthful repo-local adaptations for layout differences like `config/` and any still-missing starter helper surfaces.

## Triage

Layer: `operating_system`  
Feature type: `MODIFY`  
Summary: Replace the current large local sync control surface with a starter-style wrapper approach, then tighten the recorded customization boundary around the truly repo-specific parts.  
Reasoning: The repo now passes the exact starter `validate_adoption_shape.py`, but the larger sync/orchestration architecture still drifts in a high-maintenance way. The right next step is to converge implementation shape, not just keep documenting divergence.  
Invariants:

- `scripts/validate_adoption_shape.py` must remain exact-match aligned with starter throughout this phase.
- repo-local adaptations must stay narrow, explicit, and truthful.
- no raw copy should force incorrect starter assumptions like `configs/` if the repo still truthfully uses `config/`.
- validation must stay green after each convergence batch.
- docs must describe the actual implemented wrapper model, not a target state that has not landed yet.

Dependencies:

- `docs/superpowers/archive/specs/2026-04-22-23-55-starter-wrapper-sync-convergence-spec.md`
- latest local `project-OS-starter` baseline `a5d2d85b3174cde84f90df26642385b429e3c194`
- current repo-local `scripts/sync_architecture_docs.py`
- current repo-local `scripts/validate_repo_contracts.py`

Affected stages:

- none

Affected features:

- none

Primary lens: `shared-surface convergence`

Affected docs:

- feature_source: `none`
- feature_yaml: `none`
- feature_lineage: `regenerated only if wrapper migration changes generation flow`
- feature_history: `none`
- stage_source: `none`
- stage_contract: `none`
- feature_docs: `none`
- cross_cutting_docs:
  - `docs/operating_system/feature-lifecycle.md`
  - `docs/operating_system/doc-system-lifecycle.md`
  - `AGENTS.md`
- readme: `none`
- generated:
  - `docs/features/*/lineage.generated.yaml`
  - `docs/generated/capability_lineage.yaml`

Generated refresh required: `likely`  
Capability IDs: `none`  
Invariant IDs: `none`  
Spec needed: `no`  
Plan needed: `yes`

## File Map

Files to modify:

- `scripts/sync_architecture_docs.py`
- `scripts/validate_repo_contracts.py`
- `repo_config/adoption-mode.yaml`
- `docs/operating_system/feature-lifecycle.md`
- `docs/operating_system/doc-system-lifecycle.md`
- `AGENTS.md`
- `tests/test_validate_adoption_shape.py`
- `tests/test_validate_repo_contracts.py`

Files to inspect closely during implementation:

- `../project-OS-starter/scripts/sync_architecture_docs.py`
- `../project-OS-starter/scripts/validate_repo_contracts.py`
- `../project-OS-starter/docs/operating_system/feature-lifecycle.md`
- `../project-OS-starter/docs/operating_system/doc-system-lifecycle.md`
- `../project-OS-starter/AGENTS.md`

Generated outputs to refresh if the migrated wrapper changes generation behavior:

- `docs/features/*/lineage.generated.yaml`
- `docs/generated/capability_lineage.yaml`

## Task 1: Inventory Starter Wrapper Dependencies

**Files:**
- Inspect: `../project-OS-starter/scripts/sync_architecture_docs.py`
- Inspect: `../project-OS-starter/scripts/validate_repo_contracts.py`
- Inspect: repo-local wrapper and generator surfaces

- [ ] Step 1: Identify which starter wrapper dependencies exist in JOB-PROJECT already.
- [ ] Step 2: Identify which starter helper paths do not exist and would break a raw copy, for example:
  - `tools/docs/generate_architecture_metadata.py`
  - `scripts/format_contract_yaml.py`
  - `scripts/audit_architecture_linkage.py`
  - any starter-only validator/test file names
- [ ] Step 3: Write down the minimum substitution map from starter assumptions to JOB-PROJECT truths:
  - `configs/` versus `config/`
  - local generator entrypoint
  - local validator/test paths
- [ ] Step 4: Confirm that the exact starter `validate_adoption_shape.py` remains untouched.

## Task 2: Converge `scripts/sync_architecture_docs.py` To A Thin Wrapper

**Files:**
- Modify: `scripts/sync_architecture_docs.py`

- [ ] Step 1: Replace the current monolithic control flow with a starter-style wrapper structure:
  - parser
  - step builder
  - subprocess runner
  - check versus write mode handling
- [ ] Step 2: Keep only the smallest truthful repo-local substitutions needed for JOB-PROJECT.
- [ ] Step 3: If local generation logic must remain custom, move it behind the wrapper boundary instead of leaving it inline in the wrapper.
- [ ] Step 4: Preserve current repo outputs and pass/fail behavior while shrinking structural drift from starter.
- [ ] Step 5: Re-run generation and confirm produced outputs remain valid.

## Task 3: Tighten `scripts/validate_repo_contracts.py`

**Files:**
- Modify: `scripts/validate_repo_contracts.py`

- [ ] Step 1: Re-review starter orchestration shape and align local flow as closely as possible.
- [ ] Step 2: Keep only necessary substitutions for:
  - local adoption-shape validator entrypoint
  - local history-boundary policy
  - repo-local path names and tests
- [ ] Step 3: Remove any leftover custom branching that no longer reflects a real repo difference.
- [ ] Step 4: Keep `--fast` semantics aligned with starter intent.

## Task 4: Update Drift Ledger After Convergence

**Files:**
- Modify: `repo_config/adoption-mode.yaml`

- [ ] Step 1: Re-evaluate whether `scripts/sync_architecture_docs.py` still needs to be listed as a customization after wrapper convergence.
- [ ] Step 2: Re-evaluate whether `scripts/validate_repo_contracts.py` still needs the same rationale or a narrower one.
- [ ] Step 3: Narrow or remove divergence entries that are no longer true after implementation.
- [ ] Step 4: Keep only the remaining stable repo-specific differences.

## Task 5: Converge Docs And Generated Instructions

**Files:**
- Modify: `docs/operating_system/feature-lifecycle.md`
- Modify: `docs/operating_system/doc-system-lifecycle.md`
- Modify: `AGENTS.md`

- [ ] Step 1: Pull each file closer to the latest starter text by default.
- [ ] Step 2: Keep only repo-specific wording that still reflects implemented truth after wrapper convergence.
- [ ] Step 3: Ensure docs refer to the actual sync and validation entrypoints now in place.
- [ ] Step 4: Re-evaluate whether these files still need divergence entries, and narrow rationale if they do.

## Task 6: Refresh Tests For The Converged Wrapper Model

**Files:**
- Modify: `tests/test_validate_adoption_shape.py`
- Modify: `tests/test_validate_repo_contracts.py`

- [ ] Step 1: Keep validator tests aligned with the exact starter validator behavior.
- [ ] Step 2: Update repo-contract wrapper tests so they prove the converged orchestration shape rather than the older local control flow.
- [ ] Step 3: Add or adjust assertions only where wrapper migration materially changes expected invocation behavior.
- [ ] Step 4: Avoid preserving obsolete tests that assert old monolithic wrapper behavior.

## Task 7: Refresh And Verify

**Files:**
- Regenerate if needed: `docs/features/*/lineage.generated.yaml`
- Regenerate if needed: `docs/generated/capability_lineage.yaml`

- [ ] Step 1: Run `python scripts/sync_architecture_docs.py`.
- [ ] Step 2: Run `python scripts/sync_architecture_docs.py --check`.
- [ ] Step 3: Run `python scripts/validate_adoption_shape.py`.
- [ ] Step 4: Run `python scripts/validate_repo_contracts.py --fast`.
- [ ] Step 5: Run starter-side validation:
  - `python ..\\project-OS-starter\\scripts\\validate_adoption_shape.py --repo-root <JOB-PROJECT>`
- [ ] Step 6: Run `.venv\\Scripts\\python.exe -m pytest tests/test_validate_adoption_shape.py tests/test_validate_repo_contracts.py -q`.
- [ ] Step 7: Run `git diff --check`.

## Completion Checklist

- intent docs updated? `not needed`
- operating-system docs updated? `yes`
- stage sources updated? `not needed`
- stage contracts updated? `only if regeneration changes outputs`
- feature sources updated? `not needed`
- contract updated? `not needed`
- feature lineage updated? `if regenerated`
- feature history updated? `not needed`
- other feature-specific docs updated? `not needed`
- cross-cutting docs updated? `yes`
- agent memory updated or explicitly not needed? `not needed`
- README updated? `not needed`
- generated docs refreshed? `if wrapper migration changes generation outputs`
