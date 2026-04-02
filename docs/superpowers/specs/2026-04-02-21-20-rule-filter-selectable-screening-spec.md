---
feature_type: modify
feature_name: rule-filter-selectable-screening
status: draft
summary: "Keep all deterministic filter signals stage-owned by `rule_filter` while allowing admin settings to choose which ones hard-reject and which ones are only marked."
invariants:
  - "`rule_filter` remains the sole owner of deterministic rule evaluation."
  - "Each deterministic filter is evaluated at most once per job per run."
  - "Pre-enrichment global filters remain separate from post-enrichment `rule_filter` checks."
  - "Unselected rule filters do not reject jobs; they produce non-blocking marks only."
  - "Later stages consume `rule_filter` outcomes but do not re-own deterministic rule checks."
---

# Rule Filter Selectable Screening Spec

## Summary

The current `rule_filter` stage mixes two behaviors:

- hard deterministic rejection
- soft-but-useful preference mismatch signals

The current implementation hard-rejects both `must_have_skill_missing` and `domain_not_preferred`, even though both can be valuable as non-blocking review signals in some runs.

This spec keeps a strict stage boundary by making `rule_filter` the single owner of all deterministic rule checks while adding admin-configurable screening selection:

- selected filters: hard screening
- unselected filters: evaluated and recorded as marks

Under the new default:

- `seniority_mismatch`
- `location_type_excluded`
- `contract_type_excluded`
- `experience_level_excluded`

remain selected and blocking.

The following remain stage-owned by `rule_filter` but default to not selected:

- `must_have_skill_missing`
- `domain_not_preferred`

When not selected, those checks do not reject the job. Instead, the run records explicit non-blocking marks such as:

- `missing must-have skills`
- `domain not preferred`

This preserves a clear stage boundary while allowing the admin to tune strictness without moving logic into ranking.

## Goal

Define a stage-owned selectable screening model for deterministic rule filters where:

1. every deterministic rule check remains implemented and evaluated inside `rule_filter`
2. admin settings control which checks are blocking
3. unselected checks remain visible as non-blocking marks for inspection and downstream explanation
4. defaults favor recall for `must_have_skill_missing` and `domain_not_preferred`
5. run settings, artifacts, and admin UI make the active blocking set explicit per run

## Non-Goals

- Moving deterministic rule checks into the ranking stage
- Replacing pre-enrichment global job filters
- Making deterministic rule ownership depend on candidate profile contents
- Introducing per-candidate or per-run ad hoc rule definitions
- Adding new deterministic rule types beyond the current set
- Changing ranking formulas as part of this spec

## Design

### Stage Ownership

`rule_filter` remains the sole owner of all post-enrichment deterministic rule checks.

The stage continues to evaluate these six signals:

- `seniority_mismatch`
- `location_type_excluded`
- `contract_type_excluded`
- `experience_level_excluded`
- `must_have_skill_missing`
- `domain_not_preferred`

The stage boundary becomes:

- `rule_filter` evaluates deterministic eligibility and deterministic non-blocking marks
- `ranking` ranks only the jobs that passed blocking `rule_filter` checks
- `ranking` may consume marks for explanation or display, but it must not re-evaluate or re-own these rule checks

This preserves a single source of truth for deterministic filtering semantics.

### Blocking vs Marked Outcomes

Each deterministic rule check has two possible runtime modes:

1. selected for screening
2. not selected for screening

When selected:

- a failed check is added to `blocking_reasons`
- any job with one or more blocking reasons is rejected by `rule_filter`

When not selected:

- a failed check is added to `marks`
- the job is not rejected solely because of that failed check

This yields three possible per-job outcomes inside `rule_filter`:

1. pass with no marks
2. pass with marks
3. reject with blocking reasons

The stage does not need a fourth ownership mode. A signal is always stage-owned by `rule_filter`; only its enforcement mode changes.

### Default Selection

Default selected screening filters:

- `seniority_mismatch`
- `location_type_excluded`
- `contract_type_excluded`
- `experience_level_excluded`

Default not selected:

- `must_have_skill_missing`
- `domain_not_preferred`

Reasoning:

- the first four are closer to hard candidate eligibility or explicit exclusion constraints
- `must_have_skill_missing` is valuable but subject to JD extraction incompleteness and effective skill-synonym-map quality
- `domain_not_preferred` is a preference signal and often noisier than core eligibility fields

In manual staged runs, this risk can be reduced before `rule_filter` executes by uploading a run-scoped synonym overlay after `enrich` and before continuing to `rule_filter`. This does not change rule ownership. It improves the upstream effective synonym map consumed by `rule_filter`.

### Mark Semantics

Marks are deterministic, stage-owned findings emitted by `rule_filter` for failed checks that were not selected as blocking.

