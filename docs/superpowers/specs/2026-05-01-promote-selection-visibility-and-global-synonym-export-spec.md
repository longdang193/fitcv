---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/synonym_promote_preview.html
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

# Promote Selection Visibility And Global Synonym Export

## Summary

Refine synonym promotion UX so selection controls appear only in the promote context, and add a first-class download surface for the global canonical synonym map after promotion.

## Problem

Two operator gaps remain:

1. `Select All` / `Clear Selection` can appear as generic controls even when no promote-eligible rows exist, creating UX confusion.
2. After confirm promote, operators lack an explicit UI/API download action for the updated global canonical synonym list.

## Goals

- make promote selection controls context-aware and unambiguous
- add a canonical global synonym YAML download endpoint and UI link
- keep source-of-truth semantics explicit (global canonical file vs run-scoped overlay)

## Non-Goals

- no change to triage recommendation behavior
- no change to run-scoped approved overlay export semantics
- no automatic promote action

## Contract

## 1) Promote Control Visibility

In run detail synonym review:

- `Select All`, `Clear Selection`, and selected-count should render only when at least one row is promote-eligible (`approved_for_run_overlay`).
- when zero eligible rows exist, hide these controls and show concise helper text:
  - "No approved rows available for promotion yet."
- controls are scoped to promote-checkbox selection only; they do not affect batch approve/defer/reject controls.

## 2) Global Synonym Export Surface

Add endpoint:

- `GET /admin/synonyms/global.yaml`

Behavior:

- returns current canonical global map from `config/taxonomy/skill_synonyms.yaml`
- response media type `text/yaml`
- filename: `fitcv-global-skill-synonyms.yaml`

This endpoint exports the full canonical global list, not run-scoped deltas.

## 3) Run Detail Post-Promote UX

When promote commit succeeds (`synonym_promote_applied` present):

- show a direct link/button in the summary area:
  - `Download Global Synonyms YAML`
  - points to `GET /admin/synonyms/global.yaml`

## 4) Source-Of-Truth Messaging

UI/docs must keep this distinction explicit:

- `approved-synonym-proposals.yaml` = run-approved delta-only
- `global.yaml` endpoint = full canonical global map
- promote commit = merge/overlay into canonical global map

## Acceptance Criteria

1. Promote selection controls render only when promote-eligible rows exist.
2. Operators can download the full global canonical synonym YAML from UI/API.
3. Run detail shows post-promote global download action.
4. Docs clearly distinguish run overlay export vs global canonical export.

## Validation Plan

- app tests:
  - controls hidden when no eligible promote rows
  - controls shown when eligible rows exist
  - global export endpoint returns YAML with canonical root key
  - run detail includes global download link after promote summary
- doc checks:
  - `python scripts/validate_repo_contracts.py --fast`

## Rollout

1. backend endpoint for global YAML export
2. run detail conditional control visibility
3. post-promote download link in summary
4. docs and tests alignment
