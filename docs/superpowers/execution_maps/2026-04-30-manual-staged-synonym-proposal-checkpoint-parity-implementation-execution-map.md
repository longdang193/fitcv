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
  - docs/superpowers/specs/2026-04-30-manual-staged-synonym-proposal-checkpoint-parity-spec.md
---

# Manual-Staged Synonym Proposal Checkpoint Parity Implementation Execution Map

## Scope

Close mode drift so Stage by Stage at the `enrich -> rule_filter` checkpoint
supports full synonym HITL flow:

- proposal artifact generation/persistence
- review/approve/defer/reject in run detail
- truthful empty-state behavior

## Waves

### Wave 1: Manual Checkpoint Artifact Parity

Primary files:

- `src/fitcv_cp/worker_job.py`
- `tests/test_fitcv_cp/test_worker_job.py`

Deliverables:

- manual-staged checkpoint persists `mapping-suggestions.json` and
  `synonym-proposals.json` when suggestions exist
- `synonym-proposals-trace.json` emitted consistently
- explicit `not_applicable` status payloads when no suggestions exist

### Wave 2: Run Detail Proposal Review Parity

Primary files:

- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/run_detail.html`
- `tests/test_fitcv_cp/test_app.py`

Deliverables:

- run detail shows Synonym Proposal Review card for both `run_all` and
  `manual_staged` when proposals are present
- proposal actions (`approve`, `defer`, `reject`) available from run detail
- run-scoped action route audit and redirect behavior validated

### Wave 3: Docs + Observability Alignment

Primary files:

- `docs/observability.md`
- `docs/api.md`

Deliverables:

- checkpoint timing clarified: when proposals become available in each run mode
- run-detail/operator flow updated for proposal review actions
- export/debug guidance aligned with actual artifact lifecycle

### Wave 4: Contract Validation + Live Run Proof

Primary files:

- `scripts/validate_repo_contracts.py` (execution only)

Deliverables:

- targeted tests green
- fast contract validator green
- one live `manual_staged` run evidence captured showing checkpoint proposal
  review visibility

## Dependency Order

Hard order:

1. Wave 1 before Wave 2
2. Wave 2 before Wave 3
3. Wave 3 before Wave 4

Reason:

- UI review parity depends on proposal artifact availability at manual
  checkpoints.

## Verification Path

```powershell
python -m pytest tests/test_fitcv_cp/test_worker_job.py -k "manual_staged and synonym"
python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym and review"
python scripts/validate_repo_contracts.py --fast
```

Live proof:

1. trigger `manual_staged` run
2. pause at `awaiting_continue` after `enrich`
3. confirm run exports include `synonym-proposals.json`
4. confirm run detail shows proposal review actions

## First Buildable Subset

Wave 1 + Wave 2:

- checkpoint artifact parity
- operator review controls

This is the minimum subset that removes the current user-facing gap.