They are not rejection reasons and must not be merged into `reasons`.

Recommended canonical mark codes:

- `must_have_skill_missing`
- `domain_not_preferred`

Recommended mark metadata:

- `code`
- `message`
- optional structured details

Examples:

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

```json
{
  "code": "domain_not_preferred",
  "message": "Job domain is outside preferred domains",
  "details": {
    "job_domain": "finance",
    "preferred_domains": ["analytics", "data_science"]
  }
}
```

The exact message text may evolve, but the code shape should remain stable for inspection/export consumers.

### Config Model

Introduce a new rule-filter settings group that explicitly lists which deterministic post-enrichment filters are blocking.

Suggested config shape:

```yaml
rule_filter:
  selected_filters:
    - seniority_mismatch
    - location_type_excluded
    - contract_type_excluded
    - experience_level_excluded
```

Optional extensions may be added later, but this spec only requires `selected_filters`.

Semantics:

- every known `rule_filter` signal is always evaluated
- only signals listed in `rule_filter.selected_filters` are blocking
- known signals omitted from the list are marked-only

The source of truth for known selectable signals should live in one code-owned registry rather than being duplicated across pipeline logic, admin schema, and templates.

### Settings Schema Changes

The admin-editable settings schema currently supports scalar keys and grouped sections. This feature requires one list-valued stage setting.

Add:

- `rule_filter.selected_filters`

Suggested schema entry:

- key: `rule_filter.selected_filters`
- type: `list[str]`
- group: `rule_filter`
- label: `Blocking Rule Filters`
- description: `Choose which post-enrichment deterministic rule filters reject jobs. Unselected filters are still evaluated and recorded as marks.`
- default:
  - `seniority_mismatch`
  - `location_type_excluded`
  - `contract_type_excluded`
  - `experience_level_excluded`
- config_path:
  - `rule_filter`
  - `selected_filters`
- options:
  - `seniority_mismatch`
  - `location_type_excluded`
  - `contract_type_excluded`
  - `experience_level_excluded`
  - `must_have_skill_missing`
  - `domain_not_preferred`

Validation rules:

- value must be a non-empty list
- each entry must be one of the known selectable filter codes
- duplicates are rejected
- order should be preserved for storage round-tripping, even though runtime semantics do not depend on order
- the schema default must include the four current hard filters and omit the two optional ones

No change is required to `global_job_filters.*`; those remain pre-enrichment settings in their own section.

### Admin Settings UI

Add a dedicated `Rule Filter` settings section to the admin settings page.

Purpose:

- show the full deterministic post-enrichment filter set
- let the admin select which ones are blocking
- explain that unselected filters are still evaluated and surfaced as marks

Recommended UX:

- one section titled `Rule Filter`
- one grouped card titled `Blocking Filters`
- checkbox list for all six selectable filter codes
- helper text explaining:
  - selected = reject jobs
  - unselected = mark only
  - changes affect the next triggered run

Recommended labels:

- `Seniority mismatch`
- `Location type excluded`
- `Contract type excluded`
- `Experience level excluded`
- `Missing must-have skills`
- `Domain not preferred`

Recommended helper copy:

`Selected filters reject jobs in the rule-filter stage. Unselected filters are still evaluated and shown as non-blocking marks in run inspection.`

Recommended affordances:

- a short explanation that `must_have_skill_missing` and `domain_not_preferred` default to mark-only
- `Use Defaults` resets to the four selected / two unselected baseline
- the effective value display shows the currently active blocking set for future runs

### Run Snapshot and Settings-Used Output

Run-scoped settings snapshots must capture the chosen `rule_filter.selected_filters` list so each run is reproducible and explainable.

This setting must appear in:

- `effective_settings_json`
- settings-used export
- any run-detail settings display that reflects the saved config snapshot

The run inspector should not require an operator to infer whether `must_have_skill_missing` was blocking in that run.

For manual staged runs that use enrich-checkpoint synonym upload, the run snapshot should also make it clear that `rule_filter` consumed an effective synonym map that may include a run-scoped overlay layered on top of the base `skill_synonyms.yaml`.

### Rule Filter Runtime Output

The `rule_filter` stage result shape must expand to distinguish blocking reasons from non-blocking marks.

Current conceptual shape:

```json
{
  "passed": ["url1"],
  "rejected": [{"job_url": "url2", "reasons": ["seniority_mismatch"]}]
}
```

Target conceptual shape:

```json
{
  "passed": [
    {
      "job_url": "url1",
      "marks": [
        {
          "code": "domain_not_preferred",
          "message": "Job domain is outside preferred domains"
        }
      ]
    }
  ],
  "rejected": [
    {
      "job_url": "url2",
      "reasons": ["seniority_mismatch"],
      "marks": []
    }
  ]
}
```

