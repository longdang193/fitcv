---
layer: change
artifact_type: execution_map
status: proposed
source_spec:
  - docs/superpowers/specs/2026-05-01-promote-selection-visibility-and-global-synonym-export-spec.md
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
threads:
  - workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
specs:
  - docs/superpowers/specs/2026-05-01-promote-selection-visibility-and-global-synonym-export-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/synonym_promote_preview.html
  - docs/api.md
  - docs/usage.md
  - docs/observability.md
  - tests/test_fitcv_cp/test_app.py
map_type: implementation_execution
parent_workstream: workstream-agentic-synonym-management
---
# Promote Selection Visibility And Global Synonym Export — Implementation Execution Map

## Execution Goal

Implement context-aware promote controls and provide a first-class global synonym YAML export surface.

## Wave 1 — Backend Route

## Scope

- add global export endpoint for canonical synonym map

## Tasks

1. Add `GET /admin/synonyms/global.yaml`.
2. Return canonical YAML from `config/taxonomy/skill_synonyms.yaml`.
3. Set `Content-Disposition` filename `fitcv-global-skill-synonyms.yaml`.

## Exit Criteria

- endpoint serves full canonical YAML successfully.

## Wave 2 — Run Detail UX

## Scope

- conditional visibility for promote selection controls
- post-promote global download affordance

## Tasks

1. Show `Select All`, `Clear Selection`, and `Selected: N` only when at least one promote-eligible row exists.
2. Show helper text when zero eligible rows: `No approved rows available for promotion yet.`
3. In promote summary banner (`synonym_promote_applied` present), add `Download Global Synonyms YAML` link to `/admin/synonyms/global.yaml`.

## Exit Criteria

- controls only appear in promote-eligible context and global download is visible post-promote.

## Wave 3 — Docs Alignment

## Scope

- update API and operator docs

## Tasks

1. Update `docs/api.md` with new global export endpoint and semantics.
2. Update `docs/usage.md` and `docs/observability.md` to distinguish:
   - run-approved delta export
   - global canonical export

## Exit Criteria

- docs reflect endpoint and source-of-truth split.

## Wave 4 — Tests And Verification

## Scope

- add regression coverage and run checks

## Tasks

1. Add app tests for:
   - global YAML endpoint success + shape
   - promote controls hidden when no eligible rows
   - promote controls shown when eligible rows
   - post-promote summary includes global download link
2. Run targeted synonym tests.
3. Run `validate_repo_contracts --fast`.

## Exit Criteria

- targeted tests pass and no new validator failures are introduced by this change.

## Verification Commands

```powershell
python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym and (promote or overlay or export or review)"
python scripts/validate_repo_contracts.py --fast
```
