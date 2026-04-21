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
  - `name`

The generated contract and lineage files are outputs, not hand-edited sources.

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
