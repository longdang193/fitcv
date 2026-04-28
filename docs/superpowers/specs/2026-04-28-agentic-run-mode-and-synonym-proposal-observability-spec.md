---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-operator-surface
targets:
  - docs/intent/workstreams/threads/workstream-agentic-observability/02-agentic-observability-operator-surface.md
  - docs/intent/workstreams/threads/workstream-agentic-synonym-management/03-agentic-synonym-review-queue-and-approval.md
  - src/fitcv/pipeline.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/worker_job.py
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_analysis.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/stages/cv_generation.yaml
related_features:
  - inspection_debugging
  - trigger_run_management
  - cv_system
related_stages:
  - cv_analysis
  - cv_generation
---

# Agentic Run Mode And Synonym Proposal Observability

## Summary

Define the operator-visible artifact contract for late-stage agentic runs so a
reviewer can tell whether a run used the agentic path, what agentic artifacts
exist, and whether synonym-proposal persistence succeeded, degraded, or never
applied.

This spec is motivated by two connected truth gaps:

- a non-agentic run can look "missing agentic data" even when nothing is broken
- synonym proposals can fail to persist cleanly while leaving no first-class
  run artifact that explains what happened

The goal is not to make every artifact verbose. The goal is to stop forcing
operators to infer important runtime facts from absence.

## Triage

Layer: `change`  
Feature type: `MODIFY`

Reasoning:

- this is a bounded observability and artifact-truth change, not a new product
  lane
- existing run-detail, artifact-bundle, and CV-stage diagnostics surfaces
  already exist and need a clearer contract
- the synonym-persistence failure belongs here because the operator symptom is
  missing or ambiguous run truth, not just storage drift

Invariants:

- visible run artifacts must distinguish `not applicable` from `expected but
  missing`
- non-agentic late-stage runs must state that they are non-agentic instead of
  relying on empty inference
- agentic synonym-proposal visibility must not depend solely on BigQuery schema
  health
- artifact bundles must surface bounded truth and degradation, not raw provider
  internals

Dependencies:

