---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Clean up run-detail diagnostics by gating stage artifacts to the stages actually reached, simplifying redundant exports, making synonym-overlay inspection more useful, and tightening timeline and health semantics."
invariants:
  - Run detail remains the single-run inspection surface.
  - Per-stage artifact downloads remain available after their owning stage has been reached.
  - Run-level exports remain available, but redundant surfaces should be demoted rather than multiplied.
  - Stage-local artifacts stay the primary deep-debug contract for a specific stage.
  - Stage-complete rows, not per-job subevents, own stage-level download links in the timeline.
  - Synonym-overlay inspection must reflect the actual run-owned YAML snapshot, not only derived counts.
---

# Run-Detail Artifact Gating And Diagnostics Cleanup

## Triage

Feature type: MODIFY  
Summary: Tighten run-detail artifact availability, simplify redundant run-level exports, improve synonym-overlay inspection, and make timeline and run-health surfaces more informative and less noisy.  
Reasoning: This is an existing run-inspection surface whose current data is useful but whose artifact gating, timeline placement, synonym-overlay summary, and run-health presentation have drifted into a confusing operator experience. The work modifies both the inspection contract and the trigger/run-management UI around run detail.  
Invariants:
- Run detail remains the primary single-run inspection surface.
- A stage artifact must not be downloadable before its owning stage has been reached.
- Per-stage downloads remain stage-owned; run-level downloads remain run-owned.
- `stage-artifacts.json` may remain as a bundle export, but it should not compete with per-stage links as a first-class primary surface.
- Human-facing run detail should favor canonical normalized fields over raw extracted fields unless expanded for debugging.
- Timeline rows should read as stage lifecycle events first, not as a pile of loosely related log lines.
Dependencies:
- `inspection_debugging`
- `trigger_run_management`
- `run_lifecycle_controls`
- stage-transition artifact contracts for `normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, `cv_analysis`, and `cv_generation`
Affected stages:
- normalize
- enrich
- rule_filter
- shortlist
- ranking
- cv_analysis
- cv_generation
Affected features:
- `inspection_debugging`
- `trigger_run_management`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history: `docs/features/inspection_debugging/history.md`
  feature_docs:
    - `none`
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: `none`
  generated:
    - `docs/generated/feature_overview.md`
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_capabilities_index.yaml`
Generated refresh required: yes
Spec needed: yes
Plan needed: yes
Migration needed: no
Risk level: medium

## Problem

The current run-detail experience has several operator-facing mismatches between what the pipeline knows and what the UI suggests:

1. **Artifact downloads can appear before their owning stage is reached**
- Example: `Mapping Suggestions JSON` can be downloaded before `enrich` completes, producing an empty but technically valid file.
- This makes the UI look broken even when the backend is behaving consistently.

2. **Some fields are useful in storage but noisy in the default UI**
- Example: `domain_raw` and `domain` are both valuable in stage artifacts and enriched records, but showing both by default is often redundant for operators.

3. **Run-level and stage-level artifact surfaces overlap too much**
- `Stage Artifacts JSON` overlaps heavily with the dedicated per-stage JSON downloads.
- Several run-detail download buttons and timeline links compete for the same conceptual space.

4. **Synonym-overlay inspection is too abstract**
- `Effective Synonyms: 30` does not help an operator understand what YAML is actually active.
- The run detail already treats jobs input and candidate profile as inspectable artifacts, but synonym overlays are summarized only as counts.

5. **Stage artifacts and timeline messages are not outcome-first**
- Stage artifact organization still favors inputs before outputs, even though operators debug outcomes first.
- Timeline messages often report narrow technical facts instead of compact stage summaries.
- Stage download links appear on some per-job subevents where the stage-complete row would be the correct owner.

6. **Run health is numerically correct but not operator-guiding**
- Percentages alone do not clearly indicate when something is healthy, drifting, or problematic.

## Goals

- Gate each artifact download to the earliest lifecycle point where it has real content.
- Make the run-detail surface outcome-first instead of input-first.
- Keep raw technical fields in artifacts, but reduce redundant default UI exposure.
- Show the actual active synonym-overlay snapshot, not only derived counts.
- Make the timeline read as stage lifecycle plus compact diagnostic summary.
- Make run health visually indicative so operators can spot drift quickly.
- Keep debugging power while reducing redundant or premature download surfaces.

## Non-Goals

- Removing per-stage artifact downloads.
- Deleting `stage-artifacts.json` in this rollout.
- Replacing the stage-transition artifact system.
- Building a full in-browser artifact explorer in this pass.
- Redefining the semantic meaning of `domain_raw` or `domain` in the enrichment pipeline.

## Source-Of-Truth Alignment

Current feature/state contracts:

- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/trigger_run_management.yaml)
- [run_lifecycle_controls.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/cv_analysis.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/stages/cv_generation.yaml)

Primary implementation targets:

