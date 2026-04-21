---
feature_type: modify
feature_name: none
status: draft
summary: "Define the Phase 2 rollout that expands the proven Option B pilot across the remaining managed features and stages, adds repo-wide validation, and fills the missing cross-cutting Mode B doc surfaces."
invariants:
  - "the private repo remains the development source of truth"
  - "feature and stage meaning must live in source files before generated contracts are trusted as current-state truth"
  - "generated contracts, lineage, and discovery remain script-owned outputs rather than human-authored sources"
  - "starter-controlled shared surfaces may diverge locally only when the divergence is intentional, reviewable, and recorded"
  - "Phase 2 must leave the repo in a truthful repo-wide Mode B shape even if deeper metadata enrichment is still deferred"
---

# Option B Phase 2 Rollout Spec

## Triage

Layer: `operating_system`  
Feature type: `MODIFY`  
Summary: Expand the Phase 1 Option B pilot into a repo-wide rollout for all remaining managed features and stages, then add validator-backed enforcement and the missing root/intent docs required by the current starter guidance.  
Reasoning: Phase 1 proved the source/generated split for `cv_system` and `cv_analysis`, but the repo still mixes pilot-era truth with pre-Mode-B docs elsewhere. Phase 2 needs to remove that mixed state by migrating the rest of the managed architecture surfaces and making repo-wide drift detectable.  
Invariants:
- The private repo remains the development source of truth.
- Human-owned feature meaning must live in `feature.source.yaml` before generated feature contracts are treated as authoritative.
- Human-owned stage meaning must live in `docs/stages/*.source.yaml` before generated stage contracts are treated as authoritative.
- Generated contracts, lineage, and discovery remain outputs of sync tooling and are never the canonical edit surface.
- The starter shared-surface contract recorded in `repo_config/adoption-mode.yaml` must stay reviewable throughout the rollout.
- Phase 2 must leave the repo in a repo-wide Mode B shape that a future validator can check deterministically.
Dependencies:
- `docs/superpowers/archive/specs/2026-04-21-23-50-option-b-migration-spec.md`
- `docs/superpowers/plans/2026-04-22-00-10-option-b-phase-1-pilot-plan.md`
- `docs/features/cv_system/feature.source.yaml`
- `docs/stages/cv_analysis.source.yaml`
- `scripts/sync_architecture_docs.py`
- `tests/test_sync_architecture_docs.py`
- `repo_config/adoption-mode.yaml`
- `docs/operating_system/repo-governance.md`
- `docs/operating_system/feature-lifecycle.md`
- `docs/operating_system/stage-lifecycle.md`
- `docs/operating_system/publication-workflow.md`
Affected stages:
- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_generation`
- `cv_analysis`
Affected features:
- `admin_control_plane_core`
- `bounded_parallel_enrichment`
- `cv_system`
- `inspection_debugging`
- `multi_file_job_input`
- `pipeline_performance`
- `run_lifecycle_controls`
- `settings_system`
- `trigger_run_management`
- `ui_consistency_theming`
Primary lens: `cross-cutting`
Affected docs:
  feature_source: `docs/features/*/feature.source.yaml`
  feature_yaml: `docs/features/*/<feature_id>.yaml`
  feature_lineage: `docs/features/*/lineage.generated.yaml`
  feature_history: `docs/features/*/history.md`
  stage_source: `docs/stages/*.source.yaml`
  stage_contract: `docs/stages/*.yaml`
  feature_docs: `docs/features/*/*.md`
  cross_cutting_docs:
    - `docs/setup.md`
    - `docs/configuration.md`
    - `docs/usage.md`
    - `docs/pipeline.md`
    - `docs/architecture.md`
    - `docs/intent/README.md`
    - `docs/intent/project-charter.md`
    - `docs/intent/stakeholders.md`
    - `docs/intent/success-outcomes.md`
    - `docs/intent/constraints-and-non-goals.md`
    - `docs/operating_system/repo-governance.md`
    - `docs/operating_system/feature-lifecycle.md`
    - `docs/operating_system/stage-lifecycle.md`
    - `docs/operating_system/publication-workflow.md`
  readme: `README.md`
  generated:
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_dependency_graph.yaml`
    - `docs/generated/feature_capabilities_index.yaml`
    - `docs/generated/features_by_status.yaml`
    - `docs/generated/stages_index.yaml`
    - `docs/generated/stage_overview.md`
