---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Add a run-level zip export that bundles all currently available artifacts using the existing artifact contract and stage-gating rules."
invariants:
  - "Individual artifact downloads remain available and unchanged."
  - "The zip export is a convenience bundle, not a second artifact source of truth."
  - "Bundle contents must follow the same availability and stage-gating rules as the existing run-detail export surface."
  - "Missing artifacts must not fail the entire zip build."
---

# Run Artifact Bundle Zip Export

## Goal

Add a single `Download All Artifacts (.zip)` action on run detail so operators can export a run's currently available artifacts in one step, without duplicating artifact ownership logic or introducing a parallel contract.

## Why

The current run-detail experience makes operators download many files one by one:

- `results.json`
- `stage-artifacts.json`
- per-stage JSONs
- `settings-used.json`
- `cv-debug.json`
- `mapping-suggestions.json`

That works for deep inspection, but it is tedious for debugging, sharing, and archival. A bundle export improves usability while keeping the existing artifact model intact.

## Scope

This change applies to:

- run detail export UX
- run-scoped export endpoint behavior
- artifact availability/gating reuse

This change does not alter:

- per-stage artifact generation
- artifact schemas
- individual artifact download endpoints

## Design

### Product contract

Run detail adds one new export action:

- `Download All Artifacts (.zip)`

The zip contains all artifacts that are currently available for that run at the time of download.

Examples:

- a paused staged run after `normalize` may only include `normalize.json` and `stage-artifacts.json`
- a succeeded run may include the full bundle
- a failed run may include only the artifacts that were actually reached and persisted before failure

### Bundle ownership

The zip is a convenience transport only.

It must not compute new pipeline outputs or invent new artifact semantics. It simply packages existing run-scoped artifacts that are already:

- persisted
- stage-owned
- allowed by the current gating model

### Included files

The bundle should include the following when available:

- `manifest.json`
- `results.json`
- `stage-artifacts.json`
- `normalize.json`
- `enrich.json`
- `rule_filter.json`
- `shortlist.json`
- `ranking.json`
- `cv_analysis.json`
- `cv_generation.json`
- `settings-used.json`
- `cv-debug.json`
- `mapping-suggestions.json`

`mapping-suggestions.json` remains enrich-owned and must only be included after `enrich` has truly been reached.

### Manifest

The bundle includes a lightweight `manifest.json` to make partial bundles explicit.

Recommended fields:

```json
{
  "run_id": "...",
  "status": "awaiting_continue",
  "created_at": "...",
  "finished_at": null,
  "bundle_schema_version": "run_artifact_bundle_v1",
  "included_files": [
    "stage-artifacts.json",
    "normalize.json"
  ],
  "missing_files": [
    "enrich.json",
    "results.json"
  ]
}
```

The manifest is descriptive only. It does not become a new source of truth.

## Availability rules

The zip endpoint must reuse the same artifact availability rules already used by run detail.

That means:

- no artifact is included just because its filename is known
- inclusion requires the same persisted payload and stage reachability the UI already respects
- artifacts unavailable from the current run state are omitted, not treated as errors

### Minimum expected bundle behavior

- If at least one artifact is available, the bundle download succeeds.
- If no artifacts are available yet, the endpoint should return a user-facing validation response rather than an empty misleading zip.

## UX

### Placement

Place the new action in `Run Exports` ahead of the individual downloads:

- `Download All Artifacts (.zip)`

### Helper copy

Recommended helper text:

- `Includes all currently available run artifacts.`

This wording works for both `Run All` and `Stage by Stage` and makes partial bundles understandable for in-progress runs.

### Existing exports

Keep all existing individual download actions. The zip is additive, not a replacement.

## Execution model

The bundle should be assembled directly from already-available in-memory or persisted run artifact payloads inside the control plane.

It should:

- avoid recomputing any stage outputs
- avoid re-running pipeline logic
- avoid writing permanent new storage objects unless later needed for scale

For the first implementation, on-demand zip generation per request is the preferred model.

## Failure handling

### Do

- gracefully skip missing artifacts
- include a manifest that explains what was bundled
- return a normal zip when a subset exists

### Do not

- fail the entire bundle because one optional artifact is missing
- expose artifacts that the run has not actually reached
- create a second set of bundle-specific artifact rules

## Affected features

Primary:

- `docs/features/inspection_debugging/inspection_debugging.yaml`

Secondary:

- `docs/features/trigger_run_management/trigger_run_management.yaml`

## Affected stages

- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`

## Non-goals

- changing artifact schemas
- replacing individual downloads
- adding background prebuilt zip storage
- changing stage ownership of existing artifacts

## Acceptance criteria

- Run detail shows `Download All Artifacts (.zip)` in `Run Exports`.
- The bundle includes all and only currently available artifacts for the run.
- `mapping-suggestions.json` is never included before `enrich`.
- A partial run can still download a valid partial bundle.
- A succeeded run can download a complete bundle when all artifacts exist.
- The bundle includes `manifest.json` describing included and missing files.
- Individual artifact download behavior remains unchanged.
