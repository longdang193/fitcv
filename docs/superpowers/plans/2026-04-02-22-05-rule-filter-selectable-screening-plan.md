---
feature_type: modify
feature_name: rule-filter-selectable-screening
status: draft
summary: "Implement selectable blocking vs mark-only deterministic rule-filter behavior while preserving rule_filter stage ownership."
invariants:
  - "`rule_filter` remains the sole owner of deterministic rule evaluation."
  - "Each deterministic post-enrichment rule is evaluated at most once per job per run."
  - "Unselected rule filters never reject a job; they only emit deterministic marks."
  - "Ranking consumes rule_filter outcomes and does not re-evaluate rule_filter-owned checks."
---

# Rule Filter Selectable Screening Plan

## Triage

Feature type: MODIFY
Summary: Add admin-selectable blocking vs mark-only behavior for deterministic `rule_filter` checks while preserving stage ownership and inspection clarity.
Reasoning: The feature already exists as the deterministic post-enrichment screening stage; this change refines its runtime semantics, settings model, and inspection output rather than replacing the stage or moving ownership elsewhere.
Invariants:
- `rule_filter` remains the sole owner of deterministic rule evaluation.
- Existing blocking reason codes keep their current meaning.
- Unselected rule filters emit marks but do not reject jobs.
- Manual staged synonym overlays remain upstream input improvements only; they do not change rule ownership.
Dependencies:
- Existing `rule_filter` runtime and artifacts
- Admin settings schema/UI
- Run inspection exports and rule-filter stage artifacts
Affected stages:
- `rule_filter`
- `ranking`
Affected features:
- `trigger_run_management`
- `inspection_debugging`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/trigger_run_management/trigger_run_management.yaml`
  feature_history: `docs/features/trigger_run_management/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/feature_overview.md`
Generated refresh required: yes
Spec needed: no
Plan needed: yes
Rollback trigger: Rule-filter pass/reject behavior becomes inconsistent with settings or passed jobs lose deterministic mark visibility.
Rollback method: Revert to the prior always-blocking behavior for all six deterministic rule checks and remove mark-only emission from exports/artifacts.
Migration needed: no
Risk level: medium

## Scope

This plan implements the selectable-screening model described in [2026-04-02-21-20-rule-filter-selectable-screening-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Rule-filter/docs/superpowers/specs/2026-04-02-21-20-rule-filter-selectable-screening-spec.md).

In scope:

- add `rule_filter.selected_filters` as an admin-editable setting
- keep all six deterministic checks inside `rule_filter`
- emit non-blocking `marks` for failed but unselected checks
- preserve blocking `reasons` for selected failed checks
- expose marks in rule-filter artifacts, run results, and run-detail inspection
- make the active blocking set explicit in run snapshots and settings-used output

Out of scope:

- moving `must_have_skill_missing` or `domain_not_preferred` into ranking
- changing ranking formulas
- adding new deterministic rule types
- building a new per-run ad hoc rule authoring system

## Implementation Tasks

### Task 1: Add a code-owned selectable-filter registry

Create one code-owned registry for the six deterministic post-enrichment `rule_filter` checks.

Requirements:

- define stable internal codes and friendly labels in one place
- define the default selected set:
  - `seniority_mismatch`
  - `location_type_excluded`
  - `contract_type_excluded`
  - `experience_level_excluded`
- ensure `must_have_skill_missing` and `domain_not_preferred` remain known but default-unselected
- make the registry reusable by config validation, admin settings UI, runtime evaluation, and artifact rendering

Likely touchpoints:

- `src/fitcv/rule_filter.py`
- `src/fitcv/config.py`
- admin settings schema source in `fitcv_cp`

### Task 2: Add `rule_filter.selected_filters` to config loading and settings UI

Extend config parsing and admin-editable settings so the blocking set is explicit and validated.

Requirements:

- support `rule_filter.selected_filters` in config
- validate values against the registry
- reject duplicates and unknown codes
- preserve round-trippable ordering in settings storage
- surface the setting in the admin settings page as a checkbox-list style field
- provide a `Use Defaults` or equivalent default reset behavior if that already fits the current settings UI pattern

Deliverables:

- config defaults
- settings schema entry
- settings page rendering and save path
- tests for parsing, validation, and UI serialization

### Task 3: Refactor `rule_filter` runtime output into blocking reasons plus marks

Update runtime evaluation so every deterministic check still runs, but each failed check is routed by mode:

- selected -> blocking `reasons`
- not selected -> non-blocking `marks`

Requirements:

- keep existing rejection reason codes unchanged
- add a first-class `marks` field on passed and rejected job records where applicable
- ensure a job is rejected only if it has one or more blocking reasons
- preserve clean `pass with no marks`, `pass with marks`, and `reject with blocking reasons` semantics
- keep synonym-overlay influence limited to input matching quality, not ownership

Recommended mark payload shape:

```json
{
  "code": "must_have_skill_missing",
  "message": "Missing 2 must-have skills",
  "details": {
    "missing_count": 2,
    "missing_skills": ["dbt", "airflow"]
  }
}
```

### Task 4: Persist marks in rule-filter outputs and downstream run exports

Ensure marks survive beyond in-memory filtering and stay inspectable per run.

Requirements:

- extend rule-filter stage results to include marks
- include marks in run-scoped results export for passed jobs
- ensure rejected jobs can also carry an empty or populated `marks` array without ambiguity
- keep compatibility for existing consumers that only rely on `reasons`

Decision for implementation:

- persist marks in both:
  - rule-filter runtime/output structures
  - run-scoped inspection/export payloads

This avoids marks becoming artifact-only data that later surfaces cannot access consistently.

### Task 5: Expand rule-filter stage artifacts and run inspection

Update inspection surfaces so selectable screening is visible and debuggable.

Requirements:

- add `selected_filters` to `stage_transition_artifacts.rule_filter`
- report counts by blocking reason
- report counts by mark code
- include sample passed jobs with marks
- include sample rejected jobs with blocking reasons
- update run-detail filter presentation so passed jobs can show visible marks instead of looking cleanly passed
- keep manual staged runs and synonym-overlay context understandable from settings-used and run detail

Likely touchpoints:

- `src/fitcv/pipeline.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/run_detail.html`

### Task 6: Keep ranking downstream-only and mark-aware

Ensure ranking consumes the filtered passed set and may display rule-filter marks, but does not re-own the checks.

Requirements:

- do not recompute `must_have_skill_missing`
- do not recompute `domain_not_preferred`
- if ranking/run results mention these signals, source them from `rule_filter` marks
- confirm no existing ranking penalty logic independently reinterprets these rule checks

This task is primarily a contract-cleanup and regression-protection step rather than a large ranking rewrite.

### Task 7: Sync source-of-truth docs and generated discovery

Update the relevant docs once runtime behavior is implemented.

Required updates:

- `docs/stages/rule_filter.yaml`
- `docs/features/trigger_run_management/trigger_run_management.yaml`
- `docs/features/trigger_run_management/history.md`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/inspection_debugging/history.md`
- `docs/FitCV-pipeline.md`

