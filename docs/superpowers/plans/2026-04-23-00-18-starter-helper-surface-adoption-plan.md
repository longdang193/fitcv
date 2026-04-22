---
layer: operating_system
artifact_type: plan
status: proposed
parent_workstream: none
targets:
  - scripts/format_contract_yaml.py
  - scripts/audit_architecture_linkage.py
  - scripts/sync_architecture_docs.py
  - tests/test_format_contract_yaml.py
  - tests/test_architecture_linkage_audit.py
  - tests/test_setup_hooks.py
  - repo_config/adoption-mode.yaml
  - docs/operating_system/feature-lifecycle.md
  - docs/operating_system/doc-system-lifecycle.md
related_features: []
related_stages: []
---

# Starter Helper Surface Adoption Implementation Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/archive/specs/2026-04-23-00-10-starter-helper-surface-adoption-spec.md`  
**Type:** modify  
**Plan Layer:** operating_system  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Adopt the missing starter helper surfaces so `scripts/sync_architecture_docs.py` can move closer to the raw starter wrapper flow while keeping only narrow truthful JOB-PROJECT substitutions such as `config/` and the local generator path.

## Triage

Layer: `operating_system`  
Feature type: `MODIFY`  
Summary: Import `format_contract_yaml.py` and `audit_architecture_linkage.py` plus their matching tests, then expand the local wrapper step flow to use them and narrow the remaining divergence rationale.  
Reasoning: The wrapper-model convergence is already complete enough to benefit from the next starter helper adoption step. These helper surfaces exist upstream and should reduce the remaining wrapper drift without reopening the core generator migration.  
Invariants:

- `scripts/validate_adoption_shape.py` must remain exact-match aligned with starter.
- `tools/docs/generate_architecture_metadata.py` remains the local generator path in this phase.
- `config/` remains the truthful runtime config root in this repo.
- imported helper logic should stay as close to starter as possible, with only path/layout substitutions where needed.
- validation must stay green after each helper adoption batch.

Dependencies:

- `docs/superpowers/archive/specs/2026-04-23-00-10-starter-helper-surface-adoption-spec.md`
- latest local `project-OS-starter` helper surfaces
- completed wrapper-convergence commit `a62d04f`

Affected stages:

- none

Affected features:

- none

Primary lens: `shared-surface convergence`

Affected docs:

- feature_source: `none`
- feature_yaml: `none`
- feature_lineage: `regenerated only if helper adoption changes generation checks`
- feature_history: `none`
- stage_source: `none`
- stage_contract: `none`
- feature_docs: `none`
- cross_cutting_docs:
  - `docs/operating_system/feature-lifecycle.md`
  - `docs/operating_system/doc-system-lifecycle.md`
- readme: `none`
- generated:
  - `docs/features/*/lineage.generated.yaml`
  - `docs/generated/capability_lineage.yaml`

Generated refresh required: `possible`  
Capability IDs: `none`  
Invariant IDs: `none`  
Spec needed: `no`  
Plan needed: `yes`

## File Map

Files to modify:

- `scripts/format_contract_yaml.py`
- `scripts/audit_architecture_linkage.py`
- `scripts/sync_architecture_docs.py`
- `tests/test_format_contract_yaml.py`
- `tests/test_architecture_linkage_audit.py`
- `tests/test_setup_hooks.py`
- `repo_config/adoption-mode.yaml`
- `docs/operating_system/feature-lifecycle.md`
- `docs/operating_system/doc-system-lifecycle.md`

Files to inspect closely during implementation:

- `../project-OS-starter/scripts/format_contract_yaml.py`
- `../project-OS-starter/scripts/audit_architecture_linkage.py`
- `../project-OS-starter/tests/test_format_contract_yaml.py`
- `../project-OS-starter/tests/test_architecture_linkage_audit.py`
- `../project-OS-starter/tests/test_setup_hooks.py`

## Task 1: Adopt `format_contract_yaml.py`

**Files:**
- Add or modify: `scripts/format_contract_yaml.py`

- [ ] Step 1: Import the starter helper script into the repo.
- [ ] Step 2: Review whether any path handling needs repo-local adaptation.
- [ ] Step 3: Keep the imported surface starter-close unless a truthful local difference is required.
- [ ] Step 4: Confirm generated files are still skipped and human-authored YAML targets stay correct for this repo.

## Task 2: Adopt `audit_architecture_linkage.py`

**Files:**
- Add or modify: `scripts/audit_architecture_linkage.py`

- [ ] Step 1: Import the starter audit helper into the repo.
- [ ] Step 2: Keep the helper aligned to the local generator path `tools/docs/generate_architecture_metadata.py`.
- [ ] Step 3: Confirm the audit still truthfully enforces no `manual_refs` in managed feature sources.
- [ ] Step 4: Keep any adaptation limited to repo-local paths or fixture shape.

## Task 3: Adopt Matching Helper Tests

**Files:**
- Add or modify: `tests/test_format_contract_yaml.py`
- Add or modify: `tests/test_architecture_linkage_audit.py`
- Add or modify: `tests/test_setup_hooks.py`

- [ ] Step 1: Import starter helper tests where they truthfully apply.
- [ ] Step 2: Adapt starter-only paths like `configs/` to this repo's truthful `config/` layout where needed.
- [ ] Step 3: Avoid preserving any old local assertions that conflict with the starter helper model.
- [ ] Step 4: Keep tests focused on the helper surfaces, not broad repo-wide behavior duplication.

## Task 4: Expand The Sync Wrapper Step Flow

**Files:**
- Modify: `scripts/sync_architecture_docs.py`

- [ ] Step 1: Add `scripts/audit_architecture_linkage.py` into the wrapper step list.
- [ ] Step 2: Add `scripts/format_contract_yaml.py --check` into the wrapper step list.
- [ ] Step 3: Expand the focused pytest step to include the adopted helper tests.
- [ ] Step 4: Keep the wrapper starter-like while preserving the local generator path.

## Task 5: Narrow Drift Ledger And Doc Language

**Files:**
- Modify: `repo_config/adoption-mode.yaml`
- Modify: `docs/operating_system/feature-lifecycle.md`
- Modify: `docs/operating_system/doc-system-lifecycle.md`

- [ ] Step 1: Narrow the `scripts/sync_architecture_docs.py` divergence rationale again after helper adoption.
- [ ] Step 2: Update docs so they describe the fuller wrapper flow with the newly adopted helpers.
- [ ] Step 3: Keep only the remaining truthful local differences visible in the docs and drift ledger.

## Task 6: Refresh And Verify

- [ ] Step 1: Run `python scripts/sync_architecture_docs.py`.
- [ ] Step 2: Run `python scripts/sync_architecture_docs.py --check`.
- [ ] Step 3: Run `python scripts/validate_adoption_shape.py`.
- [ ] Step 4: Run `python scripts/validate_repo_contracts.py --fast`.
- [ ] Step 5: Run starter-side validation:
  - `python ..\\project-OS-starter\\scripts\\validate_adoption_shape.py --repo-root <JOB-PROJECT>`
- [ ] Step 6: Run `.venv\\Scripts\\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py tests/test_validate_repo_contracts.py tests/test_format_contract_yaml.py tests/test_architecture_linkage_audit.py tests/test_setup_hooks.py -q`.
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
- generated docs refreshed? `if helper adoption changes outputs`
