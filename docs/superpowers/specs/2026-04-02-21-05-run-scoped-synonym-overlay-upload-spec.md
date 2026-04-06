---
feature_type: modify
feature_name: trigger_run_management
status: draft
summary: "Add a run-scoped synonym-overlay upload step after enrich in manual staged mode so admins can adjust skill synonym matching before continuing into rule filter."
invariants:
  - The trusted base `config/skill_synonyms.yaml` must remain unchanged by run-scoped uploads.
  - Uploaded synonym overlays must apply only to the target run unless later promoted separately.
  - Manual staged runs must preserve the existing `Run Next Stage` checkpoint model rather than introducing a second execution lifecycle.
  - Downstream stages in the same run must use one effective merged synonym map once an overlay is uploaded.
---

# Run-Scoped Synonym Overlay Upload Before Rule Filter

## Triage

Feature type: MODIFY  
Summary: Add a run-scoped synonym-overlay upload control at the enrich checkpoint so admins can influence rule-filter and later-stage skill matching before continuing a manual staged run.  
Reasoning: This extends the existing staged run-management and inspection workflow with a missing checkpoint action; it changes current behavior in managed features rather than adding a new product area.  
Invariants:
- The base synonym YAML remains the stable trusted default.
- Uploaded overlays are run-scoped and review-oriented.
- The next-stage continue flow remains linear and checkpoint-driven.
- Rule filter and later synonym-aware stages consume the same effective merged map for a given run.
Dependencies:
- `config/skill_synonyms.yaml`
- runtime synonym overlay loading
- manual staged checkpoint state
- run detail inspection surfaces
Affected stages:
- `enrich`
- `rule_filter`
- `ranking`
- `cv_generation`
Affected features:
- `trigger_run_management`
- `inspection_debugging`
Primary lens: mixed
Affected docs:
- feature_yaml: `docs/features/trigger_run_management/trigger_run_management.yaml`
- feature_history: `docs/features/trigger_run_management/history.md`
- feature_docs:
  - `none`
- cross_cutting_docs:
  - `docs/FitCV-pipeline.md`
  - `docs/stages/enrich.yaml`
  - `docs/stages/rule_filter.yaml`
- readme: `none`
- generated:
  - `none`
Generated refresh required: no
Spec needed: yes
Plan needed: yes
Migration needed: no
Risk level: medium

## Problem

The current staged pipeline can pause after `enrich`, and the project already supports:

- enrich-side mapping suggestion generation
- mapping suggestion downloads
- runtime synonym overlay loading in config resolution

But the manual checkpoint workflow still has a missing operator action:

- there is no admin-facing way to upload an updated skill synonym map before continuing into `rule_filter`

That means the enrich checkpoint can show newly discovered alias candidates, but the admin cannot apply those discoveries in the same staged run without leaving the UI and changing shared config out-of-band.

This is especially painful because the first stage that materially benefits from synonym corrections is `rule_filter`.

Today the workflow is:

1. run `enrich`
2. inspect suggestions
3. manually edit repo or config outside the staged run if you want different matching
4. continue to `rule_filter`

That defeats the main benefit of manual staged mode, which is controlled stage-by-stage debugging inside one run lifecycle.

## Goals

- Let an admin upload a run-scoped synonym overlay after `enrich` and before `rule_filter`.
- Make the upload visible in run detail so the operator knows which overlay is active.
- Ensure `rule_filter` and later synonym-aware stages use the merged effective map for that run.
- Keep the base `skill_synonyms.yaml` unchanged and separate from run-scoped experimentation.
- Preserve a clear review/debugging path between downloaded suggestions and uploaded overlay updates.

## Non-Goals

- Building a full in-browser synonym editor in this rollout.
- Auto-promoting uploaded overlays into the trusted base synonym YAML.
- Supporting arbitrary stage-specific overlays for every stage in phase 1.
- Replacing the existing aggregate or per-run mapping-suggestion downloads.
- Adding synonym upload to `run_all` mode in phase 1.

## Current-State Summary

The project already has most of the substrate needed for this workflow:

- `manual_staged` runs pause after `enrich`
- enrich emits `mapping_suggestions`
- the admin can download run-level and aggregate suggestion JSON
- runtime synonym overlays can be merged on top of the base map

What is missing is the operational bridge between those pieces:

- no upload control in run detail
- no run-scoped overlay persistence owned by the control plane
- no explicit checkpoint contract saying `continue from enrich with this uploaded overlay`

So the system can discover and consume synonym updates technically, but the staged admin workflow cannot drive that lifecycle cleanly.

## Proposed Design

## 1. Add A Run-Scoped Synonym Overlay Upload Action At The Enrich Checkpoint

When a run is:

- `manual_staged`
- paused after `enrich`
- awaiting continuation into `rule_filter`

the run detail page should expose an additional control:

- `Upload Synonym Overlay YAML`

This action should sit next to the existing enrich-checkpoint controls such as:

