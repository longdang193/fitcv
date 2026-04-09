# Doc System Lifecycle

This document defines the source-of-truth model for project docs.

## Core Principle

Documentation should let a human or agent answer:

- what exists
- what is current
- what changed
- why it changed
- where the real source of truth lives

Docs explain code. They do not replace it.

## Source-Of-Truth Layers

```text
code/                        -> real truth
docs/stages/*.yaml           -> stage contracts when stage-aware docs are in scope
docs/features/*/*.yaml       -> structured current-state truth
docs/features/<feature_id>/  -> feature explanation and history
docs/*.md                    -> cross-cutting product docs
docs/operating_system/*.md   -> repo rules and workflows
README.md                    -> overview
docs/generated/*             -> generated discovery
```

## Placement Rules

### Code

Use code for:

- runtime behavior
- routes and APIs
- validation logic
- data and schema logic

### `docs/features/*/*.yaml`

Use feature YAML for:

- current feature contracts
- identity, status, dependencies, capabilities, refs

### `docs/features/<feature_id>/`

Use feature-specific docs for:

- architecture
- focused flows
- feature history

### `docs/*.md`

Use cross-cutting docs for:

- product architecture
- setup
- shared user/operator guidance

### `docs/operating_system/*.md`

Use operating-system docs for:

- repo governance
- publication workflow
- planning rules
- tooling policy
- instruction layering

### `docs/generated/*`

Use generated discovery for:

- indexes
- summaries
- lookup surfaces

Generated files must not be edited manually.

## Sync Principle

When behavior or structure changes:

- update code
- update the owning feature YAML when a feature contract changes
- update feature docs or cross-cutting docs as needed
- update operating-system docs when repo rules or workflows change
- refresh generated discovery from its source layers

## Practical Heuristic

Use the deepest layer that owns the fact:

- behavior -> code
- feature state -> feature YAML
- feature explanation -> feature docs
- repo workflow -> operating-system docs
- navigation -> README or generated discovery
