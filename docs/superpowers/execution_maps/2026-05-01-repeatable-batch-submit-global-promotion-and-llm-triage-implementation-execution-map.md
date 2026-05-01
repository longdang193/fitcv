---
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: workstream-agentic-synonym-management
map_type: implementation_execution
threads:
  - workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
specs:
  - docs/superpowers/specs/2026-05-01-repeatable-batch-submit-global-promotion-and-llm-triage-spec.md
---

# Repeatable Batch Submit, Promote-To-Global, And LLM Triage Implementation Map

## Wave 1: Repeatable Batch Submit Reliability
- Ensure repeated submits on one run are supported without stale state.
- Return deterministic batch summary (`applied`, `skipped`, `failed`) for each submit.
- Add/adjust tests for second/third submit behavior and resolved-row skips.

## Wave 2: Promote-To-Global (Preview + Commit)
- Add preview route for selected approved run proposals with diff categories (`add`, `update`, `conflict`, `skip`).
- Add explicit commit route to promote selected proposals to global synonym policy with metadata/audit.
- Add/adjust tests for preview rendering, conflict handling, and promotion persistence.

## Wave 3: LLM-Assisted Triage (Advisory)
- Add recommendation fields on run-scoped pending proposals (`recommended_action`, confidence, rationale, risk flags).
- Render recommendation details in review table and add "apply recommendations to selected" prefill helper.
- Ensure no automatic status mutation; operator submit remains mandatory (HITL).
- Add/adjust tests for visibility, helper prefill, and manual override.

## Wave 4: Docs + Validation
- Update operator-facing docs:
  - `docs/api.md` (new endpoints and payload contracts)
  - `docs/observability.md` (review/promotion/triage traces and audit fields)
- Run verification:
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym and (batch or promote or triage or overlay or export)"`
  - `python scripts/validate_repo_contracts.py --fast`
