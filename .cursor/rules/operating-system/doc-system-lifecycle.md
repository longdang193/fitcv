# Doc System Lifecycle

## When to Apply

Apply this rule whenever designing, updating, or auditing project documentation.

This includes:

- creating or revising project docs
- designing doc structure for a new project
- adding or modifying features
- changing architecture, routes, settings, or schemas
- reviewing docs for clarity, discoverability, completeness, and consistency
- ensuring both humans and agents can quickly find the right source

---

## Core Principle

> Documentation is the project’s navigation, discovery, and explanation system.
> It must allow a reader, human or AI, to answer:
> **what exists, what is current, what changed, why it changed, and where the real source of truth lives.**

Docs must not attempt to fully mirror code.

---

## Source-of-Truth Model

The system has five layers:

```text
code/                       → real truth
docs/features/*.yaml        → structured truth (current state)
docs/features/<feature_id>/ → feature-specific explanation and history
docs/*.md                   → cross-cutting explanation
README.md                   → overview
docs/generated/             → generated discovery
```

Rules:

- **code** defines actual behavior
- **feature YAML** defines what exists now
- **docs** explain how and why
- **README** helps navigation
- **generated discovery** provides fast lookup surfaces for humans and agents

Avoid duplicating the same fact manually across layers.

---

## The 5-Layer Doc System

| Layer                     | Form                           | Purpose                                   | Rule                                               |
| ------------------------- | ------------------------------ | ----------------------------------------- | -------------------------------------------------- |
| **Real Truth**            | code                           | Actual implementation and behavior        | Deepest truth                                      |
| **Structured Truth**      | `docs/features/*.yaml`         | Current feature contracts                 | One file per real feature; small and stable        |
| **Feature Docs + History**| `docs/features/<feature_id>/*` | Feature-specific architecture, flows, history | Explain one feature; do not duplicate code     |
| **Cross-Cutting Docs**    | `docs/*.md`                    | Shared architecture, pipelines, setup     | Cross-feature only                                 |
| **Overview**              | `README.md`                    | Purpose, scope, navigation                | Entry point only                                   |
| **Generated Discovery**   | `docs/generated/*`             | Fast lookup surfaces                      | Generated from code/YAML/docs; never edit manually |

---

## Layer 1 — Real Truth (Code)

Code is the authoritative source for:

- execution behavior
- routes and APIs
- schemas and data logic
- settings resolution
- validation rules

Rules:

- if code and docs disagree, code wins
- docs should explain code, not replicate it

---

## Layer 2 — Structured Truth (`docs/features/*.yaml`)

Feature files are the authoritative source for **current feature state**.

Rules:

- one file per real feature
- current state only
- small, structured, and stable
- avoid large volatile inventories unless truly necessary
- maintain `depends_on`
- do not manually maintain inverse relationships like `used_by`

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

Guidance:

- use `invariants`
- keep YAML focused on identity and contract
- do not turn feature YAML into a design document
- keep feature history in `docs/features/<feature_id>/`

---

## Layer 3 — Explanation + History (`docs/features/<feature_id>/*`)

Docs explain the system.

They include:

- architecture
- subsystem behavior
- flows and pipelines
- operational guidance

Rules:

- explanation, not duplication
- current-state docs describe the current system
- rationale belongs in docs, not YAML
- prefer multiple focused docs over one large file

### Placement Table

Use this default placement:

| Information kind | Default location |
| ---------------- | ---------------- |
| Current feature contract | `docs/features/<feature_id>.yaml` |
| Feature-specific history / post-execution review | `docs/features/<feature_id>/history.md` |
| Other feature-specific explanation | `docs/features/<feature_id>/*.md` |
| Cross-cutting architecture / pipelines / shared ops | `docs/*.md` |
| Project overview / navigation | `README.md` |
| Generated lookup surfaces | `docs/generated/*` |

Do not treat `docs/*.md` as the default home for feature-specific history.

Each feature keeps its contract at `docs/features/<feature_id>.yaml` and its explanation/history under `docs/features/<feature_id>/`.

If docs grow large, split by subsystem instead of expanding one giant file.

---

## Layer 4 — Overview (`README.md`)

README is the entry point.

Must answer:

- **Why** — purpose and value
- **What** — what the system does
- **Where** — how to navigate

Must not become:

- feature registry
- architecture dump
- changelog

---

## Layer 5 — Generated Discovery (`docs/generated/`)