- [app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/app.py)
- [run_detail.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/run_detail.html)
- [test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/tests/test_fitcv_cp/test_app.py)
- stage-artifact generation in [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv/pipeline.py) when ordering or summary contracts change

## Detailed Findings And Design

## 1. Artifact Availability Must Be Stage-Gated

### Problem

Some run-detail download buttons appear before their source stage has produced meaningful content.

Known example:
- `Mapping Suggestions JSON` can be downloaded before `enrich`, resulting in:
  - valid JSON
  - empty `suggestions`
  - poor operator trust

### Design

Each artifact surface must be available only after its source stage has been reached.

### Gating Rules

#### Always stage-gated by owning stage

- `Normalize JSON`
  - available after `normalize`
- `Enrich JSON`
  - available after `enrich`
- `Mapping Suggestions JSON`
  - available after `enrich`
- `Rule Filter JSON`
  - available after `rule_filter`
- `Shortlist JSON`
  - available after `shortlist`
- `Ranking JSON`
  - available after `ranking`
- `CV Analysis JSON`
  - available after `cv_analysis`
- `CV Generation JSON`
  - available after `cv_generation`

#### Run-level success exports

- `Results JSON`
  - available only for succeeded runs
- `CV Debug JSON`
  - available only for succeeded runs and only when snapshot exists
- `Settings Used JSON`
  - available only when a settings snapshot exists

#### Bundle exports

- `Stage Artifacts JSON`
  - available only when stage-transition artifacts have actually been persisted
  - for paused manual runs, only if the current run already has a non-empty stage-artifact bundle

### Requirements

- Empty-but-formally-valid payloads should not be treated as downloadable successes when the source stage has not run.
- If a stage is not yet reached, the download control should be hidden rather than disabled with vague wording.

## 2. Clarify `domain_raw` Versus `domain`

### Problem

Operators can easily read `domain_raw` and `domain` as duplicate values when both are surfaced without explanation.

### Design

The system should explicitly treat these as two different layers:

- `domain_raw`
  - the literal extracted or source-facing domain phrase
- `domain`
  - the normalized canonical domain used by runtime logic and matching

### Example

```text
domain_raw = "Retail Banking / Credit Analytics"
domain = "retail_banking"
```

### UI Rule

- Default run-detail tables should show only canonical `domain`.
- `domain_raw` should remain available in downloadable artifacts and any future expanded debug view.

This keeps artifact fidelity without cluttering the default inspection surface.

## 3. Keep `Stage Artifacts JSON`, But Demote It

### Problem

`Stage Artifacts JSON` overlaps heavily with:

- individual per-stage JSON downloads
- stage-slice downloads in the timeline

### Design

Keep `Stage Artifacts JSON`, but reclassify it as:

- a convenience bundle export
- not a primary operator action

### Rules

- keep the endpoint and payload
- keep it under the grouped `Exports` surface
- do not promote it to the same visual priority as stage-specific downloads
- do not duplicate its presence in multiple places on the page

### Rationale

Some operators want a one-click bundle.
That is still valid.
What is not valid is making the bundle export compete visually with the more precise per-stage surfaces.

## 4. Show The Synonym Overlay Snapshot, Not Just A Count

### Problem

`Effective Synonyms: 30` is technically true but operationally weak.

It does not answer:

- which YAML is active
- whether the source is default-only or run-specific
- whether the run overlay came from trigger-time upload or staged override
- what entries are actually in effect

### Design

The `Synonym Overlay` card should show:

- status
  - `default config only`
  - `trigger-time run overlay`
  - `staged override`
- file name when uploaded
- uploaded time
- source
- entry count

And it should also show a collapsible YAML snapshot:

- collapsed by default
- expandable when the operator wants to inspect the actual content

### Rules

- Default-only runs should still show the effective YAML snapshot if available from the runtime-owned source.
- Long YAML should be collapsed, not truncated into uselessness.
- The count may remain, but only as secondary metadata.

## 5. Stage Artifacts Should Become Outcome-First

### Problem

Stage-artifact organization still tends to lead with inputs, even though debugging is usually outcome-first.

### Design

For each stage block, the preferred human-facing order should become:

1. `decision_summary`
2. `outputs_sample`
3. `dropped_or_changed_sample`
4. `inputs_sample`

### Notes

- JSON object ordering is not semantic in the strict sense, but export readability still matters for humans.
- If the UI later renders stage artifacts inline, it should use this same order.

### Goal

An operator should see:

- what the stage produced
- what it rejected or changed
- then what it started from

not the reverse.

## 6. Timeline Messages Must Be More Stage-Summary Oriented

### Problem

Current timeline messages are often too narrow:

- `AI scored: 3 jobs`
- `Vector shortlist: 3 raw hits`
- per-job skip lines with stage download links

This makes the timeline more verbose than informative.

### Design

The timeline should favor one compact stage-summary row per stage completion.

Examples:

