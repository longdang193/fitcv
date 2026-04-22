# Project Adoption Migration Guide

Use this guide when this repo advances or cleans up its `managed_architecture_metadata` Mode B adoption.

This repo already uses managed feature folders, generated contracts, and evidence-oriented lineage. The remaining migration and cleanup work should therefore focus on keeping the repo aligned with the newer `project-OS-starter` shared surfaces instead of reintroducing legacy compatibility patterns.

## Core Rule

Do not partially migrate architecture metadata.

When the repo updates generator behavior, validation rules, generated discovery outputs, or source metadata requirements, update the whole Mode B surface together:

- source rules in `docs/features/*/feature.source.yaml`
- generator behavior in `scripts/sync_architecture_docs.py`
- validator rules in `scripts/validate_adoption_shape.py`
- generated outputs under `docs/features/*/`, `docs/stages/*`, and `docs/generated/`
- repo-facing docs and publication config that point at generated outputs

## Current Mode B Contract

The current repo contract is:

- `feature.source.yaml` is the human-owned semantic source
- `<feature_id>.yaml` is the generated assembled feature contract
- `lineage.generated.yaml` is the canonical feature-local evidence surface
- `history.md` remains human-owned feature context
- `docs/generated/architecture_dag.yaml` is the canonical generated topology/discovery surface
- `docs/generated/capability_lineage.yaml` is the canonical repo-wide generated capability-evidence summary

The older generated discovery family is retired:

- `docs/generated/features_index.yaml`
- `docs/generated/feature_dependency_graph.yaml`
- `docs/generated/feature_capabilities_index.yaml`
- `docs/generated/feature_overview.md`
- `docs/generated/features_by_status.yaml`
- `docs/generated/stages_index.yaml`
- `docs/generated/stage_overview.md`

These legacy outputs should not be recreated by hand or treated as valid steady-state artifacts.

## Function-Level Capability Metadata

Python files may now carry bounded function-level capability ownership through function docstrings:

```python
def build_cv() -> None:
    """
    @capability cv_system.structured-cv-generation
    """
```

Rules:

- use `@capability <feature_id.capability-slug>` only on canonical behavior-owning functions or methods
- keep file-level `@meta capabilities:` for broad owning surfaces where that is still the most truthful representation
- prefer one canonical capability owner where possible instead of scattering the same capability across many helpers
- use `@proves <capability_id>` only in tests that directly verify the named behavior

## Stage Participation Rules

Every managed feature source must declare `stage_participation`.

Allowed shapes:

- a non-empty list for stage-aware features
- an explicit `[]` for intentionally stage-agnostic repo surfaces

Each entry should include:

- `stage_id`
- `role`
- `capability_ids`

Validation expects:

- `stage_id` to exist in `docs/stages/*.source.yaml`
- `capability_ids` to belong to the same feature
- missing `stage_participation` to be treated as drift, not silently normalized

## Generated Text Normalization

Generated contracts should emit clean prose values:

- trailing whitespace removed
- trailing blank lines removed
- ordinary single-paragraph values kept readable without noisy multiline artifacts

If a generated contract looks wrong, patch the source or generator. Do not manually edit the generated contract.

## Cleanup Workflow

When shared-surface cleanup is needed:

1. diff current repo-control surfaces against the latest `project-OS-starter`
2. update the repo-local generator and validator together
3. backfill any newly required source fields before turning on stricter validation
4. refresh generated outputs
5. update repo-facing docs and publication config if generated paths changed
6. record the starter review in `repo_config/adoption-mode.yaml`

## Required Verification

```powershell
python scripts/sync_architecture_docs.py
python scripts/sync_architecture_docs.py --check
python scripts/validate_adoption_shape.py
.venv\Scripts\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py
git diff --check
```