- `docs/intent/workstreams/threads/workstream-agentic-observability/02-agentic-observability-operator-surface.md`
- `docs/intent/workstreams/threads/workstream-agentic-synonym-management/03-agentic-synonym-review-queue-and-approval.md`
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/bq_store.py`
- `src/fitcv_cp/worker_job.py`

Primary lens: `mixed`

Generated refresh required: `yes` after the spec is added, because
`docs/generated/planning_lineage.yaml` derives spec linkage from frontmatter.

Plan needed: `yes` before implementation, because the work crosses pipeline,
artifact-bundle, and persistence surfaces.

## Problem

The motivating example is run
`34b182b7-6264-4d6e-81e3-13e5ac4e0446`.

Investigation showed:

- `cv_analysis.json` was present and structurally normal
- `settings-used.json`, `results.json`, `cv-debug.json`, `cv_analysis.json`,
  and `cv_generation.json` contained no explicit agentic marker
- the run appears to have followed the non-agentic path because
  `cv.agentic_late_stage.enabled` was not active
- the only way to reach that conclusion was to infer from absence and from code
  in `src/fitcv/pipeline.py`

Separately, synonym-proposal persistence already has real drift:

- `src/fitcv_cp/bq_store.py` warns and degrades when
  `synonym_proposals_json` is missing from BigQuery
- the run bundle does not currently expose a first-class synonym-proposals
  artifact
- an operator can see a persistence warning or downstream absence, but not one
  bounded run-scoped truth object that says what proposals existed and whether
  persistence succeeded

These are the same class of failure:

- runtime truth exists
- operator-visible artifacts do not state it explicitly enough

## Goals

- make agentic late-stage mode explicit in operator-visible run artifacts
- distinguish `agentic disabled`, `agentic enabled but no output`, and
  `agentic output present`
- add a bounded synonym-proposals artifact contract to the run bundle
- expose degraded persistence status when BigQuery schema drift prevents durable
  storage
- keep run-detail and exported artifacts aligned on the same truth vocabulary

## Non-Goals

- no redesign of the full run-detail UI in this spec
- no new synonym review queue behavior here
- no requirement to persist raw model traces or private chain-of-thought
- no broad rewrite of every stage artifact payload

## Proposed Contract

## 1. Run-Level Agentic Mode Truth

Every run that reaches the late CV stages should expose one compact late-stage
mode summary in operator-visible artifacts.

Minimum fields:

- `late_stage_mode`: `agentic` | `non_agentic`
- `agentic_late_stage_enabled`: `true` | `false`
- `mode_source`: bounded source such as config or server-resolved mode
- `agentic_status`: `not_applicable` | `pending` | `completed` | `degraded`

Rules:

- a non-agentic run must explicitly say so
- `not_applicable` means the run did not take the agentic late-stage path
- `pending` means the agentic path is in scope but the output is not final yet
- `degraded` means the run attempted to produce agentic visibility but one or
  more required observability artifacts could not be completed

## 2. Artifact Placement Contract

The late-stage mode summary should appear in bounded operator-facing artifacts
that already act as run truth surfaces.

Required surfaces:

- `settings-used.json`
- `results.json`
- `cv_analysis.json`
- `cv_generation.json` when the stage is reached
- bundle `manifest.json`

Placement rules:

- `settings-used.json` should state the resolved runtime mode inputs and the
  final late-stage mode decision
- `results.json` should expose a compact job-facing projection so exports can
  answer whether an outcome came from the agentic late-stage path
- stage artifacts should say whether they were produced under agentic or
  non-agentic mode when the stage is reached
- `manifest.json` should identify whether agentic-only artifacts are expected,
  present, absent by design, or absent due to degradation

## 3. Non-Agentic Truth Contract

Non-agentic runs must no longer look like partial failures.

For non-agentic runs:

- the bundle should include explicit late-stage mode truth
- agentic-only artifact entries may be omitted, but the manifest must mark them
  `not_applicable` rather than silently absent
- stage artifacts should not contain empty placeholder agentic sections just to
  satisfy schema symmetry

Rule:

- explicit absence metadata is preferred over empty agentic payload shells

## 4. Agentic Artifact Expectation Contract

When `agentic_late_stage_enabled` is true, the run bundle should state which
agentic artifact families are expected.

At minimum the manifest should support per-artifact state such as:

- `present`
- `not_applicable`
- `missing`
- `degraded`

Meaning:

- `present`: artifact exists and is bundle-visible
- `not_applicable`: artifact was never expected for this run path
- `missing`: artifact should exist but does not
- `degraded`: a fallback summary exists, but the primary durable surface did
  not complete cleanly

This prevents operators from conflating "not agentic" with "agentic but broken."

## 5. Synonym-Proposals Artifact Contract

The bundle should gain a first-class synonym-proposals artifact for runs that
produce or attempt to produce agentic synonym proposals.

Suggested artifact:

- `synonym-proposals.json`

Minimum payload families:

- proposal-generation applicability
- proposal summary count
- bounded proposal objects or proposal summaries
- persistence status
- persistence destination summary
- degradation reason when durable persistence fails

This artifact is the run-scoped truth surface. BigQuery is a downstream durable
store, not the only place the operator can learn what happened.

## 6. Synonym Persistence Status Contract

Synonym-proposal persistence should expose a bounded status instead of only
warning logs.

Minimum statuses:

- `not_applicable`
- `not_attempted`
- `persisted`
- `bundle_only_degraded`
- `failed`

Meaning:

- `not_applicable`: this run or stage never entered synonym-proposal flow
- `not_attempted`: the flow existed but no proposal snapshot was produced
- `persisted`: durable store update succeeded
- `bundle_only_degraded`: proposals are preserved in the run artifact bundle,
  but durable store persistence failed or schema drift blocked it
- `failed`: neither durable persistence nor bounded fallback artifact creation
  succeeded

The current `synonym_proposals_json` schema-drift case should map to
`bundle_only_degraded` if the run artifact exists, not to silent absence.

## 7. Bundle Manifest Contract

`manifest.json` should become the first place an operator can answer:

- was this run agentic in late stage?
- should synonym proposals exist?
- which artifacts are present by design versus missing unexpectedly?

Manifest requirements:

- include the run-level late-stage mode summary
- list `synonym-proposals.json` when applicable
- encode absence/degradation state for optional artifacts
- preserve current bounded bundle behavior without becoming a full duplicate of
  every payload

## 8. Relationship To Run Detail

The operator control plane should consume these artifact truths rather than
reconstruct them ad hoc.

Run detail should be able to show:

- late-stage mode: agentic or non-agentic
- whether agentic-specific artifacts were expected
- whether synonym proposals were generated
- whether persistence succeeded, degraded to bundle-only, or failed

Rule:

- UI labels remain derived views, but the artifact vocabulary owns the truth

## 9. Degradation Rules

Degradation handling must remain operator-readable and implementation-safe.

Required behavior:

- BigQuery schema drift must not erase run-scoped proposal visibility
- missing durable storage should surface a compact reason code and human-readable
  summary
- degraded status should not mark the overall run as agentic failure unless the
  actual CV path failed
- observability degradation should remain distinct from business outcome failure

## Acceptance Criteria

- a reviewer can inspect the artifact bundle for run
  `34b182b7-6264-4d6e-81e3-13e5ac4e0446` and conclude directly that late-stage
  agentic mode was not enabled
- a reviewer can inspect an agentic run and see that late-stage agentic mode
  was enabled without reading code
- bundle metadata distinguishes `not_applicable`, `present`, `missing`, and
  `degraded` for optional agentic artifacts
- synonym proposals become visible through a run-scoped artifact when that flow
  is in play
- BigQuery column drift for `synonym_proposals_json` produces explicit degraded
  persistence truth instead of silent operator ambiguity

## Validation Expectations

- add tests for non-agentic runs that assert explicit late-stage mode truth in
  `settings-used.json`, `results.json`, and the bundle manifest
- add tests for agentic runs that assert agentic mode truth and expected
  artifact-state signaling
- add tests for synonym-proposal artifact bundling when proposal generation
  occurs
- add tests for persistence degradation when the BigQuery
  `synonym_proposals_json` column is absent
- verify the bundle manifest and download list stay aligned

## Risks

- if the repo only adds UI labels and not artifact truth, the ambiguity will
  return in exports and offline debugging
- if synonym proposals remain durable-store-only, schema drift will keep hiding
  useful run evidence
- if `degraded` and `failed` are collapsed, operators will over-diagnose
  business-path failures when the real problem is observability persistence

## Next Artifact

The next bounded artifact should be an implementation plan that splits this
spec into:

- runtime mode truth injection
- bundle and manifest contract changes
- synonym-proposal persistence fallback and validation coverage
