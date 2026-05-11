---
name: skill-doc-system-lifecycle
description: Use when designing, updating, or auditing project docs, artifact
  schemas, metadata contracts, sync rules, or generated discovery surfaces that
  affect source-of-truth placement or validator behavior.
allowed-tools: []
hooks:
  pre:
  - python scripts/hooks/run_validator.py --fast
  post:
  - python scripts/hooks/run_validator.py --fast
required_reads:
- docs/operating_system/governance/repo-governance.md
tags:
- skill
- skill-doc-system-lifecycle
required_outputs: []
---

# Doc System Lifecycle

## When to Apply

Apply when:

- creating or revising docs
- designing doc structure
- adding or changing features
- changing architecture, routes, settings, or schemas
- reviewing docs for clarity, discoverability, or consistency

## Mandatory Read

<MUST-READ>
Before doc-system decisions, read:

- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/planning/planning-dispatch.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `docs/operating_system/lifecycle/feature-lifecycle.md` when feature-managed surfaces are in scope
- `docs/operating_system/templates/task-start-routing-guide.md` when routing/planning artifacts are in scope
- `docs/operating_system/templates/master-workstream-roadmap-template.md` when roadmap shape is in scope
- `docs/operating_system/templates/registered-workstream-list-template.md` when workstream registration shape is in scope
- `docs/operating_system/templates/bounded-change-thread-template.md` when bounded thread shape is in scope
- `docs/operating_system/templates/complete-specification-set-template.md` when spec-set orchestration is in scope
- `docs/operating_system/templates/spec-authoring-map-template.md` when spec authoring orchestration is in scope
- `docs/operating_system/templates/detailed-specification-template.md` when spec structure is in scope
- `docs/operating_system/templates/implementation-execution-map-template.md` when multi-plan execution orchestration is in scope
- `docs/operating_system/templates/implementation-plan-template.md` when implementation-plan structure is in scope
- `repo_config/planning_artifact_schema.yaml` when planning metadata contract changes are in scope
- `repo_config/adoption-mode.yaml` when adoption-state or managed-surface obligations may change
- `repo_config/agent-adapter-mappings.json` or equivalent adapter mapping config only in source repos that own adapter/runtime generation; consume-only starter-kit clones should treat this surface as absent by design
- `repo_config/publication-config.json` only in source repos that own curated public publication; consume-only starter-kit clones should treat this surface as absent by design
- relevant validator and sync scripts under `scripts/` when changing schema/config contracts they enforce
- relevant tests under `tests/` when changing schema/config contracts they verify
</MUST-READ>

## Python Metadata Grounding Checklist

When drafting or reviewing Python `@meta` blocks for governed files:

1. Read ownership surfaces in order:
   - `docs/features/<feature_id>/feature.source.yaml` first
   - generated `docs/features/<feature_id>/<feature_id>.yaml` only if assembled view needed
   - `docs/features/<feature_id>/lineage.generated.yaml` only for evidence/drift questions
2. Set `ownership` explicitly to `feature` or `infrastructure`.
3. If `ownership: feature`, include `@meta.capabilities` and derive entries from upstream `capability_id` values only.
4. If `ownership: infrastructure`, omit `@meta.capabilities` only under approved infrastructure exception policy; if present, all values must resolve upstream.
5. Do not add manual `features` list when capability IDs already encode ownership.
6. Ensure file-level `responsibility`, `inputs`, and `outputs` reflect real behavior (no placeholders).
7. Verify linkage markers remain consistent:
   - file-level `@meta.capabilities`
   - code-level `@capability`
   - test-level `@proves`
8. Before closure claims on metadata-touching changes, run applicable checks:
   - `py tools/docs/generate_architecture_metadata.py --check`
   - `py scripts/validate_repo_contracts.py --fast`

## Planning-Lineage Compliance