Generated refresh required: `yes`
Capability IDs:
- `all managed feature capabilities`
Invariant IDs:
- `none`
Spec needed: `yes`
Plan needed: `yes`

## Problem

Phase 1 gave this repo a truthful Option B pilot, but only for one feature and one
stage.

That means the repo is now in a more useful but still transitional state:

- `cv_system` and `cv_analysis` have a source/generated split
- the repo has a working architecture sync/check script
- tests prove the pilot contract and stale-file detection
- lifecycle docs acknowledge the pilot path

But most of the repo still behaves like pre-Mode-B architecture metadata:

- remaining features still lack `feature.source.yaml`
- remaining stages still rely on human-edited `docs/stages/*.yaml`
- discovery files are only partially grounded in the new source layer
- there is no repo-wide validator for adoption shape
- starter-expected root docs and `docs/intent/` are still missing
- metadata normalization is inconsistent across features and stages

If Phase 2 does not close that gap, the pilot becomes an isolated exception
instead of the start of a durable migration path.

## Goal

Move JOB-PROJECT from a pilot Option B state to a repo-wide operational Option B
state.

Phase 2 should:

- migrate all managed features to `feature.source.yaml`
- migrate all stages to `*.source.yaml`
- extend the generator so it owns repo-wide contracts, lineage, and discovery
- add validator-backed checks for adoption shape and stale generated outputs
- fill the starter-expected root-doc and intent surfaces
- keep shared-surface review and intentional divergence recording current

## Non-Goals

This phase does not:

- require immediate renaming of every underscore feature ID to kebab-case
- require full code-level metadata backfill on every file in the repo
- require generator support for every future lineage/history enrichment idea
- require public-repo publication changes beyond keeping the current governed surfaces accurate
- require removal of all legacy prose in one sweep if it can be preserved as explanation rather than competing truth

## Phase 1 Baseline

Phase 2 builds on the following already-proven baseline:

- `docs/features/cv_system/feature.source.yaml` is the pilot human-owned feature source
- `docs/stages/cv_analysis.source.yaml` is the pilot human-owned stage source
- `scripts/sync_architecture_docs.py` can generate pilot contracts, lineage, and discovery
- `tests/test_sync_architecture_docs.py` proves sync behavior and stale-file detection
- pilot-generated files are refreshable and checkable in CI-style flows

Phase 2 should preserve that baseline and generalize it rather than replacing it
with a different model.

## Target State

After Phase 2, the repo should have a consistent Mode B shape for all currently
managed features and stages.

### Feature target shape

Every managed feature folder should follow:

```text
docs/features/<feature_id>/
  feature.source.yaml
  <feature_id>.yaml
  lineage.generated.yaml
  history.md
```

Ownership:

- `feature.source.yaml` is human-owned
- `<feature_id>.yaml` is generated
- `lineage.generated.yaml` is generated
- `history.md` remains explanatory and may include generator-owned blocks later, but must not duplicate the feature contract as a competing truth

### Stage target shape

Every stage should follow:

```text
docs/stages/<stage_id>.source.yaml
docs/stages/<stage_id>.yaml
```

Ownership:

- `*.source.yaml` is human-owned
- `*.yaml` is generated

### Discovery target shape

`docs/generated/*` should be fully derivable from feature source, stage source,
and the generated contract assembly process.

At minimum, Phase 2 should leave these files script-owned and reproducible:

- `docs/generated/features_index.yaml`
- `docs/generated/feature_dependency_graph.yaml`
- `docs/generated/feature_capabilities_index.yaml`
- `docs/generated/features_by_status.yaml`
- `docs/generated/stages_index.yaml`
- `docs/generated/stage_overview.md`

### Root-doc and intent target shape

The repo should also include the starter-aligned cross-cutting explanatory
surfaces:

```text
docs/setup.md
docs/configuration.md
docs/usage.md
docs/pipeline.md
docs/architecture.md
docs/intent/README.md
docs/intent/project-charter.md
docs/intent/stakeholders.md
docs/intent/success-outcomes.md
docs/intent/constraints-and-non-goals.md
```

These files should explain the project and the repo method. They must not
replace feature/stage source as the architecture source of truth.

