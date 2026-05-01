---
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: workstream-agentic-synonym-management
map_type: implementation_execution
threads:
  - workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
specs:
  - docs/superpowers/specs/2026-05-01-synonym-review-action-performance-and-approved-overlay-export-spec.md
---

# Synonym Review Action Performance And Approved Overlay Export Implementation Map

## Wave 1: Single Action Fast Path
- Refactor single action to run-scoped lookup/persistence path
- Remove cross-run `list_runs(limit=500)` dependency for run-scoped route
- Add/adjust tests

## Wave 2: True Batch Apply
- Apply selected actions in memory for one run payload
- Consolidate persistence writes and summary response
- Add/adjust tests for applied/skipped/failed reporting

## Wave 3: Approved Overlay YAML Export
- Add `GET /admin/runs/{run_id}/approved-synonym-proposals.yaml`
- Show Run Exports link when available
- Add/adjust endpoint/UI tests

## Wave 4: Docs + Validation
- Update `docs/api.md` and `docs/observability.md`
- Run:
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym and (batch or overlay or export)"`
  - `python scripts/validate_repo_contracts.py --fast`