- Treat `docs/superpowers/specs/`, `docs/superpowers/execution_maps/`, and `docs/superpowers/plans/` as execution-facing artifacts, not governing layers.
- Use `docs/generated/planning_lineage.yaml` for derived thread/spec/plan inspection rather than re-entering linkage manually in source docs.
- Keep source-of-truth ownership upstream; execution and generated inspection surfaces should derive from that ownership.
- Treat the standardized roadmap/workstream/thread/spec/map/plan templates under `docs/operating_system/templates/` as the canonical shape definitions for those artifact families.

## Artifact-Schema Compliance

- Treat schema/config contract files under `repo_config/` and their owning lifecycle docs as canonical surfaces for artifact-shape policy.
- Prefer one upstream schema owner over duplicated downstream validator or prose restatement whenever the contract can be derived.
- When schema contracts change, update the enforcing validators and tests in the same lane.
- When generated or adapter/runtime surfaces depend on schema/config contracts, refresh them and name that refresh explicitly in closeout evidence.
- Choose and state a migration policy for existing artifacts: hard break, compatibility alias, or phased migration.
- New artifacts must follow the current canonical schema; older artifacts may remain grandfathered unless migration is explicitly required.
- Do not introduce schema-only drift where templates, validators, tests, and generated outputs disagree about the contract.

## Core Principle

> Documentation is the project's navigation, discovery, and explanation system.
> It should let a human or agent answer: what exists, what is current, what changed, why it changed, and where the real source of truth lives.

Docs should explain code, not mirror it.

Canonical truth should flow downward from upstream owning layers. Lower layers
should derive or reference that truth rather than restating the same semantic
fact manually.

## Source-Of-Truth Layers

```text
code/                                 -> real truth
docs/intent/*.md                     -> project purpose and outcome sources
docs/operating_system/*.md           -> repo method and governance sources
docs/stages/*.source.yaml            -> human-owned stage source when stage-aware docs are in scope
docs/stages/*.yaml                   -> generated stage contracts when stage-aware docs are in scope
docs/features/*/feature.source.yaml  -> human-owned feature source
docs/features/*/<feature_id>.yaml    -> generated current feature contract
docs/features/*/lineage.generated.yaml -> generated feature-local evidence
docs/features/<feature_id>/          -> feature-specific explanation + partial-generated history
docs/*.md                            -> cross-cutting product explanation
docs/superpowers/specs/*.md          -> design artifacts
docs/superpowers/execution_maps/*.md -> orchestration artifacts for approved spec sets
docs/superpowers/plans/*.md          -> execution artifacts
README.md                            -> overview
docs/generated/*                     -> generated discovery
```

| Layer | Form | Purpose | Rule |
| --- | --- | --- | --- |
| Real Truth | code | Actual behavior | Deepest truth |
| Intent Source | `docs/intent/*.md` | Project purpose and outcomes | Stable, source-like, human-authored |
| Operating-System Source | `docs/operating_system/*.md` | Repo method and governance | Stable, method-focused, human-authored |
| Stage Source | `docs/stages/*.source.yaml` | Human-owned stage intent | Edit directly when stage meaning changes |
| Stage Contract | `docs/stages/*.yaml` | Generated stage boundary view | Generated only; validator-enforced in managed mode |
| Feature Source | `docs/features/*/feature.source.yaml` | Human-owned feature meaning | Edit directly when feature meaning changes |
| Feature Contract | `docs/features/*/<feature_id>.yaml` | Generated current feature contract | Generated only; validator-enforced in managed mode |
| Feature Local Evidence | `docs/features/*/lineage.generated.yaml` | Generated ownership and lineage facts | Generated only |
| Feature Explanation/History | `docs/features/<feature_id>/*` | Design, flow, ops notes, history | Feature-specific only |
| Cross-Cutting Product Docs | `docs/*.md` | Architecture, pipelines, shared product explanation | Cross-feature only |
| Execution Artifacts | `docs/superpowers/specs/*.md`, `docs/superpowers/execution_maps/*.md`, `docs/superpowers/plans/*.md` | Design, orchestration, and execution artifacts | Metadata-guided, not governing layers |
| Overview | `README.md` | Purpose and navigation | Entry point only |
| Generated Discovery | `docs/generated/*` | Fast lookup | Generated only; current managed discovery surfaces are validator-enforced |

