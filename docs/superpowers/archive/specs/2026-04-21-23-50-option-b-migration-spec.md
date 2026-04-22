---
feature_type: modify
feature_name: none
status: completed
summary: "Define the staged Option B migration for JOB-PROJECT so managed architecture metadata, shared starter-controlled repo surfaces, and generated outputs move to the latest starter-aligned contract together."
invariants:
  - "the private repo remains the development source of truth"
  - "Mode B migration must not leave product metadata, shared repo-control surfaces, and generated outputs in contradictory states"
  - "generated contracts, lineage, and discovery remain outputs rather than human-owned truth"
  - "starter-owned shared repo-control surfaces may diverge locally only when the divergence is intentional and recorded"
---

# Option B Migration Spec

## Triage

Layer: `operating_system`  
Feature type: `MODIFY`  
Summary: Migrate JOB-PROJECT to a starter-aligned Mode B shape by introducing human-owned feature/stage source files, generator-backed outputs, and a recorded shared-surface sync contract.  
Reasoning: The repo already has feature folders, stage contracts, generated discovery, adapter sync, and publication workflow, but it still treats generated lifecycle docs as editable truth, lacks the source/generated split, and only partially adopts the latest starter Mode B governance.  
Invariants:
- The private repo remains the development source of truth.
- Product architecture meaning must move into source files before generated outputs are treated as canonical.
- Shared repo-control surfaces must be reviewed against the adopted starter baseline and any intentional local divergence must be recorded.
- Generated files must not become the human-owned source of truth during or after migration.
- Mode B migration must be phased so each checkpoint leaves the repo in a truthful, reviewable state.
Dependencies:
- `repo_config/adoption-mode.yaml`
- `repo_config/publication-config.json`
- `repo_config/agent-adapter-mappings.json`
- `docs/operating_system/repo-governance.md`
- `docs/operating_system/feature-lifecycle.md`
- `docs/operating_system/stage-lifecycle.md`
- `docs/operating_system/publication-workflow.md`
- `scripts/sync_agent_adapters.ps1`
- `scripts/verify_agent_adapters.ps1`
- `scripts/publish_public_repo.ps1`
- `docs/features/*/`
- `docs/stages/*`
- `docs/generated/*`
Affected stages:
- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`
Affected features:
- `cv_system`
- `pipeline_performance`
- `bounded_parallel_enrichment`
- `settings_system`
- `admin_control_plane_core`
- `inspection_debugging`
- `trigger_run_management`
- `run_lifecycle_controls`
- `multi_file_job_input`
- `ui_consistency_theming`
Primary lens: `cross-cutting`
Affected docs:
  feature_source: `none`
  feature_yaml: `none`
  feature_lineage: `none`
  feature_history: `none`
  stage_source: `none`
  stage_contract: `none`
  feature_docs: `none`
  cross_cutting_docs:
    - `docs/operating_system/repo-governance.md`
    - `docs/operating_system/feature-lifecycle.md`
    - `docs/operating_system/stage-lifecycle.md`
    - `docs/operating_system/publication-workflow.md`
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

JOB-PROJECT is close enough to the starter's Mode B shape to be misleading.

It already has:

- managed-looking feature folders under `docs/features/`
- stage contracts under `docs/stages/`
- generated discovery under `docs/generated/`
- repo governance and publication workflow docs
- adapter sync and verification scripts
- starter-synced repo-local skills
- a recorded `starter_sync` baseline in `repo_config/adoption-mode.yaml`

But it still has material gaps against real Mode B:

1. feature folders do not yet contain `feature.source.yaml`
2. feature folders do not yet contain `lineage.generated.yaml`
3. stage meaning still lives in generated-looking files such as `docs/stages/cv_analysis.yaml`
4. there is no architecture sync/check script equivalent to `scripts/sync_architecture_docs.py`
5. lifecycle docs still describe a target model that the repo has not fully implemented
6. required root docs and the intent layer expected by the starter are still missing
7. the repo has not yet normalized capability IDs and metadata markers to a source-first Mode B contract

This creates a half-migration risk:

- humans may edit generated contract files directly because there is no source layer
- generated discovery may be trusted without a generator-backed derivation path
- future starter syncs may update governance while product metadata stays structurally stale
- validation cannot reliably distinguish intentional local divergence from incomplete migration

## Goal

Define a phased, reviewable migration from the current partial architecture-doc shape to a genuine starter-aligned Mode B shape for JOB-PROJECT.

The migration should:

- move product feature meaning into `feature.source.yaml`
- move stage meaning into `*.source.yaml`
- generate feature contracts, stage contracts, lineage, and discovery from source
- keep shared repo-control surfaces aligned with the adopted starter baseline
- make local divergence explicit instead of accidental
- leave the repo in truthful states at each checkpoint rather than requiring one large cutover

## Non-Goals

This spec does not:

- require a single-commit big-bang migration of every feature, stage, and metadata marker
- require byte-for-byte mirroring of starter repo-control files
- require immediate renaming of every feature ID if a temporary bridge is safer
- define every implementation detail of the future generator internals
- convert every existing cross-cutting doc into public-safe form as part of the Mode B migration itself

## Current-State Assessment

### What already aligns

- `repo_config/` now exists and is the live source for publication and adapter mappings
- `repo_config/adoption-mode.yaml` now records the starter baseline and shared-surface review classes
- shared skills have been synced from the latest `project-OS-starter`
- publication and adapter scripts now consume repo config rather than duplicating their own hardcoded mappings
- `docs/operating_system/` has been updated to describe the shared-surface sync contract and the intended source/generated split

### What is still not Option B-complete

- `docs/features/<feature_id>/<feature_id>.yaml` remains the editable lifecycle source in practice
- feature capabilities are still prose-heavy and not consistently feature-qualified IDs
- `docs/stages/*.yaml` is still human-authored in practice
- there is no source-backed generator that owns:
  - feature contracts
  - stage contracts
  - lineage outputs
  - discovery outputs
- required root docs under `docs/` do not exist yet
- `docs/intent/` does not exist yet
- the starter validator is not yet adopted

## Target State

After migration, JOB-PROJECT should have this architecture-doc shape.

### Feature shape

Each real managed feature should use:

```text
docs/features/<feature_id>/
  feature.source.yaml
  <feature_id>.yaml
  lineage.generated.yaml
  history.md
```

Ownership:

- `feature.source.yaml` is the human-owned feature meaning
- `<feature_id>.yaml` is a generated or normalized current-state contract
- `lineage.generated.yaml` is generated evidence and traceability
- `history.md` remains human-authored except for explicitly generated blocks if adopted later

### Stage shape

Each real stage should use:

```text
docs/stages/<stage_id>.source.yaml
docs/stages/<stage_id>.yaml
```

Ownership:

- `*.source.yaml` is the human-owned stage source
- `*.yaml` is the generated current stage contract

### Shared repo-control shape

The repo should keep these starter-controlled surface classes reviewable:

- `repo_config`
- `operating_system_docs`
- `skills`
- `adapters`
- `generated_instruction_surfaces`
- `validation_and_sync_scripts`

The review baseline and intentional divergences should remain recorded in
`repo_config/adoption-mode.yaml`.

### Root-doc and intent shape

The repo should also have:

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

These documents do not replace feature/stage lifecycle sources. They give the
starter's required cross-cutting explanation and project-purpose layer.

## Migration Principles

### 1. Source first, outputs second

Never migrate generated contracts first and treat the missing source layer as a
future cleanup.

The order must be:

1. create or normalize the human-owned source file
2. run the generator
3. review the generated outputs
4. remove the old human-edited generated file from the source-of-truth role

### 2. Shared surfaces move with product metadata

Mode B migration is not only about feature folders. Starter-owned control
surfaces must move forward with it.

That means:

- repo config
- governance docs
- skills
- adapters
- generated instruction surfaces
- validation and sync scripts

must stay reviewable against the adopted starter baseline while the product
metadata migration happens.

### 3. Prefer pilot-first migration

Do not convert every feature and stage at once.

The repo should first establish one truthful end-to-end path:

- one feature source
- one stage source
- one generator path
- one discovery refresh flow
- one code/config/test metadata path

Then scale that pattern to the rest of the repo.

### 4. Divergence is allowed, drift is not

If JOB-PROJECT intentionally differs from the starter because of local file
layout, `codex/` root usage, or FitCV-specific public mirror needs, that is
valid.

But the divergence must be:

- explicit
- localizable by path
- justified in `starter_sync`

## Proposed Migration Phases

### Phase 0: Governance Baseline

Purpose:

- finish the shared-surface contract adoption before deeper product migration

Includes:

- `repo_config/*`
- `docs/operating_system/*`
- `.agents/skills/*`
- adapter scripts and mappings
- generated instruction surfaces

Exit criteria:

- starter baseline ref recorded
- reviewed surface classes recorded
- current divergences documented
- adapter sync and dry-run publication succeed from repo-config inputs

Status:

- mostly complete on this branch

### Phase 1: Architecture Source Layer Pilot

Purpose:

- prove the source/generated split on one feature and one stage

Recommended pilot:

- feature: `cv_system`
- stage: `cv_analysis`

Work:

1. create `docs/features/cv_system/feature.source.yaml`
2. create `docs/stages/cv_analysis.source.yaml`
3. define the minimum generator behavior needed to produce:
   - `docs/features/cv_system/cv_system.yaml`
   - `docs/features/cv_system/lineage.generated.yaml`
   - `docs/stages/cv_analysis.yaml`
4. document what stays human-authored versus generated
5. keep the old contract content only as an input to the new source split, not as a parallel source of truth

Exit criteria:

- one feature and one stage follow the full source/generated shape
- the generated outputs are reproducible from source
- there is no ambiguity about which files humans edit

### Phase 2: Generator and Discovery Backbone

Purpose:

- make discovery and contract generation reproducible for the repo

Work:

1. add the repo's architecture sync/check script
2. define its inputs and outputs
3. refresh generated discovery from the new source layer
4. add tests for the generator behavior
5. prepare for future adoption of a stronger validator

Required generated outputs:

- feature contracts
- stage contracts
- lineage outputs when adopted
- generated discovery indexes

Exit criteria:

- generated files can be refreshed from source
- generated outputs are not hand-maintained
- the script becomes the canonical refresh path

### Phase 3: Feature and Stage Rollout

Purpose:

- migrate the remaining managed features and stages to source-first Mode B

Work:

1. create `feature.source.yaml` for each real product feature
2. create `*.source.yaml` for each stage
3. normalize feature/stage links
4. generate contracts and lineage
5. remove any remaining source-of-truth ambiguity

Special attention:

- `settings_system`
- `pipeline_performance`
- `bounded_parallel_enrichment`
- control-plane feature folders under `fitcv_cp`

Exit criteria:

- every managed feature has the required folder shape
- every stage in scope has a source file and generated contract
- generated discovery matches the new source layer

### Phase 4: Metadata Normalization

Purpose:

- align code/config/test/doc metadata with canonical feature and capability identifiers

Work:

1. decide ID strategy:
   - temporary underscore bridge, or
   - full kebab-case migration
2. normalize capability IDs to stable feature-qualified identifiers
3. update source metadata markers across:
   - code
   - config
   - tests
   - scripts
   - docs
4. ensure lineage generation can rely on those identifiers

Exit criteria:

- metadata references canonical feature IDs
- capability identifiers are stable and feature-qualified
- lineage generation is not forced to infer feature meaning from prose-only labels

### Phase 5: Starter Validation and Required Docs

Purpose:

- close the remaining starter contract gaps once the source/generated model is real

Work:

1. add `docs/intent/`
2. add required root docs under `docs/`
3. adopt or adapt `scripts/validate_adoption_shape.py`
4. decide which starter validator rules apply immediately versus with local divergence

Exit criteria:

- required root docs exist and are substantive
- the intent layer exists
- the validator can run meaningfully against the repo's actual Mode B shape

## Detailed Design Decisions

### Feature-source schema

The repo should move toward a feature source shape that is semantically stable
and not overloaded with generated freshness values.

Preferred fields:

- `feature_id`
- `name`
- `status`
- `type`
- `summary`
- `invariants`
- `domains`
- `depends_on`
- `capabilities`
- `stage_participation`
- optional `lineage_exceptions`

Generated-only values such as assembled refs, timestamps, revision counters,
and derived dependency views should not be manually maintained in the source.

### Capability identifiers

Current prose-heavy capability lists should migrate to a stable structured form.

Preferred shape:

```yaml
capabilities:
  - capability_id: cv_system.structured-cv-generation
    name: Structured CV Generation
    summary: Produce the structured CV artifact and rendered markdown output.
```

If a temporary bridge is needed, it should be explicit and short-lived rather
than silently treating prose bullets as permanent stable IDs.

### Stage ownership

Stage sources should own:

- stage identity
- purpose
- boundaries
- inputs and outputs
- primary/supporting feature relationships

Feature sources should own:

- feature meaning
- stage participation
- feature capabilities within stages

### Shared-surface review record

`repo_config/adoption-mode.yaml` should remain the single machine-readable
adoption source and keep the `starter_sync` block rather than creating a second
adjacent record unless a later validator tool requires that split.

Required fields:

- `starter_baseline_ref`
- `last_shared_surface_review_at`
- `reviewed_surface_classes`
- optional `divergences`

### Required-doc adoption

The required root docs should be treated as cross-cutting project docs, not as
replacements for feature/stage lifecycle sources.

That means:

- `docs/pipeline.md` explains the cross-feature flow
- `docs/architecture.md` explains the system structure
- `docs/configuration.md` explains config ownership and usage
- `docs/setup.md` and `docs/usage.md` explain operator/developer entry points
- `docs/intent/*` explains project purpose rather than migration mechanics

## Risks

### Risk 1: Source/generated dual truth

If the migration leaves both the old generated contract and the new source file
human-edited, the repo becomes less trustworthy than before.

Mitigation:

- pilot one feature/stage end-to-end first
- document editable versus generated files clearly
- adopt generator-backed outputs before broad rollout

### Risk 2: Over-eager ID migration

A full feature ID renaming sweep could create unnecessary churn across docs,
tests, config, and runtime metadata.

Mitigation:

- decide explicitly whether ID normalization is phase-1 critical or phase-4 work
- if bridging, record it as a temporary divergence or migration debt item

### Risk 3: Validator before reality

Adopting the starter validator before the repo actually has the source/generated
split will create noise instead of trust.

Mitigation:

- keep validator adoption deferred until after the pilot and generator backbone
- document the deferral in `starter_sync`

### Risk 4: Shared-surface sync without product migration

The repo could look governance-aligned while still not having a real Mode B
product metadata shape.

Mitigation:

- treat shared-surface sync as Phase 0, not the whole migration
- require a follow-on implementation plan that covers the product source layer

## Validation Strategy

Each phase should have validation that matches its scope.

### Phase 0 validation

- `.\scripts\sync_agent_adapters.ps1`
- `.\scripts\verify_agent_adapters.ps1`
- `.\scripts\publish_public_repo.ps1`
- `git diff --check`

### Phase 1 validation

- generator pilot tests
- review of one feature source and one stage source
- review that generated outputs are reproducible and not manually edited

### Phase 2 validation

- architecture sync/check script runs successfully
- generated discovery refreshes from source
- tests cover generator input/output behavior

### Phase 3 and 4 validation

- all managed features have source files
- all in-scope stages have source files
- no authoritative flat feature YAML remains
- metadata markers reference canonical feature/capability IDs

### Phase 5 validation

- required root docs exist and are substantive
- intent layer exists
- adoption validator runs meaningfully against the repo

## Acceptance Criteria

This migration is complete when:

- `repo_config/adoption-mode.yaml` truthfully records Mode B and starter shared-surface review
- shared repo-control surfaces are current to the adopted starter baseline or intentionally diverged
- every managed feature uses `feature.source.yaml`
- every in-scope stage uses `*.source.yaml`
- generated contracts, lineage, and discovery come from a canonical sync/check workflow
- generated outputs are not hand-maintained as truth
- code/config/test/doc metadata points to canonical feature and capability identifiers
- required root docs and the intent layer exist with real project-specific content
- the validator path adopted by the repo can meaningfully enforce the chosen Mode B shape

## Open Questions

1. Should feature IDs remain underscore-based during the first migration pass, or is early kebab-case normalization worth the churn?
2. Which existing generated discovery files should remain public-export candidates once the source/generated split is complete?
3. Should `history.md` remain fully human-authored in this repo, or adopt partial generated blocks later?
4. Should lineage generation be introduced in the pilot or deferred until the generator backbone phase?

## Recommendation

Proceed with a pilot-first Mode B migration.

The first implementation plan should cover:

1. `cv_system` feature source creation
2. `cv_analysis` stage source creation
3. a minimal architecture sync/check script
4. regeneration of the pilot contracts and discovery
5. a documented rule for which files humans now edit

That pilot should become the template for the remaining repo-wide rollout rather
than trying to migrate every feature, stage, and metadata marker in one pass.
