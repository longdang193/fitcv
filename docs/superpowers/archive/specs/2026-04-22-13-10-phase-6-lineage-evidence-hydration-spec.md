---
layer: operating_system
artifact_type: spec
status: completed
parent_workstream: none
targets:
  - docs/features/*/lineage.generated.yaml
  - docs/features/*/<feature_id>.yaml
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

# Phase 6 Lineage Evidence Hydration Spec

## Triage

Layer: `operating_system`  
Feature type: `CHANGE`  
Summary: Hydrate the new Phase 5 lineage schema with real evidence and remove YAML alias noise so `lineage.generated.yaml` becomes both informative and reviewer-friendly.  
Reasoning: Phase 5 aligned the repo to the newer evidence-oriented lineage shape, but the generated files still contain mostly empty evidence buckets and repeated YAML anchors like `&id001` / `*id001`. That means the schema is right, but the practical lineage value is still too low.  
Invariants:

- The private repo remains the development source of truth.
- `feature.source.yaml` remains the human-owned semantic source.
- `<feature_id>.yaml` remains the generated assembled current-state contract.
- `lineage.generated.yaml` remains generated and evidence-oriented.
- File metadata and `@proves` remain source inputs to lineage, not hand-edited lineage output.
- Starter shared-surface review remains tracked in `repo_config/adoption-mode.yaml`.

Dependencies:

- Phase 5 spec: `docs/superpowers/archive/specs/2026-04-22-12-05-phase-5-evidence-oriented-lineage-alignment-spec.md`
- Phase 5 plan: `docs/superpowers/plans/2026-04-22-12-20-phase-5-evidence-oriented-lineage-alignment-plan.md`
- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`
- current file metadata under `scripts/` and `tests/`

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

## Problem

Phase 5 delivered the right lineage schema, but the generated evidence is still
too thin to be operationally useful.

Current observed issues:

1. capability lineage buckets such as `code`, `tests`, `configs`,
   `components`, `specs`, and `plans` are usually empty
2. `docs` evidence is often limited to `history.md`, which means lineage looks
   formally complete while still lacking meaningful implementation proof
3. repeated list values like `evidence_gaps` and `allowed_evidence_gaps`
   serialize with YAML anchors such as `&id001` / `*id001`, which is valid YAML
   but noisy and confusing for reviewers
4. validation currently checks the shape of lineage, but not whether evidence
   has been hydrated enough to justify stronger completeness claims

So the repo is now structurally aligned but still weak on evidence quality and
generated readability.

## Goal

Bring the Phase 5 lineage model to a more useful steady state so that:

1. `lineage.generated.yaml` contains real evidence derived from repo metadata
2. generated YAML does not emit alias noise for repeated list content
3. capability completeness is based on actual evidence presence rather than
   placeholder buckets
4. validation can distinguish between acceptable evidence gaps and missing
   lineage hydration

## Non-Goals

This phase does not:

- redesign the Phase 5 lineage top-level schema
- require a full history migration to the starter partial-generated format
- require perfect symbol-level code tracing for every capability
- require every doc mention to become lineage evidence
- reopen underscore feature-ID policy

## Current Baseline

The repo now generates lineage in the Phase 5 evidence-oriented shape:

- `feature_id`
- `source`
- `invariants`
- `capabilities`
- `timeline`

But current generator behavior is still intentionally minimal:

- `docs` is usually derived from `history.md`
- `specs` and `plans` are not meaningfully populated from current repo surfaces
- `code`, `tests`, `configs`, and `components` are emitted as empty lists
- repeated lists are serialized with YAML anchors by the YAML dumper

That means Phase 5 established the contract, but not yet the hydrated evidence.

## Proposed Target State

After Phase 6, a representative capability lineage entry should look more like:

```yaml
capabilities:
  cv_system.structured-cv-generation:
    state: active
    statement: Generate the structured CV artifact and rendered markdown output from the selected evidence bundle.
    code:
      - src/...
    tests:
      - tests/...
    docs:
      - docs/features/cv_system/history.md
    specs:
      - docs/superpowers/archive/specs/...
    plans:
      - docs/superpowers/archive/plans/...
    evidence_gaps:
      - missing_config_evidence
    allowed_evidence_gaps:
      - missing_config_evidence
    completeness_status: partial
