---
layer: operating_system
artifact_type: spec
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

# Starter Helper Surface Adoption

## Summary

Adopt the next missing starter helper surfaces so JOB-PROJECT can move closer to
the raw `project-OS-starter` wrapper flow after the sync-wrapper convergence
phase.

This phase should import and wire up the helper scripts that the latest starter
wrapper already expects:

- `scripts/format_contract_yaml.py`
- `scripts/audit_architecture_linkage.py`

and their matching tests where they truthfully apply:

- `tests/test_format_contract_yaml.py`
- `tests/test_architecture_linkage_audit.py`
- `tests/test_setup_hooks.py`

## Problem

The repo now uses a starter-style wrapper for
`scripts/sync_architecture_docs.py`, but it still carries documented drift
because the starter helper surfaces are missing locally.

Current state:

- `scripts/validate_adoption_shape.py` is exact-match aligned with starter
- `scripts/sync_architecture_docs.py` is now wrapper-shaped
- `tools/docs/generate_architecture_metadata.py` exists locally as the repo's
  generation helper
- starter helper scripts and tests still have not been adopted

That means the wrapper still needs a reduced local step set instead of the
fuller starter command flow.

## Goals

- Import `scripts/format_contract_yaml.py` from starter and adapt it only where
  repo-local paths or contracts truly differ.
- Import `scripts/audit_architecture_linkage.py` from starter and adapt it only
  where repo-local paths or metadata rules truly differ.
- Import the matching starter tests that prove those helper surfaces.
- Extend `scripts/sync_architecture_docs.py` toward the fuller starter step
  sequence once those helpers are available locally.
- Narrow the remaining `scripts/sync_architecture_docs.py` divergence rationale
  in `repo_config/adoption-mode.yaml`.

## Non-Goals

- Do not rework the core local generator again in this phase.
- Do not force raw starter assumptions like `configs/` if this repo still
  truthfully uses `config/`.
- Do not broaden adoption-shape rules beyond the current starter source of
  truth.
- Do not change feature content or ownership metadata except where helper
  adoption requires generated refresh.

## Target State

### Sync Wrapper

After this phase, `scripts/sync_architecture_docs.py` should be able to include
the same helper-step categories as starter:

- adoption-shape validation
- generator validation/check
- architecture linkage audit
- contract YAML formatting check
- focused architecture metadata tests

### Repo-Local Adaptation Boundary

Remaining local substitutions should be narrow:

- local generator path remains `tools/docs/generate_architecture_metadata.py`
- local runtime config root remains `config/`
- any helper adaptation should be path/layout based, not independent logic drift

## Acceptance Criteria

- `scripts/format_contract_yaml.py` exists locally and passes its local tests
- `scripts/audit_architecture_linkage.py` exists locally and passes its local tests
- matching helper tests are present and green where applicable
- `scripts/sync_architecture_docs.py` uses the adopted helpers in its step flow
- `repo_config/adoption-mode.yaml` records a smaller and more truthful wrapper
  divergence rationale than before
- the following all pass:
  - `python scripts/sync_architecture_docs.py`
  - `python scripts/sync_architecture_docs.py --check`
  - `python scripts/validate_adoption_shape.py`
  - `python scripts/validate_repo_contracts.py --fast`
  - `.venv\Scripts\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py tests/test_validate_repo_contracts.py tests/test_format_contract_yaml.py tests/test_architecture_linkage_audit.py tests/test_setup_hooks.py -q`

## Risks

- Helper adoption may reveal additional repo-layout drift that was previously
  hidden by the narrower local wrapper step set.
- Raw starter helper imports may assume file layouts or fixture names that need
  careful repo-local adaptation.
- If the helper tests are imported too literally, they may assert starter-only
  paths instead of truthful JOB-PROJECT paths.

## Suggested Next Step

Turn this spec into a focused implementation plan that adopts the helper
surfaces one by one in this order:

1. `format_contract_yaml.py`
2. `audit_architecture_linkage.py`
3. matching tests
4. wrapper step expansion
5. divergence-ledger narrowing
