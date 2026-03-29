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

## 5-Layer Doc System

```text
code/                        → real truth
docs/features/*.yaml         → structured truth
docs/features/<feature_id>/  → explanation + history
README.md                    → overview
docs/generated/              → generated discovery
````

| Layer                 | Form                           | Purpose                   | Rule                                |
| --------------------- | ------------------------------ | ------------------------- | ----------------------------------- |
| Real Truth            | code                           | Actual behavior           | Deepest truth                       |
| Structured Truth      | `docs/features/*.yaml`         | Current feature contracts | One small file per feature          |
| Explanation + History | `docs/features/<feature_id>/*` | Design, flow, history     | Explain; do not duplicate code      |
| Overview              | `README.md`                    | Purpose and navigation    | Entry point only                    |
| Generated Discovery   | `docs/generated/*`             | Fast lookup               | Generated only; never edit manually |

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

Use `docs/features/<feature_id>/` for focused docs: design, flow, spec, plan, ops notes, and history.

Rules:

- explanation, not duplication
- current-state docs describe current behavior
- rationale belongs here, not in YAML
- prefer small focused docs over one large doc

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
| Feature added/changed                             | `docs/features/*.yaml`                  |
| Architecture or cross-feature explanation changes | docs                                    |
| Purpose/navigation changes                        | `README.md`                             |
| Feature history changes                           | `docs/features/<feature_id>/history.md` |
| Lookup surfaces stale                             | regenerate `docs/generated/*`           |

## Naming

- feature contract: `docs/features/<feature_id>/<feature_id>.yaml`
- feature docs/history: `docs/features/<feature_id>/`
- spec: `docs/superpowers/specs/YYYY-MM-DD-HH-MM-<feature>-spec.md`
- plan: `docs/superpowers/plans/YYYY-MM-DD-HH-MM-<feature>-plan.md`
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

If a fact is generated, update the source and regenerate.

## Cross-Reference Discipline

- README links to key docs and generated discovery
- feature YAML links to docs/spec/plan/history
- generated indexes point to authoritative files
- no orphan docs
- no conflicting current-state sources

## Anti-Patterns

- duplicating facts across code, YAML, docs, and generated files
- putting long history into YAML
- putting implementation detail into README
- manually maintaining generated relationships
- editing generated files manually
- treating docs as more authoritative than code
- changing code without updating feature YAML

## Migration Policy

Applies to NEW documents only.

Existing docs are grandfathered. They do not need to be rewritten. When a feature YAML exists, it becomes the current structured truth for that feature.
