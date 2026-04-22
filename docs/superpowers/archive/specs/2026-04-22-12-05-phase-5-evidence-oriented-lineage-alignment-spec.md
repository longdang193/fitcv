---
layer: operating_system
artifact_type: spec
status: completed
parent_workstream: none
targets:
  - docs/features/*/feature.source.yaml
  - docs/features/*/<feature_id>.yaml
  - docs/features/*/lineage.generated.yaml
  - docs/features/*/history.md
  - docs/generated/*
  - scripts/sync_architecture_docs.py
  - scripts/validate_adoption_shape.py
  - tests/test_sync_architecture_docs.py
  - tests/test_validate_adoption_shape.py
  - docs/operating_system/feature-lifecycle.md
  - repo_config/adoption-mode.yaml
related_features:
  - admin_control_plane_core
  - bounded_parallel_enrichment
  - cv_system
  - inspection_debugging
  - multi_file_job_input
  - pipeline_performance
  - run_lifecycle_controls
  - settings_system
  - trigger_run_management
  - ui_consistency_theming
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 5 Evidence-Oriented Lineage Alignment Spec

## Triage

Layer: `operating_system`  
Feature type: `CHANGE`  
Summary: Align JOB-PROJECT's Mode B feature-folder model to the newer `project-OS-starter` evidence-oriented lineage contract and managed-feature migration target.  
Reasoning: The latest starter guidance now makes the target feature-folder contract explicit. JOB-PROJECT currently uses the right filenames and has completed Phase 4 metadata correction, but it still carries an older managed-folder shape in `feature.source.yaml`, `<feature_id>.yaml`, and `lineage.generated.yaml`.  
Invariants:

- The private repo remains the development source of truth.
- `feature.source.yaml` stays human-owned and semantic.
- `<feature_id>.yaml` stays generated and assembled current-state contract output.
- `lineage.generated.yaml` stays generated feature-local lineage evidence, not a refs summary.
- Generated discovery remains script-owned output.
- Starter shared-surface review remains tracked in `repo_config/adoption-mode.yaml`.

Dependencies:

- `C:\Users\HOANG PHI LONG DANG\repos\project-OS-starter` commit `f03977b279e714d00e04cef8a686b8ae67d8208a`
- `project-OS-starter/docs/operating_system/project-adoption-migration-guide.md`
- `project-OS-starter/docs/superpowers/specs/2026-04-22-lineage-generated-schema-contract-spec.md`
- `project-OS-starter/docs/superpowers/specs/2026-04-22-feature-folder-migration-target-spec.md`
- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`

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

- feature_source: `docs/features/*/feature.source.yaml`
- feature_yaml: `docs/features/*/<feature_id>.yaml`
- feature_lineage: `docs/features/*/lineage.generated.yaml`
- feature_history: `docs/features/*/history.md`
- stage_source: `none`
- stage_contract: `docs/stages/*.yaml`
- feature_docs: `none`
- cross_cutting_docs: `none`
- operating_system_docs:
  - `docs/operating_system/feature-lifecycle.md`
- readme: `none`
- generated:
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_dependency_graph.yaml`
  - `docs/generated/feature_capabilities_index.yaml`
  - `docs/generated/feature_overview.md`
  - `docs/generated/features_by_status.yaml`
  - `docs/generated/stages_index.yaml`
  - `docs/generated/stage_overview.md`

Generated refresh required: `yes`  
Capability IDs: `managed feature capability IDs`  
Invariant IDs: `none`  
Spec needed: `yes`  
Plan needed: `yes`

## Starter Baseline

The latest starter guidance is now anchored at commit:

- `f03977b279e714d00e04cef8a686b8ae67d8208a`
- title: `Clarify managed feature migration targets`

That commit updates the migration guide and adds two new starter specs:

- `2026-04-22-lineage-generated-schema-contract-spec.md`
- `2026-04-22-feature-folder-migration-target-spec.md`

Together, they define a newer Mode B target that is stricter than the shape
currently used by JOB-PROJECT.

## Problem

JOB-PROJECT now has:

- managed feature folders
- curated capability IDs
- required file metadata on behavioral scripts/tests
- generated contracts, lineage, and discovery

That is enough to satisfy the older repo-local Mode B shape, but it is not
enough to satisfy the newer starter target.

The main remaining drift is structural:

1. `feature.source.yaml` is still carrying older contract-adjacent fields such
   as `owner`, `primary_stage`, `stages`, `refs`, and `keywords`
2. generated feature contracts still mirror too much of the old source shape
3. `lineage.generated.yaml` is still using the older summary-style top-level
   schema with keys like:
   - `generated_contract`
   - `naming_policy`
   - `capability_shape`
   - `capability_ids`
   - `refs`
   - `refs_by_type`
4. capability entries in source still use the older `name` and `summary`
   emphasis instead of the newer starter-style `statement` and `state`
5. feature history is still manual rather than aligned to the starter's
   partial-generated history target

This means JOB-PROJECT currently has starter-shaped filenames but not the full
starter-aligned artifact contract.

## Goal

Bring JOB-PROJECT onto the newer starter-aligned managed-feature target so that:

1. `feature.source.yaml` becomes a smaller semantic source
2. `<feature_id>.yaml` becomes the assembled generated contract surface
3. `lineage.generated.yaml` becomes canonical evidence-oriented lineage output
4. feature capability entries align with the newer starter source model
5. validators and generator make the newer target enforceable rather than
   optional

## Non-Goals

This phase does not:

- change the repo's underscore feature-ID policy unless the starter now
  requires it for this repo's local divergence policy
- redesign stage contracts
- require full feature-history migration in the same batch if a staged bridge
  is safer
- require a complete rewrite of every feature source by hand before automation
  exists
- remove all repo-local divergence from starter governance files

## Current JOB-PROJECT Drift Against New Starter Target

### 1. Feature source is still too large

Starter now says `feature.source.yaml` should keep only human-owned semantic
fields such as:

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
- `lineage_exceptions`

JOB-PROJECT still keeps older source-level fields such as:

- `owner`
- `primary_stage`
- `stages`
- `refs`
- `keywords`

These should be removed, relocated, or derived into generated outputs.

### 2. Generated contract still looks too much like a copied source file

The newer starter target expects `<feature_id>.yaml` to be the generated
assembled current-state contract. In JOB-PROJECT, the generated contract still
resembles a lightly mirrored source file and carries older source-era fields.

### 3. Lineage is not yet evidence-oriented in the starter sense

Starter now explicitly rejects the older summary-style lineage shape. JOB-PROJECT
still uses exactly the top-level fields the starter now names as invalid for
managed-mode alignment.

### 4. Capability source shape is still older-style

Starter's newer migration target prefers capability entries like:

```yaml
capabilities:
  - capability_id: <feature_id>.<capability_slug>
    statement: <human-owned statement>
    state: active
```

JOB-PROJECT still uses:

- `capability_id`
- `name`
- `summary`

That is clearer than prose-derived IDs, but it still does not match the new
starter target.

### 5. History target is still pending

Starter now describes a partial-generated `history.md` pattern with:

- `# History`
- generated block markers
- `## Human Notes`

JOB-PROJECT has not yet adopted that target.

## Proposed Target State

After Phase 5, each managed feature should converge toward:

```text
docs/features/<feature_id>/
  feature.source.yaml
  <feature_id>.yaml
  lineage.generated.yaml
  history.md
```

With ownership split:

- `feature.source.yaml`: minimal human-owned semantic source
- `<feature_id>.yaml`: generated current-state contract with refs/freshness
- `lineage.generated.yaml`: generated evidence-oriented lineage
- `history.md`: partial-generated history with human notes

## Proposed Design

### 1. Shrink `feature.source.yaml`

Update JOB-PROJECT's source schema so it retains only the semantic fields
starter now expects.

Rules:

- remove legacy source fields like `owner`, `primary_stage`, `stages`, `refs`,
  and `keywords`
- map stage relationship meaning into `stage_participation` where appropriate
- keep semantic meaning in source rather than generated summary facts

### 2. Move contract-adjacent fields into generated contract output

Update the generator so `<feature_id>.yaml` becomes the assembled feature
contract surface.

That generated contract should carry:

- generated refs
- any freshness metadata this repo supports
- assembled current-state view

It should stop pretending the source file is the whole contract.

### 3. Replace legacy lineage schema

Rewrite `lineage.generated.yaml` generation to follow the newer starter
evidence-oriented contract.

At minimum, the target should align to the starter's explicit top-level shape:

- generated header
- `feature_id`
- `source`
- `invariants`
- `capabilities`
- `timeline`

It should explicitly stop emitting the rejected legacy keys:

- `generated_contract`
- `naming_policy`
- `capability_shape`
- `capability_ids`
- `refs`
- `refs_by_type`

### 4. Update capability source shape

Transition feature source capabilities from:

- `capability_id`
- `name`
- `summary`

to the newer starter-style semantic shape:

- `capability_id`
- `statement`
- `state`

The contract should stay stable and human-owned while generated outputs derive
other views from it.

### 5. Introduce a staged history migration path

If full history migration is too much for one batch, the plan may stage it.
But the spec target should still be the starter partial-generated history model.

That means:

- preserve useful old notes
- stop treating manual changelog structure as the long-term target
- generate the canonical history block once the generator supports it

### 6. Tighten validation to the new target

`scripts/validate_adoption_shape.py` should evolve from checking the Phase 4
legacy-compatible shape to checking the new starter-aligned shape.

Validation should eventually catch:

- extra legacy fields in `feature.source.yaml`
- wrong capability field shape in source
- legacy summary-style lineage top-level keys
- missing evidence-oriented lineage structure
- stale generated contracts or discovery after source changes

## Execution Strategy

Phase 5 should likely proceed in these batches:

### Batch 1: Generator and validator groundwork

- update generator output model for contract and lineage
- add tests for the new source/contract/lineage shapes
- keep temporary compatibility only where needed for staged rollout

### Batch 2: Feature source migration

- migrate feature sources to the smaller semantic shape
- migrate capabilities to `statement` and `state`
- remove legacy source-only fields

### Batch 3: Generated contract and lineage refresh

- regenerate feature contracts
- regenerate evidence-oriented lineage
- refresh generated discovery

### Batch 4: History alignment

- adopt partial-generated history pattern
- preserve old notes under `## Human Notes`

### Batch 5: Validation hardening

- remove transitional compatibility checks
- require the new starter-aligned schema as the only valid Mode B target

## Risks

### Risk 1: Contract movement breaks too many downstream assumptions at once

Moving fields out of source and changing lineage shape may break local tools,
tests, or mental models.

Mitigation:

- test generator and validator first
- stage compatibility bridges carefully
- migrate features in a controlled batch rather than opportunistically

### Risk 2: Evidence-oriented lineage is under-specified locally

If we swap out the old lineage shape without deciding how code/tests/docs/config
evidence should map into the new schema, the repo could land in an incomplete
state.

Mitigation:

- make the plan define the exact evidence buckets and minimal required keys
- keep starter schema as the contract anchor

### Risk 3: History migration becomes a distraction

History migration could expand the scope unnecessarily.

Mitigation:

- allow history to be a separate batch if needed
- keep Phase 5's primary goal on source/contract/lineage alignment

## Acceptance Criteria

Phase 5 is complete when all of the following are true:

1. Managed `feature.source.yaml` files follow the newer smaller semantic source
   shape.
2. Managed feature capability entries follow the newer starter-aligned source
   shape.
3. Generated `<feature_id>.yaml` files serve as assembled current-state
   contracts rather than mirrored source dumps.
4. `lineage.generated.yaml` follows the starter evidence-oriented schema and no
   longer emits the legacy summary-style top-level keys.
5. Validation and tests enforce the new target.
6. `repo_config/adoption-mode.yaml` and repo operating-system docs describe the
   new alignment honestly.

## Validation Strategy

Minimum implementation verification should include:

- `.\.venv\Scripts\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- `git diff --check`

## Execution Notes

Phase 5 execution landed the source/contract/lineage alignment target and
validation hardening on 2026-04-22.

Implemented in this phase:

- stricter generator and validator behavior for the Phase 5 source shape
- evidence-oriented `lineage.generated.yaml`
- generated current-state feature contracts
- generated discovery refresh
- operating-system governance and adoption-mode updates

Deferred from this phase:

- starter partial-generated `history.md` alignment

That history work remains a follow-up so the repo does not pretend the starter
history target is already complete.
