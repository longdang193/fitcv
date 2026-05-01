---
layer: change
artifact_type: implementation_execution_map
status: proposed
source_spec:
  - docs/superpowers/specs/2026-05-01-apply-approved-to-run-and-synonym-review-drift-remediation-spec.md
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - docs/api.md
  - docs/usage.md
  - docs/observability.md
  - tests/test_fitcv_cp/test_app.py
---

# Apply Approved To Run And Synonym Review Drift Remediation — Implementation Execution Map

## Execution Goal

Close review/runtime drift by adding an explicit `Apply Approved to This Run` action and align UI/artifacts/docs with real synonym application semantics.

## Wave 1 — Backend Apply-To-Run Endpoint

## Scope

- add run-scoped apply-approved endpoint
- update run effective settings snapshot deterministically

## Tasks

1. Add `POST /admin/runs/{run_id}/synonym-proposals/apply-approved-to-run`.
2. Gather currently approved proposals (`approved_for_run_overlay`).
3. Build overlay YAML and apply into run `effective_settings_json` via runtime overlay path.
4. Persist run effective settings update and emit event payload with counts/actor.
5. Add terminal-run/precondition guards and summary redirect params.

## Exit Criteria

- endpoint updates current run snapshot and returns deterministic summaries.

## Wave 2 — Run Detail UX

## Scope

- add explicit apply-to-run action
- keep promote/global flow separate

## Tasks

1. Add `Apply Approved to This Run` button/form in synonym review card.
2. Add helper copy clarifying downstream-stage-only effect.
3. Add apply summary banner (`applied/skipped/failed`).
4. Ensure promote controls remain independent and unchanged in semantics.

## Exit Criteria

- operator can explicitly apply approved pairs to run snapshot without promoting global.

## Wave 3 — Artifact And Messaging Alignment

## Scope

- make run bundle and run detail messaging reflect actual behavior

## Tasks

1. Ensure artifact bundle includes:
   - `approved-synonym-proposals.yaml` when approved pairs exist
   - `synonym-overlay-used.yaml` when run overlay snapshot exists
2. Ensure manifest missing/applicability states are consistent with conditional artifacts.
3. Keep/confirm reranker-blocked 0-CV messaging truth path in run detail.

## Exit Criteria

- bundle and run-detail outputs are behaviorally accurate and debuggable.

## Wave 4 — Docs Alignment

## Scope

- align operator and API docs to three distinct actions

## Tasks

1. Update `docs/api.md`:
   - add apply-to-run endpoint
   - clarify review vs apply-to-run vs promote-to-global
2. Update `docs/usage.md` flow ordering.
3. Update `docs/observability.md` with apply-to-run traces/summaries.

## Exit Criteria

- docs no longer imply approval alone mutates run snapshot.

## Wave 5 — Verification And Regression

## Scope

- harden with tests and checks

## Tasks

1. Add/extend tests for:
   - apply-to-run endpoint snapshot mutation
   - no global mutation from apply-to-run
   - terminal/precondition guard paths
   - artifact bundle inclusion for synonym YAML artifacts
2. Run targeted synonym + bundle tests.
3. Run `validate_repo_contracts --fast`.

## Exit Criteria

- tests pass and no new contract failures introduced.

## Verification Commands

```powershell
python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym or bundle or reranker_blocked"
python scripts/validate_repo_contracts.py --fast
```