- `Download Enrich JSON`
- `Download Mapping Suggestions JSON`
- `Run Next Stage`

The intended operator flow becomes:

1. inspect enrich-stage output
2. download mapping suggestions if needed
3. upload a reviewed synonym overlay YAML
4. continue into `rule_filter`

Phase 1 recommendation:

- support file upload only
- keep pasted YAML as a later enhancement if it proves necessary

## 2. Treat The Upload As Run-Scoped Overlay Input

The uploaded YAML should be stored as run-scoped checkpoint input, not as shared repo config.

Recommended behavior:

- attach the uploaded overlay to the run record
- associate it with the current checkpoint after `enrich`
- keep it available for all subsequent stages in that run

It should not:

- mutate `config/skill_synonyms.yaml`
- affect other runs
- silently update default environment config

Illustrative concept:

```json
{
  "run_id": "abc",
  "synonym_overlay_source": "uploaded_yaml",
  "synonym_overlay_filename": "skill_synonyms_reviewed.yaml",
  "synonym_overlay_entries": 12
}
```

## 3. Validate Overlay Shape Before Accepting It

The upload path should validate the YAML before it becomes active.

Minimum validation rules:

- top-level structure must match the project synonym-map contract
- keys and values must be strings
- aliases must be non-empty
- canonicals must be non-empty

Preferred accepted shapes:

```yaml
skill_synonyms:
  powerbi: power bi
  gcp: google cloud
```

or, if the current loader already accepts flat maps, that same existing contract should be reused.

Validation failures should be shown as explicit operator-facing errors in the run detail flow, not as silent no-ops.

## 4. Use One Effective Merged Map For The Rest Of The Run

Once a valid overlay is uploaded, the next continuation from `enrich` should use:

```text
effective_skill_synonyms =
  base skill_synonyms.yaml
  + run-scoped uploaded overlay
```

That effective map should be reused consistently by:

- `rule_filter`
- `ranking`
- `gap_analysis`
- `validator`
- any other synonym-aware stage logic in the run

The key rule is:

- one run, one effective merged synonym map at continuation time

This avoids stage drift where `rule_filter` sees one map and later stages see another.

## 5. Make The Active Overlay Visible In Run Inspection

The run detail page should make the uploaded overlay explicit.

Recommended fields:

- overlay status: none | uploaded
- overlay filename
- upload time
- entry count
- effective-map source summary

This should appear in the same part of the UI that already shows:

- run mode
- checkpoint status
- next stage
- completed stages

The goal is to answer:

- did this run continue with the default synonym map, or with a reviewed overlay?

## 6. Keep Mapping Suggestions And Uploaded Overlays Distinct

The project should continue to distinguish:

- discovered suggestions
- active uploaded overlay
- trusted base synonym map

These are different lifecycle states:

1. discovered during enrich
2. reviewed and uploaded for one run
3. later promoted into trusted shared config

This distinction matters because:

- not every suggestion should be activated
- not every activated overlay entry should become a permanent default
- debugging and governance need a clear audit trail

## 7. Scope The First Rollout To The Enrich -> Rule Filter Handoff

Phase 1 should stay narrow:

- only available in `manual_staged`
- only exposed when the run is paused after `enrich`
- only intended to influence downstream continuation from that checkpoint

This is enough to solve the immediate operator problem without turning the admin UI into a general config editor.

Later extensions could include:

- overlay replacement/removal before continue
- paste-YAML mode
- upload support at later checkpoints
- explicit promotion tooling from run overlay to trusted base config

## Data Contract Notes

The control plane likely needs a run-scoped persistence shape for the uploaded overlay.

Illustrative payload:

```json
{
  "schema_version": "run_synonym_overlay_v1",
  "source": "upload",
  "filename": "skill_synonyms_reviewed.yaml",
  "uploaded_at": "2026-04-02T21:00:00Z",
  "entries": {
    "powerbi": "power bi",
    "gcp": "google cloud"
  }
}
```

Exact storage location can be finalized in implementation, but the run-scoped contract should support:

- inspection
- validation
- deterministic reload on continue

## Operational Flow

Recommended phase-1 operator flow:

1. Trigger a `manual_staged` run.
2. Let the run pause after `enrich`.
3. Inspect enrich outputs and mapping suggestions.
4. Upload a reviewed synonym overlay YAML.
5. Confirm the overlay is active in run detail.
6. Continue to `rule_filter`.
7. Let downstream stages consume the effective merged map for this run.

## Acceptance Criteria

- A manual staged run paused after `enrich` exposes an upload control for a run-scoped synonym overlay.
- The uploaded overlay is validated before activation.
- The uploaded overlay is persisted with the run and survives refresh/reload.
- `rule_filter` and later synonym-aware stages use the merged effective map for that run.
- The run detail page clearly shows whether an overlay is active and which file was uploaded.
- The base `config/skill_synonyms.yaml` remains unchanged by this workflow.

