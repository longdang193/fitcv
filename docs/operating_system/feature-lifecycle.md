# Feature Lifecycle

This document defines how managed features are classified and tracked.

## Core Principle

A real managed feature should have a human-owned source at
`docs/features/<feature_id>/feature.source.yaml` and a generated current-state
contract at `docs/features/<feature_id>/<feature_id>.yaml`.

Stages help with architecture and planning, but features remain the primary lifecycle units.

## Classification

Use these classifications for meaningful feature work:

- `ADD`
  - new capability with no existing equivalent
- `MODIFY`
  - behavior change to an existing capability
- `REPLACE`
  - new capability that supersedes an older one

If a change is only a defect correction with no meaningful contract change, update code and docs as needed without inventing a new feature.

## Status Flow

```text
planned -> draft -> building -> rollout -> active -> deprecated
```

Use `feature.source.yaml` to track human-owned feature meaning and the
generated feature contract to inspect the assembled current state.

## Required Feature Contract Shape

Each managed feature should use this folder shape:

- `docs/features/<feature_id>/feature.source.yaml`
- `docs/features/<feature_id>/<feature_id>.yaml`
- `docs/features/<feature_id>/lineage.generated.yaml`
- `docs/features/<feature_id>/history.md`

The source layer should define:

- `feature_id`
- `name`
- `status`
- `type`
- `summary`
- `invariants`
- `domains`
- `depends_on`
- `capabilities`
- optional `stage_participation`

Naming and shape policy for this repo:

- `feature_id` uses lowercase underscore format such as `cv_system`
- `capability_id` uses `<feature_id>.<kebab-suffix>`
- managed features should use structured capability entries with at least:
  - `capability_id`
  - `statement`
  - `state`
- capability IDs should name durable product or domain behavior, not sentence-level change notes
- long implementation details belong in capability `statement`, linked evidence surfaces, or feature history rather than inside the ID itself
- string-only capability entries are not accepted in steady-state Mode B

Ownership split:

- `feature.source.yaml` remains the minimal human-owned semantic source
- `<feature_id>.yaml` is the generated assembled current-state contract
- `lineage.generated.yaml` is the generated evidence-oriented lineage surface
- `history.md` remains feature-local history and human context; partial-generated starter history alignment is still a follow-up step for this repo

## File Metadata And Proof

Files with behavioral weight should use top-of-file `@meta` docstrings when they
live under repo-controlled script and test surfaces such as `scripts/` and
`tests/`.

Rules:

- file-level `capabilities` metadata is selective, not blanket
- only add capability references when the file materially participates in
  lineage
- use test-level `@proves <capability_id>` as proof evidence when a test exists
  to verify a capability
- do not treat tests, helper wrappers, or passive docs as semantic capability
  owners just because they mention a feature

The generated contract and lineage files are outputs, not hand-edited sources.
The current lineage target is the evidence-oriented Phase 5 shape:

- `feature_id`
- `source`
- `invariants`
- `capabilities`
- `timeline`

Phase 6 hydration rules:

- generated lineage should stay human-readable and must not emit YAML alias
  anchors such as `&id001` or `*id001`
- direct capability evidence should come from explicit file metadata and
  `@proves` when available
- feature-level specs and plans may be included as conservative fallback
  evidence, but they do not replace direct implementation or proof evidence
- `completeness_status` should stay conservative:
  - `complete` requires direct code or test evidence
  - `partial` means some real evidence exists but not enough for full coverage
  - `missing_evidence` means only weak or no evidence has been found

Phase 7 direct-evidence pilot rules:

- direct evidence backfill should start with a bounded pilot, not repo-wide
  blanket tagging
- Phase 8 extends the same pilot model to selected `settings_system` and
  `pipeline_performance` capabilities, but it is still not a requirement that
  every managed capability be complete
- Phase 9 extends the pilot to selected `trigger_run_management` and
  `inspection_debugging` capabilities and also treats noisy source-level YAML
  anchors in human-owned feature sources as readability drift to clean up during
  targeted evidence batches
- Phase 10 closes the residual `settings_system` and `pipeline_performance`
  pilot set by mapping UI/schema/config/runtime settings controls and stage
  performance behavior to direct code and proof evidence
- pilot capability-to-file mappings should stay sparse and materially true
- pilot proof should use truthful `@proves <capability_id>` only in tests that
  actually verify the named behavior
- repo-level pilot requirements may be declared in
  `repo_config/adoption-mode.yaml` and enforced by
  `scripts/validate_adoption_shape.py`
- if a capability still lacks truthful direct proof, prefer leaving it
  `partial` over inventing noisy ownership

Refresh source-owned feature outputs with:

```powershell
python scripts/sync_architecture_docs.py
```

Validate repo-wide adoption shape with:

```powershell
python scripts/validate_adoption_shape.py
```

## Planning Gate

Before writing a spec or plan, determine:

- whether an affected feature already exists
- whether the change is `ADD`, `MODIFY`, or `REPLACE`
- which feature docs and generated surfaces must be updated

Cross-cutting operating-system changes may use `Affected features: none`.

## Completion Rule

A managed feature is not truly complete until:

- code is updated
- the owning feature source is updated
- supporting docs are updated as needed
- generated discovery is refreshed when source layers changed
