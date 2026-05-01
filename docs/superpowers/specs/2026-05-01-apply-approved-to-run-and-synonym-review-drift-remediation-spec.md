---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/worker_job.py
  - docs/api.md
  - docs/usage.md
  - docs/observability.md
  - tests/test_fitcv_cp/test_app.py
related_features:
  - trigger_run_management
  - inspection_debugging
  - settings_system
related_stages:
  - enrich
  - rule_filter
---

# Apply Approved To This Run And Synonym Review Drift Remediation

## Summary

Add an explicit `Apply Approved to This Run` action that materializes run-approved synonym proposals into the current run’s effective synonym overlay, and resolve contract drift between review-state semantics and runtime-application semantics.

## Problem

Current behavior has a real operator drift:

1. review actions (`approve_for_run_overlay`) update proposal status only
2. they do **not** update run effective settings overlay
3. later stages in the same run may therefore not consume newly approved pairs unless a separate overlay upload or global promotion occurs

This conflicts with operator expectations implied by review language.

## Drift Findings (Scope Of Remediation)

## Drift A — Review vs runtime application

- status `approved_for_run_overlay` does not guarantee run-time application in current run.

## Drift B — UI affordance ambiguity

- review panel supports approve/reject/defer but lacks explicit action to apply approved set into current run snapshot.

## Drift C — Artifact clarity

- run artifact bundle does not always make it obvious which synonym YAML was actually used vs merely reviewed.

## Goals

- make run-local application explicit and deterministic via one action
- preserve existing HITL review and global promotion boundaries
- provide clear observability of what was applied to the run and when
- align API/docs/UI wording with actual behavior

## Non-Goals

- no automatic global promotion
- no implicit auto-apply on every approve click
- no mutation of past completed stages

## Contract

## 1) New Action: Apply Approved To This Run

Add run-scoped endpoint:

- `POST /admin/runs/{run_id}/synonym-proposals/apply-approved-to-run`

Behavior:

- collects proposals currently in `approved_for_run_overlay`
- builds deterministic overlay YAML from approved pairs
- merges this approved overlay into the run’s `effective_settings_json`
  using existing runtime overlay mechanism
- records overlay source metadata:
  - `run_overlay_source = "proposal_review_apply"`
  - `run_overlay_filename = "approved-synonym-proposals.yaml"`
  - `run_overlay_entry_count`
  - `run_overlay_yaml`
  - `run_overlay_uploaded_at`
- emits run event with counts and actor/note

Preconditions:

- run exists
- run not terminal (`succeeded`, `failed`, `cancelled` blocked)
- at least one approved proposal exists

Result:

- redirect to run detail with summary query params:
  - `synonym_apply_to_run_applied`
  - `synonym_apply_to_run_skipped`
  - `synonym_apply_to_run_failed`

## 2) Stage Applicability Rule

The action applies to downstream stages only.

- if run is paused before `rule_filter` (manual staged after enrich), this is the primary intended path
- if run is already beyond downstream synonym-dependent stages, action may still persist snapshot but must show warning that it will not retroactively change completed outputs

## 3) UI Contract

Synonym Proposal Review card must include:

- `Apply Approved to This Run` button
- concise helper text:
  - "Applies approved pairs to this run’s downstream stages."
- summary banner for apply action counts

Promote-to-global remains separate and explicit.

## 4) Checkbox Visibility Contract (already in-flight)

- rows already globally promoted must not show promote checkbox
- select-all/clear-selection controls only show when promote-eligible rows exist

## 5) Artifact And Trace Contract

`Download All Artifacts` should include when available:

- `approved-synonym-proposals.yaml` (approved delta)
- `synonym-overlay-used.yaml` (run snapshot actually used)

Manifest must mark these as:

- `present` when included
- `not_applicable` when no overlay exists
- `missing` only when expected but unavailable

## 6) Messaging Contract For 0 CV Cases

When `cvs_generated = 0` and all ranked rows are `ranked_blocked_by_reranker_fit`, run detail must report gating truth (blocked before CV generation), not generic "did not produce valid CV output."

## 7) Documentation Alignment

Update docs to clearly distinguish:

- review status change
- apply-to-run snapshot mutation
- promote-to-global canonical mutation

## Acceptance Criteria

1. Operator can click `Apply Approved to This Run` and run effective settings snapshot is updated with approved overlay.
2. Later stages in the same run use the applied overlay when stage order allows.
3. Global canonical file remains unchanged unless promote-to-global is confirmed.
4. Run detail and docs explicitly separate review, apply-to-run, and promote-to-global semantics.
5. Artifact bundle includes approved and used synonym YAML artifacts when available.
6. 0-CV messaging reflects reranker-blocked truth when applicable.

## Validation Plan

- app tests:
  - apply-approved endpoint updates `effective_settings_json`
  - apply-approved summary query params
  - terminal-run guard behavior
  - no-global-mutation on apply-to-run
  - artifact bundle includes synonym YAMLs when available
  - reranker-blocked 0-CV message path
- integration smoke:
  - stage-by-stage run paused after enrich
  - approve proposals
  - apply approved to run
  - continue to rule_filter and verify settings-used / overlay snapshot
- contract checks:
  - `python scripts/validate_repo_contracts.py --fast`

## Rollout

1. backend apply-approved endpoint + event payload
2. run detail button + summary banner
3. artifact/manifest alignment
4. docs alignment
5. regression + smoke verification
