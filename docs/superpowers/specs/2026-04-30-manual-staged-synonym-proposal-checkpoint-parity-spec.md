---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - docs/observability.md
  - docs/api.md
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - trigger_run_management
  - inspection_debugging
  - settings_system
related_stages:
  - enrich
  - rule_filter
---

# Manual-Staged Synonym Proposal Checkpoint Parity

## Summary

Ensure Stage by Stage runs at the `enrich -> rule_filter` checkpoint have the
same synonym-proposal lifecycle as Run All:

- proposal generation
- proposal persistence
- run-detail review/approve actions

Today, operators can upload overlay YAML at this checkpoint but often cannot
review/approve generated synonym proposals because proposal artifacts are not
always present yet.

## Problem

Current operator experience is split:

- Stage by Stage shows **Synonym Overlay** upload controls after `enrich`.
- Synonym proposal review card appears only when `synonym_proposals_json`
  exists with proposals.
- In manual-staged checkpoint flow, mapping suggestions / proposal payloads can
  be missing at this moment, so no review card appears.

This creates mode drift and undermines HITL consistency.

## Goals

- guarantee proposal artifact availability at the manual enrich checkpoint
- guarantee review/approve UI visibility when proposals exist
- keep proposal approval semantics bounded and auditable
- keep backward compatibility for runs without proposal artifacts

## Non-Goals

- no redesign of synonym confidence/ranking heuristics
- no auto-approval policy changes
- no cross-run/global promotion workflow changes

## Proposed Contract

## 1) Checkpoint Artifact Parity

At manual-staged `awaiting_continue` after `enrich` with `next_stage=rule_filter`,
the worker must persist:

- `mapping-suggestions.json` snapshot (if suggestions exist)
- `synonym-proposals.json` snapshot derived from mapping suggestions
- `synonym-proposals-trace.json` trace payload

If no suggestions exist, persist explicit `not_applicable` status payloads so UI
can truthfully explain absence.

## 2) Run-Detail Review Surface Parity

Run detail must show a **Synonym Proposal Review** card whenever proposal
payload has proposal records, independent of run mode.

Required controls per proposal:

- `Approve`
- `Defer`
- `Reject`

Each action writes review history and emits run event audit.

## 3) Approval Semantics

Approving a proposal remains run-scoped overlay behavior:

- update run effective settings snapshot with approved aliases
- preserve proposal IDs under runtime metadata
- do not mutate shared default synonym taxonomy

## 4) Truthful Empty States

When proposals are absent:

- show explicit “no proposals generated” signal only if checkpoint artifacts say
  `not_applicable`
- do not imply hidden errors

## Acceptance Criteria

1. For a manual-staged run paused after `enrich`, `synonym-proposals.json` is
   present in run artifact exports.
2. For the same run, run detail shows proposal review controls when proposals
   exist.
3. Proposal approve/defer/reject actions update proposal status and audit trail.
4. Run All and Stage by Stage expose equivalent proposal review behavior.
5. Existing overlay YAML upload flow remains functional.

## Validation Plan

- unit tests for worker checkpoint persistence of mapping/proposal artifacts in
  manual-staged flow
- app tests for run-detail proposal card visibility in manual-staged checkpoint
- app tests for approve/defer/reject route behavior and run-scoped overlay
  updates
- validator pass:
  - `python scripts/validate_repo_contracts.py --fast`

## Risks

- duplicate proposal generation if checkpoint persistence runs multiple times
- stale proposal payloads if continue/retry flow skips refresh logic

Mitigation:

- idempotent proposal identity seeds
- overwrite-with-latest checkpoint snapshot semantics plus trace summary

## Rollout

1. patch worker checkpoint persistence for manual-staged enrich pause
2. patch run-detail rendering + action routes
3. add/adjust tests
4. run fast validator suite
5. verify with one live manual-staged run and artifact inspection
