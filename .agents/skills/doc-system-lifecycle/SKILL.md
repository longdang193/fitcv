---
name: doc-system-lifecycle
description: Use for designing, updating, or auditing project docs. Defines the 5-layer doc system, naming, frontmatter, sync rules, and generated discovery. Applies to NEW documents; existing docs are grandfathered
---


# Doc System Lifecycle

## When to Apply

Apply when:

- creating or revising docs
- designing doc structure
- adding or changing features
- changing architecture, routes, settings, or schemas
- reviewing docs for clarity, discoverability, or consistency

## Core Principle

> Documentation is the project’s navigation, discovery, and explanation system.  
> It should let a human or agent answer: what exists, what is current, what changed, why it changed, and where the real source of truth lives.

Docs should explain code, not mirror it.

## 5-Layer Doc System with Stage-Aware Extension

```text
code/                       → real truth
docs/stages/*.yaml          → stage contracts (when stage-aware docs are in scope)
docs/features/*/*.yaml        → structured truth
docs/features/<feature_id>/ → feature-specific explanation + history
docs/*.md                   → cross-cutting explanation
README.md                   → overview
docs/generated/             → generated discovery
````

| Layer                   | Form                           | Purpose                            | Rule                                |
| ----------------------- | ------------------------------ | ---------------------------------- | ----------------------------------- |
| Stage Contracts         | `docs/stages/*.yaml`           | Stage boundaries and ownership hints | Optional; architectural only      |
| Real Truth              | code                           | Actual behavior                    | Deepest truth                       |
| Structured Truth        | `docs/features/*/*.yaml`         | Current feature contracts          | One small file per feature          |
| Feature Explanation     | `docs/features/<feature_id>/*` | Design, flow, ops notes, history   | Feature-specific only               |
| Cross-Cutting Docs      | `docs/*.md`                    | Architecture, pipelines, shared ops| Cross-feature only                  |
| Overview                | `README.md`                    | Purpose and navigation             | Entry point only                    |
| Generated Discovery     | `docs/generated/*`             | Fast lookup                        | Generated only; never edit manually |

### Layer 1 — Code

Authoritative for behavior, routes/APIs, and schema/data logic.

### Layer 2 — Feature YAML

Authoritative for current feature state.

Rules:

- one file per real feature
- current state only
- small and stable
- keep `depends_on`
- generate inverse links like `used_by`

### Stage Contracts When In Scope

Stage-aware projects may add:

```text
docs/stages/*.yaml
```

Use this layer only for:

- stage identity
- purpose
- inputs / outputs
- architectural boundaries
- stage-to-feature relationships

Rules:

- stages are above features for navigation, not replacement lifecycle units
- stage contracts must not duplicate full feature truth
- do not create placeholder stage files before a project-specific rollout is ready

Recommended shape:

```yaml
feature_id:
name:
version:
status:
type:
owner:
summary:
invariants: []
domains: []
depends_on: []
capabilities: []
refs:
  docs: []
  spec: []
  plan: []
  history:
keywords: []
```

### Layer 3 — Explanation + History

Use `docs/features/<feature_id>/` for focused docs such as design, flow, ops notes, and history for one feature. Use `docs/*.md` only for cross-feature architecture docs. Specs and plans continue to live under `docs/superpowers/`.

Rules:

- explanation, not duplication
- current-state docs describe current behavior
- rationale belongs here, not in YAML
- prefer small focused docs over one large doc

### Placement Table

Use this default placement:

| Information kind | Default location |
| ---------------- | ---------------- |
| Stage boundary contract (when adopted) | `docs/stages/<stage_id>.yaml` |
| Current feature contract | `docs/features/<feature_id>/<feature_id>.yaml` |
| Feature-specific history / post-execution review | `docs/features/<feature_id>/history.md` |
| Other feature-specific explanation | `docs/features/<feature_id>/*.md` |
| Cross-cutting architecture / pipeline / shared ops | `docs/*.md` |
| Project overview / navigation | `README.md` |
| Generated lookup surfaces | `docs/generated/*` |

Do not treat `docs/*.md` as the default home for feature-specific history.

### Layer 4 — README

Must answer:

- Why
- What
- Where

Must not become:

- a feature registry
- a design dump
- a changelog

### Layer 5 — Generated Discovery

Required for fast lookup.

Minimum outputs:

```text
docs/generated/features_index.yaml
docs/generated/feature_overview.md
```

Add more only when needed, such as:

- `feature_dependency_graph.yaml`
- `feature_file_map.yaml`
- `routes_index.yaml`
- `settings_index.yaml`

Rules:

- generate from code/YAML/docs
- never edit manually
- not a source of truth
- always point back to the source

## Artifact Conventions

| Situation                                         | Update                                  |
| ------------------------------------------------- | --------------------------------------- |
| Behavior changes                                  | code                                    |
| Feature added/changed                             | `docs/features/*/*.yaml`                  |
| Feature-specific explanation changes              | `docs/features/<feature_id>/*.md`       |
| Architecture or cross-feature explanation changes | `docs/*.md`                             |
| Purpose/navigation changes                        | `README.md`                             |
| Feature history changes                           | `docs/features/<feature_id>/history.md` |
| Lookup surfaces stale                             | regenerate `docs/generated/*`           |

## Naming

- feature contract: `docs/features/<feature_id>/<feature_id>.yaml`
- stage contract when adopted: `docs/stages/<stage_id>.yaml`
- feature docs/history: `docs/features/<feature_id>/`
- spec: `docs/superpowers/archive/specs/YYYY-MM-DD-HH-MM-<feature>-spec.md`
- plan: `docs/superpowers/archive/plans/YYYY-MM-DD-HH-MM-<feature>-plan.md`
- generated files: descriptive names under `docs/generated/`

## Frontmatter for Specs and Plans

```yaml
---
feature_type: modify   # add | modify | replace
feature_name: run-input-snapshot-consistency
status: building
summary: "<1-sentence goal>"
---
```

Optional:

```yaml
invariants:
  - non-negotiable constraints
```

## Sync Principle

- update code when behavior changes
- update feature YAML before or with feature changes
- update docs before or with design/reasoning changes
- update README when navigation changes
- regenerate `docs/generated/` whenever sources change

Before marking work complete, name the exact docs touched:

- affected `docs/features/<feature_id>/<feature_id>.yaml`
- affected `docs/stages/<stage_id>.yaml` when stage-aware docs are in scope
- `docs/features/<feature_id>/history.md` or other focused docs under `docs/features/<feature_id>/`
- any cross-feature docs under `docs/*.md`
- `README.md` if navigation changed
- generated outputs to refresh

If a fact is generated, update the source and regenerate.

## Cross-Reference Discipline

- README links to key docs and generated discovery
- feature YAML links to docs/spec/plan/history
- generated indexes point to authoritative files
- no orphan docs
- no conflicting current-state sources

## Anti-Patterns

- duplicating facts across code, YAML, docs, and generated files
- treating stage contracts as a replacement for feature contracts
- putting long history into YAML
- putting implementation detail into README
- manually maintaining generated relationships
- editing generated files manually
- treating docs as more authoritative than code
- changing code without updating feature YAML

## Migration Policy

Applies to NEW documents only.

Existing docs are grandfathered. They do not need to be rewritten. When a feature YAML exists, it becomes the current structured truth for that feature.

