# Feature Lifecycle

This document defines how managed features are classified and tracked.

## Core Principle

A real managed feature should have a current-state contract at `docs/features/<feature_id>/<feature_id>.yaml`.

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

Use the feature YAML to track the current state.

## Required Feature Contract Shape

Each managed feature should define:

- `feature_id`
- `name`
- `version`
- `status`
- `type`
- `summary`
- `invariants`
- `domains`
- `depends_on`
- `capabilities`
- `refs`

## Planning Gate

Before writing a spec or plan, determine:

- whether an affected feature already exists
- whether the change is `ADD`, `MODIFY`, or `REPLACE`
- which feature docs and generated surfaces must be updated

Cross-cutting operating-system changes may use `Affected features: none`.

## Completion Rule

A managed feature is not truly complete until:

- code is updated
- the feature contract is updated
- supporting docs are updated as needed
- generated discovery is refreshed when source layers changed