## Governing Layers

Use `docs/intent/` for:

- the original project problem
- stakeholders and audiences
- success outcomes
- major promises the project should preserve
- constraints and non-goals

Rules:

- keep intent docs stable and source-like
- do not turn intent docs into execution logs or changelogs
- do not move repo-method rules into intent just because they are cross-cutting

Use `docs/operating_system/` for:

- repo governance
- planning rules
- tooling policy
- workflow and routing guidance
- instruction layering

Rules:

- keep operating-system docs method-focused
- if the document is really about what the project is for, it belongs in `docs/intent/`

## Stage Source And Stage Contracts

Use stage source files for:

- stage identity
- purpose
- inputs / outputs
- architectural boundaries
- stage-to-feature relationships
- short human notes

Rules:

- humans edit `docs/stages/*.source.yaml`
- generated stage contracts must not duplicate full feature truth
- stage source owns stage role semantics such as `primary_features` and `supporting_features`
- feature source owns stage capability participation through `stage_participation.stage_id` and `capability_ids`
- generated stage contracts derive assembled refs and linkage views from those sources
- in managed mode, generated stage contracts are validator-enforced migration targets rather than loose generated suggestions
- the expected steady-state shape is a flat top-level mapping with fields such as `stage_id`, `name`, `status`, `purpose`, and generated ref families like `feature_refs`, `capability_refs`, `code_refs`, `test_refs`, `doc_refs`, `config_refs`, and `component_refs`
- older nested stage wrappers are migration debt, not a valid steady-state managed shape

## Feature Source, Generated Contract, And Evidence

Use `docs/features/*/feature.source.yaml` as the human-owned semantic source.
Use the generated `<feature_id>.yaml` only as the assembled current-state
contract.

Rules:

- one real feature folder per managed feature
- edit `feature.source.yaml`, not generated feature YAML
- do not keep manual feature `version`
- freshness fields such as `revision`, `latest_change_id`, and `last_updated_at` are generated from completed plans
- do not use `manual_refs`; refs come from metadata on the owning code, tests, docs, specs, plans, configs, and AML components
- use `lineage.generated.yaml` for detailed evidence, ownership, and timeline facts
- in managed mode, the generated `<feature_id>.yaml` contract is validator-enforced, including canonical top-level fields and `refs` families
- generated feature contracts should keep structured `invariants` and `capabilities` entries rather than legacy bare-string summaries

Recommended feature-source shape:

```yaml
feature_id:
name:
status:
type:
summary:
invariants: []
domains: []
depends_on: []
capabilities: []
stage_participation: []
lineage_exceptions: []
```

Selective reading rule for opted-in feature folders:

- read `feature.source.yaml` first
- read the generated `<feature_id>.yaml` only when the current assembled contract view is needed
- read `lineage.generated.yaml` for ownership, evidence, drift, or traceability work
- read `history.md` or other feature prose only when explanation or chronology is needed
- do not load the entire feature folder by default

## Feature Explanation + History

Use `docs/features/<feature_id>/` for focused docs such as design, flow, ops
notes, and history for one feature. Use `docs/*.md` only for cross-feature
product docs.

Rules:

- explanation, not duplication
- current-state docs describe current behavior
- rationale belongs here, not in YAML
- prefer small focused docs over one large doc
- `history.md` is partially generated when the feature is opted into the architecture system:
  - the block between `<!-- GENERATED HISTORY START -->` and `<!-- GENERATED HISTORY END -->` is generator-owned
  - `## Human Notes` stays human-authored
- in managed mode, that generated boundary pattern is validator-enforced for `history.md`

## Placement Table

Use this default placement:

