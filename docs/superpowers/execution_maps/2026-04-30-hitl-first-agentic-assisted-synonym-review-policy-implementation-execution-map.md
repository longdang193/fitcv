---
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: workstream-agentic-synonym-management
map_type: implementation_execution
threads:
  - workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
  - workstream-operator-control-plane.operator-control-plane-agentic-review-actions
specs:
  - docs/superpowers/specs/2026-04-30-hitl-first-agentic-assisted-synonym-review-policy-spec.md
---

# HITL-First Agentic-Assisted Synonym Review Policy Implementation Execution Map

## Scope

Implement HITL-first synonym governance with:

- advisory agent recommendations
- operator batch review actions
- strict audit trail capture
- backward-compatible single-action flows

## Waves

### Wave 1: Batch Action Backend

Primary files:

- `src/fitcv_cp/app.py`
- `tests/test_fitcv_cp/test_app.py`

Deliverables:

- `POST /admin/runs/{run_id}/synonym-proposals/batch-action`
- per-item transition validation
- partial success response (`applied/skipped/failed`)
- compatibility with existing single-proposal action route

### Wave 2: Run Detail Batch Review UI

Primary files:

- `src/fitcv_cp/templates/run_detail.html`
- `src/fitcv_cp/app.py`
- `tests/test_fitcv_cp/test_app.py`

Deliverables:

- row-level action selectors
- optional “apply recommendation to selected/all filtered”
- one submit button for batch commit
- clear pending/resolved row states

### Wave 3: Recommendation + Audit Enrichment

Primary files:

- `src/fitcv_cp/worker_job.py`
- `src/fitcv_cp/app.py`
- `tests/test_fitcv_cp/test_worker_job.py`
- `tests/test_fitcv_cp/test_app.py`

Deliverables:

- advisory recommendation fields per proposal
- review action records include recommendation snapshot at decision time
- exports include enriched audit details

### Wave 4: Docs + Contract Gate

Primary files:

- `docs/observability.md`
- `docs/api.md`

Deliverables:

- operator flow documentation for batch HITL review
- API payload/response documentation for batch actions
- validator-facing docs alignment complete

### Wave 5: Verification + Live Proof

Primary files:

- tests + runtime execution only

Deliverables:

- targeted tests green
- `validate_repo_contracts.py --fast` green
- one live run demonstrating batch review and artifact/audit output

## Dependency Order

Hard order:

1. Wave 1 before Wave 2
2. Wave 2 before Wave 3
3. Wave 3 before Wave 4
4. Wave 4 before Wave 5

Reason:

- backend transition/audit semantics must be stable before UI and docs finalize.

## Verification Path

```powershell
python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym and batch"
python -m pytest tests/test_fitcv_cp/test_worker_job.py -k "synonym and audit"
python scripts/validate_repo_contracts.py --fast
```

## First Buildable Subset

Wave 1 + Wave 2:

- batch backend + batch UI without recommendation enrichment

This delivers immediate operator time savings while keeping HITL guarantees.