Generated discovery artifacts are required lookup surfaces for humans and agents.

Purpose:

- accelerate navigation
- improve retrieval
- avoid repeated manual lookup
- provide compact searchable summaries of current state

Rules:

- generated from code, feature YAML, and/or docs
- never edited manually
- not the primary source of truth
- must always point back to the authoritative source
- should favor compact, predictable, machine-friendly formats

Every project should generate at least:

```text
docs/generated/features_index.yaml
docs/generated/feature_overview.md
```

These provide:

- list of all features
- status and type
- quick navigation entry points

Add more generated artifacts only when real friction appears. Examples:

- dependency unclear → `feature_dependency_graph.yaml`
- ownership unclear → `feature_file_map.yaml`
- too many routes → `routes_index.yaml`
- too many settings → `settings_index.yaml`

Do not generate these upfront.

Generation guidance:

- generate repetitive inventories instead of hand-maintaining them in prose
- generate inverse relationships like `used_by`
- generate indexes that help answer “where should I look?”
- generated files should include a clear “do not edit manually” header when practical

---

## Artifact Conventions

### When to Update Which Layer

| Situation                             | Update                           |
| ------------------------------------- | -------------------------------- |
| Behavior changes                      | code                             |
| Feature added or changed              | `docs/features/*.yaml`                  |
| Feature-specific explanation changes  | `docs/features/<feature_id>/*.md`       |
| Architecture or cross-feature changes | `docs/*.md`                             |
| Project purpose or navigation changes | `README.md`                             |
| Feature evolution needs human history | `docs/features/<feature_id>/history.md` |
| Lookup surfaces need refresh          | `docs/generated/*` via generator        |

---

## Naming Conventions

- feature contracts: `docs/features/<feature_id>.yaml`
- feature explanation and history: `docs/features/<feature_id>/`
- specs: `docs/superpowers/specs/YYYY-MM-DD-HH-MM-<feature>-spec.md`
- implementation plans: `docs/superpowers/plans/YYYY-MM-DD-HH-MM-<feature>-plan.md`
- generated artifacts: descriptive names under `docs/generated/`

Keep naming predictable and searchable.

---

## Frontmatter for Specs and Plans

```yaml
---
feature_type: modify   # add | modify | replace
feature_name: run-input-snapshot-consistency
status: building       # planned | draft | building | rollout | active | deprecated
summary: "<1-sentence goal>"
---
```

Optional:

```yaml
invariants:
  - non-negotiable constraints
```

---

## Sync Principle

- update code when behavior changes
- update feature YAML before or with feature changes
- update docs before or with architecture or reasoning changes
- update README when purpose or navigation changes
- regenerate `docs/generated/` whenever source layers change
- docs must not lag behind the system

Before marking work complete, name the exact docs touched:

- affected `docs/features/<feature_id>.yaml`
- `docs/features/<feature_id>/history.md` or other focused docs under `docs/features/<feature_id>/`
- any cross-feature docs under `docs/*.md`
- `README.md` if navigation changed
- generated outputs refreshed

If a fact is generated, update the source and regenerate; do not hand-edit the generated artifact.

---

## Cross-Reference Discipline

- `README.md` links to key docs and generated discovery surfaces
- feature files link to docs, specs, plans, and history
- feature directories link their history and focused docs back to the contract
- generated indexes point back to authoritative files
- no orphan docs
- no conflicting current-state sources

---

## Anti-Patterns

- one giant `docs/features/` directory (one file per feature instead)
- duplicating the same fact across code, YAML, docs, and generated files
- putting long history into feature YAML
- putting implementation detail into README
- manually maintaining inverse relationships that should be generated
- editing generated artifacts manually
- treating docs as more authoritative than code
- updating code without updating feature YAML
- letting generated discovery drift from its sources

---

## Practical Heuristics

Default placement:

- behavior → code
- current feature state → `docs/features/*.yaml`
- explanation and rationale → `docs/features/<feature_id>/` for feature-specific; `docs/*.md` for cross-cutting architecture
- project entry point → `README.md`
- fast lookup and retrieval surfaces → `docs/generated/*`

When unsure, place information in the **deepest layer that owns it**, then generate any higher-level discovery view from that source.

---

## Minimum Healthy System

A healthy project should have at least:

- code as real truth
- one YAML per major feature
- docs explaining architecture or key subsystems
- a README for purpose and navigation
- generated discovery artifacts that index the current system