- `Normalize complete: kept 6 of 7 jobs, removed 1 duplicate`
- `Enrich complete: 5 enriched, 1 rejected before enrich, fresh=0, reused=5`
- `Rule filter complete: 3 passed, 2 rejected`
- `Shortlist complete: 3 shortlisted, 0 backfilled`
- `Ranking complete: 3 scored, strong=1, stretch=0, skip=2`
- `CV analysis complete: 1 ready, 2 skipped, 0 failed`
- `CV generation complete: 1 accepted, 0 validation failed, 0 failed`

### Humanized Stage Labels

Machine stage codes should be mapped to cleaner labels:

- `pipeline_start` -> `Pipeline Start`
- `layer1_normalize` -> `Normalize`
- `layer1b_pre_filter` -> `Pre-Enrichment Filter`
- `layer1_jobs` -> `Enrich`
- `layer2_candidate` -> `Candidate Profile`
- `layer3_filter` -> `Rule Filter`
- `layer3_shortlist` -> `Shortlist`
- `layer3_ai_score` -> `AI Scoring`
- `layer3_ranking` -> `Ranking`
- `layer4_cv_analysis_skip` -> `CV Analysis Skip`
- `layer4_cv_analysis` -> `CV Analysis`
- `layer4_cv_error` -> `CV Analysis Error` or `CV Generation Error` depending on the true owner
- `pipeline_complete` -> `Pipeline Complete`

### Requirements

- Stage summary rows should carry the most useful compact counts.
- Per-job subevents may remain when helpful, but they should not visually dominate the stage summary.

## 7. Stage Download Links Should Belong To Stage Summary Rows

### Problem

`Download CV Analysis JSON` currently appears on per-job skip rows such as:

- `Skipped ... (fit=skip)`

This is the wrong ownership boundary.

### Design

Stage download links should be attached to the aggregate stage summary row, for example:

- `CV analysis complete: 1 ready, 2 skipped, 0 failed`

Per-job rows should remain narrative only.

### Rule

Timeline stage download links belong on:

- stage-complete rows
- optionally stage-checkpoint rows when that helps staged/manual flows

They should not be attached to per-job subevents.

## 8. Run Health Should Be More Indicative, Not Just Numeric

### Problem

The current `Run Health` card reports correct percentages, but it does not guide interpretation well enough.

### Design

`Run Health` should gain visual severity semantics:

- green for healthy
- amber for caution / drift
- red for likely problem

### Candidate Threshold Model

#### Shortlist

- backfill rate
  - green: `0%`
  - amber: `> 0% and <= 20%`
  - red: `> 20%`

#### Ranking

- skip rate
  - green / amber / red thresholds to be calibrated, but should visibly warn when skip dominates scored jobs

#### CV Analysis

- skip rate
  - caution when unusually high
- failure rate
  - red when non-zero

#### CV Generation

- validation-fail rate
  - amber/red depending on magnitude
- generation-fail rate
  - red when non-zero
- persistence-fail rate
  - red when non-zero

### Presentation

Each health row/tile should show:

- label
- percent
- numerator / denominator
- severity color
- short interpretation text, for example:
  - `Healthy`
  - `Some retrieval drift`
  - `High skip rate`
  - `Validation issues detected`

### Goal

Run health should help an operator answer:

- what is going wrong?
- where should I look next?

without needing to infer meaning from neutral blue percentage chips.

## Proposed UI Hierarchy Changes

The run-detail page should follow this order:

1. Run header + lifecycle actions
2. Run summary
3. Primary outcome banner / outputs
4. Run health
5. Synonym overlay card
6. Inspection tabs
7. Event timeline
8. Export surface

This preserves the run-detail IA cleanup already in progress while making:

- artifacts safer
- health more interpretable
- synonym inspection more useful
- timeline ownership cleaner

## Acceptance Criteria

- `Mapping Suggestions JSON` and any similar stage-owned export no longer appear before their stage has been reached.
- Run detail shows canonical `domain` by default and keeps `domain_raw` in artifacts/debug-only surfaces.
- `Stage Artifacts JSON` remains available but is visually demoted to a convenience bundle export.
- The `Synonym Overlay` card shows a collapsible YAML snapshot instead of only `Effective Synonyms: N`.
- Stage artifact organization and any future inline rendering are outcome-first: outputs, changed state, then inputs.
- Timeline stage summary rows show compact stage-quality-style counts where available.
- Timeline stage download links appear on stage summary rows, not on per-job skip subevents.
- `Run Health` uses visually indicative severity semantics rather than neutral metric presentation only.

## Expected Outcome

After this cleanup:

- operators will stop seeing empty-looking downloads that were offered too early
- raw and normalized fields will stay available without cluttering the default UI
- run-detail artifact surfaces will be easier to trust
- synonym-overlay state will become inspectable in the same spirit as other run-owned inputs
- timeline rows will communicate stage outcomes more clearly
- run health will help operators detect drift and bottlenecks faster