Implementation may retain a compatibility-friendly wrapper if needed, but the design requires that marks become first-class stage output and are not overloaded into rejection reasons.

### Persistence and Inspection

`rule_filter_results` currently stores pass/fail plus rejection reasons. The design must evolve inspection outputs so marks are queryable and visible for passed jobs too.

Required behavior:

- rejected jobs continue to store blocking `reasons`
- passed jobs with marks must preserve those marks for run-scoped inspection/export
- run detail should distinguish:
  - rejected by blocking rule filter
  - passed with rule-filter marks
  - passed cleanly

The storage mechanism may be achieved by extending `rule_filter_results` or by using run-scoped artifacts/exports, but the user-facing result must preserve marks with the same run scope as rejection reasons.

Minimum inspection changes:

- run detail filter outcome area shows non-blocking marks for passed jobs
- exported run results include marks alongside existing filter status
- rule-filter stage artifact summarizes both:
  - blocking reason counts
  - mark counts

### Stage Artifact Changes

`stage_transition_artifacts.rule_filter` should expand from pure reject accounting to mixed outcome accounting.

Required additions:

- active `selected_filters` for the run
- counts by blocking reason
- counts by mark code
- sample passed jobs with marks
- sample rejected jobs with blocking reasons

This keeps inspection aligned with the runtime semantics and avoids hidden configuration-dependent behavior.

### Pipeline and Ranking Interaction

Ranking must only consume jobs that passed blocking `rule_filter`.

Ranking may display or forward rule-filter marks for explanatory purposes, but it must not:

- recompute `must_have_skill_missing`
- recompute `domain_not_preferred`
- apply additional penalty semantics that reinterpret those deterministic checks independently of `rule_filter`

If a later ranking explanation wants to mention these signals, it should consume `rule_filter`-emitted marks rather than derive new ownership.

`rule_filter` should evaluate these checks using the run's effective synonym map. In manual staged runs, that effective map may include a run-scoped overlay uploaded after `enrich`. The selectable-screening model remains unchanged: the overlay improves deterministic matching inputs, while `rule_filter` still owns the deterministic decision and mark emission.

### Backward Compatibility

This feature changes rule-filter output semantics and inspection expectations, so compatibility needs to be deliberate.

Recommended compatibility approach:

- keep existing rejection reason codes unchanged
- add marks as a new field rather than changing the meaning of `reasons`
- default behavior preserves the current four hard filters as blocking
- existing runs without `rule_filter.selected_filters` in their settings snapshot are interpreted using the new default list

### Documentation Impact

Update source-of-truth docs to reflect:

- `rule_filter` owns deterministic marks as well as deterministic rejections
- admin settings now include a selectable rule-filter blocking set
- inspection/export surfaces show marks for passed jobs
- manual staged runs may update the effective skill synonym map after `enrich` and before `rule_filter`

Primary doc updates expected:

- `docs/stages/rule_filter.yaml`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/trigger_run_management/trigger_run_management.yaml`
- `docs/features/cv_system/cv_system.yaml`
- `docs/FitCV-pipeline.md`

## Acceptance Criteria

- [ ] `rule_filter` remains the sole owner of all six deterministic post-enrichment checks
- [ ] `must_have_skill_missing` and `domain_not_preferred` are not moved to ranking
- [ ] admin-editable setting `rule_filter.selected_filters` exists
- [ ] the setting accepts only known deterministic rule-filter codes
- [ ] defaults select `seniority_mismatch`, `location_type_excluded`, `contract_type_excluded`, and `experience_level_excluded`
- [ ] defaults leave `must_have_skill_missing` and `domain_not_preferred` unselected
- [ ] selected filters reject jobs
- [ ] unselected filters do not reject jobs
- [ ] unselected failed filters are emitted as non-blocking marks
- [ ] passed jobs can carry rule-filter marks
- [ ] rejected jobs continue to carry blocking reasons
- [ ] run-scoped settings snapshots record the active `rule_filter.selected_filters`
- [ ] admin settings page includes a dedicated `Rule Filter` section for blocking filter selection
- [ ] run detail and exports distinguish blocking reasons from marks
- [ ] rule-filter stage artifacts report both blocking reason counts and mark counts
- [ ] ranking does not re-evaluate or re-own `must_have_skill_missing` or `domain_not_preferred`

## Open Questions

- Should marks be persisted in `rule_filter_results`, in stage artifacts only, or in both?
- Should passed jobs with marks get a dedicated UI label such as `passed_with_marks`, or should the UI keep a binary pass/fail label plus a visible marks badge?
- Should the admin settings UI show stable internal codes, friendly labels only, or both?