| Information kind | Default location |
| --- | --- |
| Project purpose / outcomes | `docs/intent/*.md` |
| Repo method / governance | `docs/operating_system/*.md` |
| Stage boundary source | `docs/stages/<stage_id>.source.yaml` |
| Generated stage boundary contract | `docs/stages/<stage_id>.yaml` |
| Feature source | `docs/features/<feature_id>/feature.source.yaml` |
| Current feature contract | `docs/features/<feature_id>/<feature_id>.yaml` |
| Generated feature evidence | `docs/features/<feature_id>/lineage.generated.yaml` |
| Feature-specific history / post-execution review | `docs/features/<feature_id>/history.md` |
| Other feature-specific explanation | `docs/features/<feature_id>/*.md` |
| Cross-cutting product architecture / pipeline / shared ops | `docs/*.md` |
| Project overview / navigation | `README.md` |
| Design artifacts | `docs/superpowers/specs/*.md` |
| Spec-authoring and implementation-execution orchestration artifacts | `docs/superpowers/execution_maps/*.md` |
| Execution artifacts | `docs/superpowers/plans/*.md` |
| Generated lookup surfaces | `docs/generated/*` |

Do not treat `docs/*.md` as the default home for feature-specific history or
`docs/operating_system/*.md` as the default home for project intent.

## README

Must answer:

- why
- what
- where

Must not become:

- a feature registry
- a design dump
- a changelog

README remains a synthesized orientation layer. It should summarize the source
layers rather than becoming a parallel source of truth.

## Generated Discovery

Use `docs/generated/*` for:

- aggregate indexes
- summaries
- lookup surfaces
- assembled planning lineage across workstreams, threads, specs, and plans

Rules:

- generate from code, YAML, docs, specs, and plans
- never edit manually
- not a source of truth
- always point back to the source
- use `docs/generated/planning_lineage.yaml` when humans need the assembled
  thread/spec/plan lineage view
- for the current managed target, treat `docs/generated/architecture_dag.yaml` and `docs/generated/capability_lineage.yaml` as validator-enforced generated contracts, not optional byproducts

## Metadata for Specs and Plans

For new or touched specs/plans under `docs/superpowers/`, use:

```yaml
---
layer: intent | operating_system | workstream | change
artifact_type: spec | plan
status: proposed | active | completed | superseded
parent_thread: <thread-id> | none
parent_spec: docs/superpowers/specs/<file>.md | none
targets:
  - <path>
related_features:
  - <feature_id>
related_stages:
  - <stage_id>
---
```

Rules:

- `layer`, `artifact_type`, and `status` are required
- for new change-layer specs, prefer `parent_thread`
- for new change-layer plans, prefer `parent_thread` plus `parent_spec`
- `related_features` and `related_stages` are optional
- `targets` is required when the artifact is cross-cutting or otherwise ambiguous in scope
- `targets` may be omitted only when the scope is already obvious and narrowly local

## Sync Principle

- update code when behavior changes
- update intent docs when project-purpose sources change
- update stage source before or with stage-meaning changes
- update feature source before or with feature-meaning changes
- update docs before or with design or reasoning changes
- update README when navigation changes
- rerun `scripts/sync_architecture_docs.py` whenever architecture metadata sources change

Before marking work complete, name the exact docs touched:

- affected `docs/intent/*.md` when project-purpose sources changed
- affected `docs/operating_system/*.md` when repo method changed
- affected `docs/stages/<stage_id>.source.yaml` when stage-aware docs are in scope
- affected `docs/stages/<stage_id>.yaml` when stage-aware docs are in scope
- affected `docs/features/<feature_id>/feature.source.yaml`
- affected `docs/features/<feature_id>/<feature_id>.yaml`
- affected `docs/features/<feature_id>/lineage.generated.yaml` when evidence changed
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
- changing code without updating the owning feature or stage source
- restating an upstream semantic fact manually in a downstream layer when it should be derived instead

## Migration Policy

Applies to NEW documents only.

Existing docs are grandfathered. They do not need to be rewritten. When a
feature YAML exists, it becomes the current structured truth for that feature.
