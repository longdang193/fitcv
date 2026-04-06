---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Add timeline-linked JSON downloads for stage artifacts and a single run-scoped settings-used JSON to improve debugging without adding an in-page artifact viewer."
invariants:
  - "Stage artifact inspection remains download-first in this rollout; no in-page artifact viewer is required."
  - "The full effective run settings should be persisted once per run, not duplicated into every stage artifact block."
  - "Per-stage downloads should slice existing run-scoped artifacts rather than introducing separate stage-specific persistence models."
  - "Artifacts remain bounded debugging surfaces rather than new systems of record."
  - "Timeline affordances should improve navigation to artifacts without changing stage authority or pipeline decisions."
---

# Timeline-Linked Stage Artifact Downloads Design

## Affected Feature Contracts

- [`docs/features/inspection_debugging/inspection_debugging.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)
- [`docs/features/trigger_run_management/trigger_run_management.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/trigger_run_management/trigger_run_management.yaml)
- [`docs/features/cv_system/cv_system.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)

## Stage Contracts

- [`docs/stages/normalize.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/normalize.yaml)
- [`docs/stages/enrich.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/enrich.yaml)
- [`docs/stages/rule_filter.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/rule_filter.yaml)
- [`docs/stages/shortlist.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/shortlist.yaml)
- [`docs/stages/ranking.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/ranking.yaml)
- [`docs/stages/cv_generation.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/cv_generation.yaml)

## Triage

Feature type: MODIFY  
Summary: Add timeline-linked per-stage artifact downloads plus one run-scoped settings-used JSON so operators can inspect stage outputs and runtime settings directly from the event timeline.  
Reasoning: The existing stage-transition artifact rollout added a run-scoped JSON download, but debugging still requires leaving the timeline context and downloading one combined blob. This is a bounded inspection/debugging enhancement on top of the existing stage-artifacts design rather than a new runtime feature.  
Invariants:
- Timeline links should remain navigation/download affordances only; they must not become a second in-page artifact rendering system in this rollout.
- Settings used by the run should be persisted once in a dedicated run-scoped JSON instead of being repeated inside every stage block.
- Per-stage downloads should be derived from the already persisted run-scoped stage artifact, not stored separately.
- Stage contracts remain the boundary truth; downloaded stage JSON is a runtime snapshot at that boundary.
- Existing run-results export, CV debug export, and run-level stage-artifacts export remain supported.
Dependencies:
- `inspection_debugging`
- `trigger_run_management`
- `cv_system`
- existing run-scoped stage-transition artifacts
- existing effective settings snapshot on `pipeline_runs`
Affected stages:
- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_generation`
Affected features:
- `inspection_debugging`
- `trigger_run_management`
- `cv_system`
Primary lens: stage
Affected docs:
  stage_contracts:
    - `docs/stages/normalize.yaml`
    - `docs/stages/enrich.yaml`
    - `docs/stages/rule_filter.yaml`
    - `docs/stages/shortlist.yaml`
    - `docs/stages/ranking.yaml`
    - `docs/stages/cv_generation.yaml`
  feature_yaml:
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
    - `docs/features/trigger_run_management/trigger_run_management.yaml`
    - `docs/features/cv_system/cv_system.yaml`
  feature_history:
    - `docs/features/inspection_debugging/history.md`
    - `docs/features/trigger_run_management/history.md`
    - `docs/features/cv_system/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - none
  readme: none
  generated:
    - none
Generated refresh required: no  
Spec needed: yes  
Plan needed: yes  
Risk level: medium

## Why This Follow-Up Exists

The current stage-transition artifact feature improved persistence, but it still leaves two debugging frictions:

1. the operator must download one combined JSON and manually find the stage they care about
2. the settings that shaped the run are not exposed as a first-class debugging artifact alongside stage outputs

This is especially awkward in the event timeline, where the operator can already see:

- `layer1_normalize`
- `layer3_shortlist`
- `layer3_ranking`
- `pipeline_complete`

but cannot directly download the artifact for that stage from the same row.

So the missing capability is not a new viewer. It is a better download and inspection flow:

- download the full stage artifact JSON
- download the stage-specific slice from a timeline event row
- download the single settings-used JSON for the run

## Problem Statement

The current admin run detail supports:

- `Download Results JSON`
- `Download CV Debug JSON`
- `Download Stage Artifacts JSON`

But it does not yet support:

- stage-specific downloads from the event timeline
- a dedicated settings-used JSON artifact for debugging

This causes two practical issues:

1. artifact navigation is still too coarse
2. settings context is still implicit rather than inspectable as a dedicated artifact

## Design Goal

Add a timeline-linked, download-only debugging flow where an operator can:

1. download the full run-scoped stage-artifacts JSON
2. download the JSON for one specific stage directly from the corresponding timeline event group
3. download one run-scoped settings-used JSON that captures the effective settings actually used by the run

This rollout should stay bounded:

- no in-page artifact viewer
- no per-stage persistence tables
- no duplicated full config embedded into each stage block

## Proposed Model

### 1. One dedicated run-scoped settings artifact

Add a first-class `settings_used.json` download surface for each run.

Recommended top-level shape:

```json
{
  "run_id": "...",
  "settings_schema_version": "settings_used_v1",
  "created_at": "...",
  "effective_settings": { ... },
  "sources": {
    "config_path": ".env.yaml",
    "active_settings_applied": true,
    "runtime_input_overrides_applied": true
  }
}
```

Purpose:

- give operators the exact effective settings used by the worker
- avoid repeating config payloads inside every stage block

### 2. Keep one combined stage-artifacts JSON

Do not replace the existing combined run-scoped stage-artifacts JSON.

Keep:

- one run-scoped `stage-artifacts.json`

Use it as the backing source for:

- run-level download
- per-stage download slices

### 3. Add per-stage download routes

Each documented stage should become downloadable as a JSON slice of the combined run-scoped artifact.

Recommended route shape:

```text
/admin/runs/{run_id}/stage-artifacts/{stage_id}.json
```

Examples:

- `/admin/runs/<id>/stage-artifacts/normalize.json`
- `/admin/runs/<id>/stage-artifacts/shortlist.json`
- `/admin/runs/<id>/stage-artifacts/ranking.json`

These routes should:

- load the persisted combined stage-artifacts JSON
- extract only the requested stage block
- return a small envelope like:

```json
{
  "run_id": "...",
  "stage_id": "shortlist",
  "artifact_schema_version": "stage_transition_artifacts_stage_v1",
  "created_at": "...",
  "stage_artifact": { ... }
}
```

### 4. Add timeline-linked download affordances

The event timeline should gain stage-aware download actions for the rows that correspond to a recognized stage boundary.

Examples:

- `layer1_normalize` → download `normalize.json`
- `layer1_jobs` → download `enrich.json`
- `layer3_filter` → download `rule_filter.json`
- `layer3_shortlist` → download `shortlist.json`
- `layer3_ranking` → download `ranking.json`
- `layer4_cv_skip`, `layer4_cv_validation_failed`, `pipeline_complete` → download `cv_generation.json`

This should be download-only in Phase 1.5:

- no modal
- no inline expansion
- no pretty in-page rendering

## Event-to-Stage Mapping

The UI needs one explicit mapping from timeline event stages to stage-contract stage IDs.

Recommended mapping:

| Timeline event stage | Stage artifact |
| --- | --- |
| `layer1_normalize` | `normalize` |
| `layer1_jobs` | `enrich` |
| `layer3_filter` | `rule_filter` |
| `layer3_shortlist` | `shortlist` |
| `layer3_ranking` | `ranking` |
| `pipeline_complete` | `cv_generation` |

Optional support:

- `layer4_cv_skip`
- `layer4_cv_validation_failed`

These may also point to `cv_generation` if the run has a persisted `cv_generation` stage block.

Important:

- event labels stay event-local
- stage IDs stay stage-contract-local
- the mapping layer must be explicit, not inferred ad hoc in the template

## What Goes In the Stage Artifact vs Settings Artifact

### Stage artifact should include

- stage status
- counts
- results summaries
- sample rows or identifiers
- stage-local errors
- maybe `relevant_setting_keys`

### Stage artifact should not include

- the full effective config object

### Settings-used artifact should include

- the effective run config actually used by the worker
- high-level provenance:
  - config path
  - active settings applied
  - runtime overrides applied

This split keeps artifacts useful without noisy duplication.

## Why download-only is the right next step

This follow-up should stay small.

Benefits of download-only:

- minimal UI risk
- fast operator value
- no need to design an artifact viewer yet
- no duplication of artifact rendering logic in templates
- keeps the admin surface simple while the artifact contracts mature

So the recommendation is:

- add more download entry points
- do not add a stage artifact viewer yet

## Persistence Recommendation

### Settings-used artifact

Prefer a dedicated run-scoped persistence field on `pipeline_runs`, parallel to:

- `results_export_json`
- `cv_generation_debug_json`
- `stage_transition_artifacts_json`

Recommended new field:

- `settings_used_json`

Why:

- easy run-scoped fetch
- consistent with existing control-plane snapshot model
- avoids reusing `effective_settings_json` directly as a user-facing/debug artifact contract

### Stage slices

Do not persist them separately.

They should be derived at request time from:

- `stage_transition_artifacts_json`

That keeps the storage model simple.

## Boundedness Rules

### Settings-used artifact

Allowed to contain the full effective settings snapshot once per run.

Because it is only stored once, the duplication risk is low compared with embedding it in every stage block.

### Stage artifact slices

Must remain bounded by the same rules as the combined stage-artifacts JSON:

- no extra row expansion at download time
- no stage-specific recomputation
- no automatic enrichment of the stored block

The per-stage route is a slice, not a rebuilt artifact.

## Relationship To Existing Artifacts

### Results export

Keep it.

Purpose:

- run outcome summary

### CV debug export

Keep it.

Purpose:

- deep Layer 4 artifact debugging

### Stage artifacts export

Keep it.

Purpose:

- stage boundary runtime handoff inspection

### Settings-used export

Add it.

Purpose:

- exact run configuration/debug context

Together they form a small, clear debugging artifact set:

1. `results.json`
2. `cv-debug.json`
3. `stage-artifacts.json`
4. `settings-used.json`

## UI Scope

Phase 1.5 UI should include:

- run-level button:
  - `Download Settings Used JSON`
- existing run-level stage-artifacts button remains
- timeline row affordances for recognized stage-boundary events:
  - `Download Stage JSON`

Optional:

- tooltip or compact label showing which stage the row maps to

Out of scope:

- artifact viewer tabs
- inline JSON rendering
- per-stage diff views

## Acceptance Criteria

1. A succeeded run can download one dedicated `settings-used.json` artifact containing the effective settings used by the worker.

2. The event timeline exposes stage-linked download actions for recognized stage-boundary rows.

3. Downloading a stage from the timeline returns only the persisted stage block for that stage, wrapped in a small stage envelope.

4. Stage-specific downloads are derived from the already persisted combined stage-artifacts JSON and do not introduce separate stage persistence.

5. Stage artifacts remain bounded and do not embed the full effective settings object inside every stage block.

6. Operators can debug a run using a small artifact set:
   - settings used
   - stage artifacts
   - results export
   - CV debug

7. The rollout does not add an in-page artifact viewer.

## Recommended Next Step

Write an implementation plan that:

1. adds a dedicated `settings_used_json` persistence surface
2. adds stage-slice download routes derived from `stage_transition_artifacts_json`
3. maps timeline event stages to documented stage IDs in one explicit server-side mapping
4. keeps the UI strictly download-only
5. updates the stage/feature contracts and histories to reflect the new artifact set