Generated refresh:

- regenerate `docs/generated/feature_overview.md`

## Verification Plan

### Unit and contract tests

- config parsing and validation for `rule_filter.selected_filters`
- rule-filter runtime tests for:
  - selected failed checks reject
  - unselected failed checks mark only
  - mixed blocking reasons plus marks
  - default selected set behavior
- artifact/export tests for mark persistence
- admin settings UI tests for selected-filter round-tripping
- run-detail inspection tests for passed jobs with marks

### Regression checks

- existing hard-filter behavior remains unchanged for the four default selected filters
- default config no longer blocks on `must_have_skill_missing`
- default config no longer blocks on `domain_not_preferred`
- manual staged synonym overlay still affects matching quality without changing ownership semantics

## Execution Order

1. Implement the selectable-filter registry and config defaults.
2. Add admin settings schema and UI support.
3. Refactor `rule_filter` runtime to emit `reasons` and `marks`.
4. Persist marks through run results and stage artifacts.
5. Update run-detail inspection surfaces.
6. Confirm ranking only consumes emitted outcomes.
7. Sync docs and refresh generated discovery.

## Risks and Notes

- The highest risk is silent UI ambiguity: passed jobs with marks may still look like clean passes unless inspection surfaces are updated together with runtime output.
- The second risk is contract drift between admin settings, config defaults, and runtime-known filter codes; the shared registry in Task 1 is the guardrail.
- Backward compatibility is manageable if `reasons` stay stable and `marks` are additive.

## Task Status

- [ ] Task 1: Add a code-owned selectable-filter registry
- [ ] Task 2: Add `rule_filter.selected_filters` to config loading and settings UI
- [ ] Task 3: Refactor `rule_filter` runtime output into blocking reasons plus marks
- [ ] Task 4: Persist marks in rule-filter outputs and downstream run exports
- [ ] Task 5: Expand rule-filter stage artifacts and run inspection
- [ ] Task 6: Keep ranking downstream-only and mark-aware
- [ ] Task 7: Sync source-of-truth docs and generated discovery

## Verification Status

- [ ] Not started