## Migration Principles

### 1. Source first, everywhere

For each feature or stage:

1. create or normalize the source file
2. generate the contract output
3. review the output
4. update surrounding docs to point at the new ownership model

Never declare a feature or stage migrated until the source file exists and the
generated output is reproducible.

### 2. Prefer truthful normalization over cosmetic parity

Starter alignment matters, but truthful local structure matters more than forced
cosmetic matching.

Example:

- temporary underscore feature IDs may remain if they are explicitly recorded and generator-safe
- capability IDs should move toward stable feature-qualified identifiers even if full naming cleanup is staged

### 3. Preserve explanation, remove duplicate truth

Legacy prose docs can remain when they explain why, tradeoffs, or flow.
They should be trimmed or rewritten when they restate contract facts that now
belong in source/generated lifecycle files.

### 4. Validation must become routine

By the end of Phase 2, the repo should be able to answer both questions with
commands:

- are generated architecture docs up to date?
- does the repo satisfy the adopted Mode B shape?

### 5. Divergence must stay explicit

Any deliberate difference from starter guidance should remain recorded in
`repo_config/adoption-mode.yaml`, including whether the difference is temporary,
accepted, or queued for a later phase.

## Scope

### In scope

- create `feature.source.yaml` for all managed features that still lack one
- create `docs/stages/*.source.yaml` for all stages that still lack one
- extend `scripts/sync_architecture_docs.py` from pilot scope to repo-wide scope
- extend tests to cover multiple features/stages plus discovery regeneration
- add a repo-wide adoption-shape validator or adapt the starter validator to this repo
- update lifecycle/governance docs to describe repo-wide reality instead of pilot-only behavior
- add starter-expected root docs and `docs/intent/`
- refresh generated discovery from the normalized source/generated model

### Out of scope

- repo-wide code annotation backfill for every implementation file
- full feature ID renaming campaign
- public-repo structural redesign
- advanced lineage automation from code ownership beyond what is needed for truthful generated outputs

## Proposed Design

### A. Feature migration set

Migrate the remaining feature folders:

- `admin_control_plane_core`
- `bounded_parallel_enrichment`
- `inspection_debugging`
- `multi_file_job_input`
- `pipeline_performance`
- `run_lifecycle_controls`
- `settings_system`
- `trigger_run_management`
- `ui_consistency_theming`

`cv_system` remains the template and should be normalized further only if the
same schema changes are applied across the full set.

Each feature source should include, at minimum:

- `feature_id`
- `name`
- `status`
- `type`
- `summary`
- `domains`
- `depends_on`
- `capabilities`
- `stage_participation`
- `refs`
- `keywords`

Freshness and revision details remain generated, not source-owned.

### B. Stage migration set

Migrate the remaining stages:

- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_generation`

`cv_analysis` remains the template.

Each stage source should include, at minimum:

- `stage_id`
- `name`
- `summary`
- `boundaries`
- `inputs`
- `outputs`
- `depends_on`
- `primary_features`
- `related_features`
- `refs`
- `keywords`

### C. Generator expansion

`scripts/sync_architecture_docs.py` should expand from pilot behavior to repo-wide behavior.

Required outputs:

- assemble feature contracts for every managed feature folder with source
- assemble lineage output for every managed feature folder with source
- assemble stage contracts for every stage with source
- regenerate all discovery files listed in this spec
- support `--check` for stale-file detection across the full managed set

Design constraints:

- generator logic should skip unmanaged folders/files cleanly
- output ordering should be deterministic
- no generated file should need hand edits to stay current

### D. Validator adoption

Phase 2 should add a validator entry point, either by:

- adopting a repo-local version of the starter validator, or
- implementing a repo-specific validator that checks the same Mode B shape principles

The validator should catch at least:

- missing `feature.source.yaml` for managed features
- missing `lineage.generated.yaml` after sync
- missing `*.source.yaml` for managed stages
- stale generated contracts/discovery
- missing required root docs and intent docs
- contradictions between `repo_config/adoption-mode.yaml` and actual repo state where practical

### E. Root-doc and intent surfaces

Phase 2 should add the missing explanatory layers:

- `docs/setup.md`
- `docs/configuration.md`
- `docs/usage.md`
- `docs/pipeline.md`
- `docs/architecture.md`
- `docs/intent/README.md`
- `docs/intent/project-charter.md`
- `docs/intent/stakeholders.md`
- `docs/intent/success-outcomes.md`
- `docs/intent/constraints-and-non-goals.md`

These should be concise, stable, and source-like. They should not become change
logs or duplicate the feature/stage contracts.

## Execution Strategy

Phase 2 should be implemented in batches rather than as one undifferentiated
sweep.

### Batch 1: Schema finalization

- confirm the pilot source schemas are the repo-wide template
- make any needed schema refinements once, before migrating the rest
- update tests to lock the schema behavior

### Batch 2: Remaining feature migration

- create source files for remaining managed features
- generate feature contracts and lineage outputs
- review and trim conflicting legacy contract content

### Batch 3: Remaining stage migration

- create source files for remaining stages
- generate stage contracts
- align stage references to the migrated feature sources

### Batch 4: Discovery + validator expansion

- regenerate the full discovery layer
- add repo-wide stale-file and adoption-shape validation
- update CI-style verification commands in docs if needed

### Batch 5: Root-doc and intent completion

- add the starter-expected root docs
- add `docs/intent/`
- make sure they link to, rather than compete with, lifecycle sources

### Batch 6: Shared-surface review refresh

- update `repo_config/adoption-mode.yaml`
- record what is now aligned, what remains deferred, and why

## Risks

### Risk 1: Bulk migration drifts away from the pilot contract

If feature/stage migrations are done ad hoc, the repo could end up with several
slightly different source schemas.

Mitigation:

- finalize schema behavior before bulk rollout
- keep tests on representative multi-feature and multi-stage cases

### Risk 2: Legacy generated files still get edited manually

Even after migration, contributors may keep editing generated YAML directly.

Mitigation:

- validator should flag stale outputs
- lifecycle docs should state edit ownership clearly
- generated file headers/comments can be added later if needed

### Risk 3: Root docs become duplicate architecture truth

Adding `docs/setup.md`, `docs/pipeline.md`, and `docs/architecture.md` could
recreate the same duplication problem at a different level.

Mitigation:

- treat them as explanatory navigation layers
- link to source/generated lifecycle files rather than restating contract tables exhaustively

### Risk 4: Validator is too strict too early

If validation enforces constraints before migration is complete, it may create
noise and slow the rollout.

Mitigation:

- land validator with scoped phases or clear exceptions
- only flip to repo-wide enforcement when the migration batch is complete

## Acceptance Criteria

Phase 2 is complete when all of the following are true:

1. Every managed feature folder has `feature.source.yaml`, generated `<feature_id>.yaml`, and `lineage.generated.yaml`.
2. Every stage has `*.source.yaml` plus generated `*.yaml`.
3. `scripts/sync_architecture_docs.py` regenerates repo-wide contracts and discovery deterministically.
4. A validator command can check repo-wide Mode B adoption shape and fail on missing or contradictory required surfaces.
5. `docs/generated/*` are refreshable and treated as generated-only outputs.
6. The required root docs and `docs/intent/` files exist and describe the repo truthfully.
7. `repo_config/adoption-mode.yaml` reflects the post-Phase-2 alignment state and any remaining intentional divergences.

## Validation Strategy

Minimum verification for implementation:

- `python -m pytest tests/test_sync_architecture_docs.py`
- `python scripts/sync_architecture_docs.py`
- `python scripts/sync_architecture_docs.py --check`
- `python scripts/validate_adoption_shape.py`
- `git diff --check`

If the validator lands under a different path, the plan should update these
commands explicitly.

## Deferred To Later Phases

The following may remain deferred after Phase 2 if they are recorded
explicitly:

- kebab-case feature ID migration
- deeper code/test/doc metadata backfill for richer lineage automation
- partially generated `history.md` blocks
- stronger CI integration for adoption-shape enforcement

## Open Questions

1. Should underscore feature IDs remain an accepted local divergence through Phase 2, or should the validator require a naming migration plan?
2. Should unmanaged or experimental feature folders be explicitly listed in `repo_config/adoption-mode.yaml` so the validator can ignore them deterministically?
3. Should `history.md` stay fully human-authored in Phase 2, or should we reserve generated block markers now even if no history generator lands yet?

