---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
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

# Approved Synonym Overlay Merge Policy Clarification

## Summary

Clarify and enforce that approved synonym exports and promotion flows are overlay/delta surfaces, not full replacements of the global canonical synonym map.

## Problem

Operators are unclear whether `approved-synonym-proposals.yaml` is:

1. only run-approved pairs, or
2. a full canonical file replacement.

This ambiguity creates risk of accidental overwrite and policy drift.

## Goals

- define one unambiguous contract for approved synonym export and promotion
- enforce append/overlay behavior in UI copy, API docs, and runtime behavior
- make conflict/override behavior explicit
- preserve global canonical source-of-truth guarantees

## Non-Goals

- no redesign of proposal generation
- no change to HITL decision model
- no automatic global writes without explicit promote action

## Source Of Truth

- global canonical policy file:
  - `config/taxonomy/skill_synonyms.yaml`
- run-scoped approved set:
  - `pipeline_runs.synonym_proposals_json` (approved statuses only)
- approved overlay export:
  - generated per run, delta-only representation

## Canonical Contract

## 1) Export Semantics

`GET /admin/runs/{run_id}/approved-synonym-proposals.yaml` must export only run-approved pairs.

It must never serialize the entire global canonical synonym map.

## 2) Promote Semantics

`promote-to-global` is a merge/overlay operation:

- base = current `config/taxonomy/skill_synonyms.yaml`
- delta = selected approved run-scoped pairs
- result = base plus delta, where delta keys override existing canonical values for the same alias

This is an explicit append/overlay commit, not a replace-with-export operation.

## 3) Conflict Policy

For alias collisions:

- if alias not present in base: append alias->canonical
- if alias exists with same canonical: no-op
- if alias exists with different canonical: treat as explicit override and surface in preview diff

Preview must include counts:

- `new_aliases`
- `unchanged_aliases`
- `overridden_aliases`

## 4) UI Copy Contract

Run detail and promote preview text must explicitly state:

- export is run-scoped approved delta only
- global file is updated via merge/overlay
- promotion does not blindly replace the canonical file

Promote selection UX must include:

- a `Select All` control for eligible approved rows
- clear selected-count feedback
- ability to deselect individual rows before preview/commit

## 5) Observability Contract

Promote summary/audit payload should record:

- selected proposal count
- applied/new count
- unchanged count
- overridden count
- failed count
- target file path

## API/Doc Updates

Update `docs/api.md` endpoint description for:

- `/admin/runs/{run_id}/approved-synonym-proposals.yaml`
- promote preview/commit endpoints

Add explicit behavior language:

- "delta-only export"
- "merge/overlay commit"
- "override on alias key collision"

Update `docs/usage.md` and `docs/observability.md` operator notes with the same contract.

## Acceptance Criteria

1. Approved overlay export contains only run-approved pairs.
2. Promote preview clearly distinguishes add/no-op/override rows.
3. Promote commit merges into global canonical file without replacing full file with run export.
4. UI wording and API docs explicitly describe delta/merge semantics.
5. Promote observability summary includes add/no-op/override counts.
6. Promote flow supports `Select All` + per-row deselect with accurate selected-count behavior.

## Validation Plan

- app tests:
  - approved export excludes non-approved and excludes unrelated global entries
  - promote preview classification coverage (`new`, `unchanged`, `override`)
  - promote commit preserves unrelated existing global mappings
  - promote commit overrides only selected colliding aliases
- doc checks:
  - `python scripts/validate_repo_contracts.py --fast`

## Rollout

1. contract wording updates (UI + docs)
2. promote selection UX (`Select All` + selected-count)
3. preview classification hardening
4. merge semantics tests
5. observability count exposure
