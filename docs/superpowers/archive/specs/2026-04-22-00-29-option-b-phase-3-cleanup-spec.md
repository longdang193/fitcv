---
feature_type: modify
feature_name: none
status: completed
summary: "Define the Phase 3 cleanup after the repo-wide Mode B rollout by tightening naming conventions, enriching lineage outputs, and making sync and validation enforcement routine."
invariants:
  - "the private repo remains the development source of truth"
  - "feature and stage meaning stays source-owned in docs/features/*/feature.source.yaml and docs/stages/*.source.yaml"
  - "generated contracts, lineage, and discovery remain script-owned outputs"
  - "Phase 3 should tighten deferred cleanup areas without reopening the completed Phase 2 source/generated rollout"
  - "starter-aligned shared-surface review remains explicit in repo_config/adoption-mode.yaml"
---

# Option B Phase 3 Cleanup Spec

## Triage

Layer: `operating_system`  
Feature type: `MODIFY`  
Summary: Clean up the remaining post-rollout Option B gaps by deciding and enforcing feature/capability naming conventions, deepening generated lineage, and integrating architecture sync/validation into routine enforcement paths.  
Reasoning: Phase 2 completed the repo-wide source/generated rollout, but it intentionally left several cleanup items deferred so the migration could land safely. Those deferred items now define the next bounded phase of work.  
Invariants:
- The private repo remains the development source of truth.
- Human-owned lifecycle meaning stays in feature and stage source files.
- Generated feature contracts, stage contracts, lineage, and discovery stay script-owned outputs.
- Phase 3 should reduce intentional divergence and operational drift, not replace the Phase 2 model.
- Any remaining divergence from starter guidance must stay explicit and reviewable in `repo_config/adoption-mode.yaml`.
Dependencies:
- `docs/superpowers/archive/specs/2026-04-21-23-50-option-b-migration-spec.md`
- `docs/superpowers/archive/specs/2026-04-21-23-54-option-b-phase-2-rollout-spec.md`
- `docs/features/*/feature.source.yaml`
- `docs/features/*/lineage.generated.yaml`
- `docs/stages/*.source.yaml`
- `docs/generated/*`
- `repo_config/adoption-mode.yaml`
- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`
- `tests/test_sync_architecture_docs.py`
- `tests/test_validate_adoption_shape.py`
- repo hook and CI entrypoints that should eventually run these checks
Affected stages:
- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`
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
    - `docs/architecture.md`
    - `docs/configuration.md`
    - `docs/usage.md`
    - `docs/pipeline.md`
    - `docs/operating_system/repo-governance.md`
    - `docs/operating_system/feature-lifecycle.md`
    - `docs/operating_system/stage-lifecycle.md`
    - `docs/operating_system/publication-workflow.md`
  readme: `README.md`
  generated:
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_dependency_graph.yaml`
    - `docs/generated/feature_capabilities_index.yaml`
    - `docs/generated/feature_overview.md`
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

The repo now has a truthful repo-wide Mode B shape, but the cleanup layer after
that rollout is still incomplete.

The main deferred gaps are:

1. feature IDs still use local underscore names rather than a settled normalization contract
2. capability entries are only partially normalized and still mix string-only and structured forms
3. lineage generation is intentionally lightweight and mostly source-ref based
4. sync and validation commands are available, but they are not yet guaranteed in CI or hook flows
5. `repo_config/adoption-mode.yaml` still records these areas as intentional local deferrals rather than resolved policy

That means the repo is structurally migrated, but not yet fully tightened.

## Goal

Turn the completed Mode B rollout into a more opinionated, lower-drift operating
state.

Phase 3 should:

- settle the naming and ID policy for managed feature and capability metadata
- make generated lineage more useful for traceability and drift review
- move architecture sync/validation from optional manual commands toward standard enforcement
- update governance and adoption records so remaining divergence is smaller and more explicit

## Non-Goals

This phase does not:

- redo the Phase 2 source/generated migration
- require a public-repo publication redesign
- require full semantic extraction from code for every lineage fact
- require a big-bang rename if a staged compatibility bridge is safer
- require replacing human-authored history docs with a fully generated history system

## Current Baseline

After Phase 2, the repo already has:

- repo-wide `feature.source.yaml` coverage
- repo-wide `*.source.yaml` stage coverage
- generated contracts and discovery refreshed by `scripts/sync_architecture_docs.py`
- repo-wide shape validation via `scripts/validate_adoption_shape.py`
- starter-aligned root docs and `docs/intent/`

The remaining work is therefore cleanup and hardening, not foundational migration.

## Cleanup Targets

### A. Naming and ID normalization

The repo still uses underscore feature IDs like `cv_system` and a mixed
capability model:

- some capabilities are structured with `capability_id`, `name`, and `summary`
- some capabilities remain string-only labels

Phase 3 should decide one of these policies:

1. keep underscore feature IDs as a long-term accepted local divergence and make that explicit in validation and docs
2. define a staged migration toward starter-style kebab-case feature IDs

Regardless of feature-ID policy, Phase 3 should normalize capability shape
toward structured entries wherever capability-level traceability matters.

### B. Richer generated lineage

Current `lineage.generated.yaml` files are useful but thin. They mostly expose:

- source path
- generated contract path
- basic dependencies
- some refs and stage participation

Phase 3 should improve lineage so it better supports:

- capability-level traceability
- stage participation summaries
- normalized refs grouped by type
- clearer evidence for why a feature contract currently looks the way it does

This should stay bounded and deterministic. It does not need to become a full
knowledge graph.

### C. Routine enforcement

The repo can already run:

- `python scripts/sync_architecture_docs.py --check`
- `python scripts/validate_adoption_shape.py`

Phase 3 should make these part of normal enforcement, for example by wiring
them into:

- repo hooks
- CI jobs
- documented pre-merge verification steps

The goal is to make drift visible automatically instead of relying on memory.

## Target State

After Phase 3, the repo should be able to state all of the following
truthfully:

1. managed feature and capability naming policy is explicit and enforced
2. generated lineage gives a useful, structured traceability view rather than a minimal placeholder
3. stale architecture docs and broken Mode B shape are caught by routine automation
4. `repo_config/adoption-mode.yaml` reflects the reduced divergence set clearly

## Proposed Design

### 1. Naming-policy decision layer

Add an explicit naming policy to the architecture-doc contract.

At minimum, that policy should define:

- allowed feature-ID format
- allowed capability-ID format
- whether string-only capabilities are still allowed
- whether compatibility aliases are needed during cleanup

If underscore feature IDs remain, the validator should check consistency rather
than pretending a kebab-case migration already happened.

### 2. Capability normalization

Promote capability entries that still use plain strings into structured entries
when they materially affect:

- discovery
- lineage
- stage participation
- reviewability

Phase 3 does not need to over-model trivial capability labels, but it should
reduce mixed representation where it harms generated outputs.

### 3. Lineage model enrichment

Extend `scripts/sync_architecture_docs.py` so `lineage.generated.yaml`
includes a stronger assembled view, potentially including:

- capability summaries
- capability IDs
- stage-role rollups
- normalized ref buckets
- dependency rollups
- optional markers for structured-vs-legacy capability entries

The output should remain deterministic, reviewable, and cheap to regenerate.

### 4. Validation expansion

Extend `scripts/validate_adoption_shape.py` so it can catch:

- inconsistent feature-ID naming versus the chosen policy
- inconsistent capability-ID format where structured capability entries exist
- unexpected mixed capability shapes where the policy forbids them
- missing or malformed lineage fields once the richer model lands

### 5. Enforcement integration

Update repo automation so the architecture checks are run in the places where
drift matters most.

Minimum target:

- pre-merge CI path runs architecture freshness and adoption-shape validation
- governance docs name those checks as standard expectations

Optional target:

- local hook integration for earlier feedback

## Execution Strategy

Phase 3 should proceed in this order:

### Batch 1: Policy decision

- choose the feature-ID policy
- choose the capability-shape policy
- record temporary compatibility rules if needed

### Batch 2: Generator and validator expansion

- enrich lineage generation
- expand validation for naming and lineage structure
- extend tests before bulk metadata cleanup

### Batch 3: Metadata normalization

- normalize capability entries where needed
- apply any selected naming bridge or alias strategy
- regenerate contracts and lineage

### Batch 4: Enforcement integration

- wire checks into CI or hook flows
- update governance and verification docs
- refresh `repo_config/adoption-mode.yaml`

## Risks

### Risk 1: Cleanup turns into a second migration

If Phase 3 tries to rename every identifier and backfill every possible lineage
fact at once, it could destabilize the already-complete Phase 2 rollout.

Mitigation:

- keep this phase bounded to policy, lineage, and enforcement cleanup
- use compatibility bridges where needed

### Risk 2: Over-modeling lineage

If lineage becomes too ambitious, it may become noisy or expensive to maintain.

Mitigation:

- keep lineage assembled from already-owned sources first
- prefer deterministic summaries over speculative derived facts

### Risk 3: Validator strictness outruns metadata cleanup

If new validation rules land before metadata is normalized, the repo may fail in
a noisy or frustrating way.

Mitigation:

- add tests first
- expand the validator in lockstep with cleanup
- allow explicitly documented transitional exceptions if needed

### Risk 4: Naming policy remains ambiguous

If the repo neither commits to underscore IDs nor defines a migration path,
future contributors will keep guessing.

Mitigation:

- force a clear policy decision in Batch 1
- document it in governance plus adoption-mode records

## Acceptance Criteria

Phase 3 is complete when all of the following are true:

1. Feature and capability naming policy is explicit in docs and enforced by validation.
2. `lineage.generated.yaml` contains a materially richer traceability model than the current lightweight version.
3. Tests cover the expanded lineage and validation behavior.
4. Architecture freshness and adoption-shape checks are part of standard enforcement, not just optional manual commands.
5. `repo_config/adoption-mode.yaml` reflects the post-cleanup divergence state accurately.

## Validation Strategy

Minimum verification for implementation:

- `python -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py`
- `python scripts/sync_architecture_docs.py`
- `python scripts/sync_architecture_docs.py --check`
- `python scripts/validate_adoption_shape.py`
- the relevant CI or hook path that runs those checks once integrated
- `git diff --check`

## Open Questions

1. Should underscore feature IDs remain the stable long-term local policy, or should Phase 3 only introduce aliases and defer real renaming again?
2. Should string-only capability entries remain allowed for small features, or should all managed features move to structured capability objects?
3. How much lineage enrichment is enough before diminishing returns outweigh the review value?
4. Should enforcement land in CI only first, or in both CI and local hooks during the same phase?