```

And generated YAML should be plain expanded YAML without `&id001` / `*id001`
aliases.

## Proposed Design

### 1. Disable YAML aliases in generated lineage outputs

Update the YAML dump path used by `scripts/sync_architecture_docs.py` so
repeated Python objects are emitted as normal repeated YAML content rather than
anchor-based aliases.

This is a readability requirement, not a schema change.

Rules:

- generated files should remain deterministic
- no semantic data should be lost
- do not post-process YAML with brittle string replacement if the dumper can be
  configured directly

### 2. Hydrate evidence from real repo metadata surfaces

The generator should populate evidence buckets from actual metadata-bearing
surfaces rather than placeholder empties.

Minimum desired derivation:

- `code`
  - files under `src/` or other behavioral code surfaces whose top-of-file
    metadata names the feature or capability
- `tests`
  - test files and `@proves` markers that point to the capability
- `specs`
  - related spec docs when feature or capability lineage can be resolved from
    refs or metadata
- `plans`
  - related execution plans when lineage can be resolved from refs or metadata
- `configs`
  - repo-managed config or manifest files that materially participate in the
    capability
- `components`
  - component or workflow surfaces when this repo has a real metadata contract
    for them

This does not need to become a full semantic graph. It does need to become more
truthful than “everything empty except history.”

### 3. Separate feature-level refs from capability-level evidence

Phase 6 should keep a clear distinction between:

- feature-level context surfaces
- capability-level evidence surfaces

Not every feature-level spec or plan should automatically be stamped onto every
capability without review. A bounded heuristic is acceptable, but it should be
explicit.

Recommended approach:

- allow feature-level fallback refs where capability-specific linkage is not yet
  available
- mark resulting completeness conservatively
- prefer direct capability evidence from file metadata and `@proves`

### 4. Introduce meaningful completeness states

`completeness_status` should reflect the actual evidence quality instead of
defaulting almost everything to `missing_evidence`.

Recommended states:

- `complete`
  - core evidence buckets expected for this capability are present
- `partial`
  - at least some real evidence exists, but not enough for full completeness
- `missing_evidence`
  - no meaningful implementation or proof evidence exists yet

The exact thresholds should be documented in generator and validator behavior.

### 5. Tighten validator expectations around hydrated evidence

`scripts/validate_adoption_shape.py` should evolve from pure shape checking to
lightweight evidence sanity checks.

Examples:

- reject lineage outputs that still contain YAML anchors if alias-free output is
  the repo rule
- reject capabilities that claim `complete` without real `code` or `tests`
- allow `partial` or `missing_evidence` while the repo is still being hydrated
- ensure referenced evidence paths actually exist

The validator should not require perfect coverage in one step, but it should
block obviously misleading lineage claims.

### 6. Refresh governance wording

Repo governance should explain the new Phase 6 expectation clearly:

- Phase 5 established the lineage schema
- Phase 6 hydrates that schema with actual evidence and human-readable output
- history alignment remains a separate follow-up

## Evidence Sources In Scope

Phase 6 should inspect these repo surfaces as candidate lineage sources:

- `scripts/**/*.py`
- `tests/**/*.py`
- `repo_config/*`
- `docs/superpowers/archive/specs/*.md`
- `docs/superpowers/archive/plans/*.md`
- `docs/superpowers/plans/*.md`
- `docs/features/*/history.md`

Optional same-phase sources if they already have usable metadata:

- workflow files
- adapter or manifest surfaces
- repo-local component definitions

## Execution Strategy

Phase 6 should likely proceed in these batches:

### Batch 1: Generator and test groundwork

- add failing tests for alias-free YAML output
- add failing tests for hydrated evidence buckets
- define expected completeness-state transitions

### Batch 2: Evidence extraction

- teach the generator to collect metadata-bearing code and test refs
- teach the generator to collect available spec/plan/config evidence
- keep derivation conservative and deterministic

### Batch 3: Validation hardening

- add evidence-path existence checks
- add completeness-status sanity rules
- add alias-free output checks if needed

### Batch 4: Repo refresh and governance update

- regenerate all feature contracts and lineage files
- refresh `docs/generated/*`
- update operating-system docs and adoption notes

## Risks

### Risk 1: Over-attributing feature refs to every capability

If the generator blindly copies all feature-level specs and plans into every
capability, lineage will look full but remain semantically weak.

Mitigation:

- distinguish feature-level fallback from direct capability evidence
- keep completeness conservative when linkage is indirect

### Risk 2: Validator gets strict before hydration is good enough

If validation hardens too early, the repo may fail on many features before the
generator can supply better evidence.

Mitigation:

- implement generator and tests first
- only hard-fail on misleading claims, nonexistent paths, or alias-policy
  violations

### Risk 3: Metadata parsing becomes too clever

If Phase 6 tries to infer too much from weak heuristics, it may create noisy or
wrong lineage edges.

Mitigation:

- prefer explicit metadata and `@proves`
- keep heuristics simple, documented, and reviewable

## Acceptance Criteria

Phase 6 is complete when all of the following are true:

1. generated `lineage.generated.yaml` files no longer emit YAML anchors like
   `&id001` / `*id001`
2. representative capabilities across the managed feature set include real
   evidence in at least some of `code`, `tests`, `specs`, `plans`, `configs`,
   or `components`
3. evidence path lists point only to real repo files
4. `completeness_status` is derived from actual evidence presence and no longer
   defaults to a misleading placeholder pattern
5. validator and tests enforce the new hydration expectations honestly
6. repo governance documents the new lineage-evidence expectation and any
   remaining intentional drift

## Validation Strategy

Minimum implementation verification should include:

- `.\.venv\Scripts\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- `git diff --check`

## Open Questions

1. Should Phase 6 treat feature-level specs/plans as capability evidence by
   default, or only when stronger linkage is unavailable?
2. Which non-Python config/workflow/component surfaces in this repo already have
   enough metadata quality to be included now?
3. Should alias-free YAML be enforced only for lineage outputs, or for all
   generated YAML files in the architecture-doc system?

## Execution Notes

Phase 6 execution landed on 2026-04-22.

Implemented in this phase:

- alias-free generated YAML for architecture-doc outputs
- conservative lineage hydration from explicit Python metadata, `@proves`, and
  feature-level spec/plan fallback evidence
- evidence-path and completeness-claim validation hardening
- regenerated feature contracts, lineage files, and discovery outputs
- operating-system and adoption-mode wording updates

Not implemented in this phase:

- broad direct capability seeding across `src/`
- starter partial-generated `history.md` alignment
