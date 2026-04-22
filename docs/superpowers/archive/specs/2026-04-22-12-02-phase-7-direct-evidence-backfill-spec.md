---
layer: operating_system
artifact_type: spec
status: completed
parent_workstream: none
targets:
  - docs/features/cv_system/feature.source.yaml
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/trigger_run_management/feature.source.yaml
  - docs/features/cv_system/lineage.generated.yaml
  - docs/features/inspection_debugging/lineage.generated.yaml
  - docs/features/trigger_run_management/lineage.generated.yaml
  - docs/features/cv_system/cv_system.yaml
  - docs/features/inspection_debugging/inspection_debugging.yaml
  - docs/features/trigger_run_management/trigger_run_management.yaml
  - scripts/sync_architecture_docs.py
  - scripts/validate_adoption_shape.py
  - tests/test_sync_architecture_docs.py
  - tests/test_validate_adoption_shape.py
  - docs/operating_system/feature-lifecycle.md
  - repo_config/adoption-mode.yaml
related_features:
  - cv_system
  - inspection_debugging
  - trigger_run_management
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 7 Direct Evidence Backfill Spec

## Triage

Layer: `operating_system`  
Feature type: `CHANGE`  
Summary: Backfill direct code and test evidence for a small pilot set of managed features so the evidence-oriented lineage model starts reflecting real implementation and proof surfaces instead of mostly spec and plan context.  
Reasoning: Phase 6 made lineage honest and readable, but the repo still reports `missing_code_evidence=232` and `missing_test_evidence=230`. The next useful step is not a repo-wide metadata flood. It is a bounded pilot that proves the direct-evidence workflow on the highest-value features first.  
Invariants:

- The private repo remains the development source of truth.
- `feature.source.yaml` remains the human-owned semantic source.
- `<feature_id>.yaml` remains a generated contract, not a hand-edited source.
- `lineage.generated.yaml` remains generated from upstream metadata.
- Direct code and test evidence must come from explicit file metadata and `@proves`, not from inferred filename guesses.
- Capability IDs remain stable, feature-qualified, and minimally scoped.
- We prefer sparse truthful evidence over broad noisy evidence.

Dependencies:

- Phase 5 spec: `docs/superpowers/archive/specs/2026-04-22-12-05-phase-5-evidence-oriented-lineage-alignment-spec.md`
- Phase 5 plan: `docs/superpowers/plans/2026-04-22-12-20-phase-5-evidence-oriented-lineage-alignment-plan.md`
- Phase 6 spec: `docs/superpowers/archive/specs/2026-04-22-13-10-phase-6-lineage-evidence-hydration-spec.md`
- Phase 6 plan: `docs/superpowers/plans/2026-04-22-13-25-phase-6-lineage-evidence-hydration-plan.md`
- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`
- existing Python file metadata and `@proves` conventions

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
- `inspection_debugging`
- `trigger_run_management`

Primary lens: `cross-cutting pilot`

Affected docs:

- feature_source:
  - `docs/features/cv_system/feature.source.yaml`
  - `docs/features/inspection_debugging/feature.source.yaml`
  - `docs/features/trigger_run_management/feature.source.yaml`
- feature_yaml:
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/trigger_run_management/trigger_run_management.yaml`
- feature_lineage:
  - `docs/features/cv_system/lineage.generated.yaml`
  - `docs/features/inspection_debugging/lineage.generated.yaml`
  - `docs/features/trigger_run_management/lineage.generated.yaml`
- feature_history:
  - `docs/features/cv_system/history.md`
  - `docs/features/inspection_debugging/history.md`
  - `docs/features/trigger_run_management/history.md`
- stage_source: `none`
- stage_contract:
  - `docs/stages/*.yaml`
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
Capability IDs: `pilot capability sets under cv_system, inspection_debugging, and trigger_run_management`  
Invariant IDs: `none`  
Spec needed: `yes`  
Plan needed: `yes`

## Problem

Phase 6 improved lineage generation, but the repo still lacks enough direct
implementation and proof evidence to make the evidence-oriented schema truly
useful.

Current observed issues:

1. many capability entries still have empty `code` and `tests` buckets
2. `completeness_status: partial` is often driven by fallback `specs` and
   `plans`, not by implementation or proof surfaces
3. the biggest remaining gaps cluster around high-value feature folders with
   broad capability sets, especially:
   - `cv_system`
   - `inspection_debugging`
   - `trigger_run_management`
4. there is still no clear repo rule for how much direct evidence is enough for
   a capability before we stop tagging files

So the schema is ready, but the repo still needs a disciplined evidence-seeding
pass.

## Goal

Establish the Phase 7 pilot pattern for direct lineage evidence by:

1. backfilling truthful `capabilities:` metadata into a bounded set of real code
   and test files
2. adding `@proves <capability_id>` only where tests genuinely verify the named
   capability
3. reducing `missing_code_evidence` and `missing_test_evidence` for the pilot
   features in a measurable way
4. documenting the curation rules so later rollout phases can scale safely

## Non-Goals

This phase does not:

- eliminate all lineage gaps across the repo
- require every file in a feature area to declare capability metadata
- introduce automatic static-analysis inference of capability ownership
- convert fallback spec or plan context into fake direct evidence
- retune Phase 6 alias handling or reopen the lineage schema shape
- rewrite starter partial-generated `history.md`

## Current Baseline

Representative lineage files such as:

- `docs/features/cv_system/lineage.generated.yaml`
- `docs/features/inspection_debugging/lineage.generated.yaml`

show the same pattern:

- `docs`, `specs`, and `plans` are populated
- `code` and `tests` are often empty
- `evidence_gaps` still include `missing_code_evidence` and
  `missing_test_evidence`

The repo-wide gap counts at spec time are:

- `missing_code_evidence=232`
- `missing_test_evidence=230`

That is too large for an unbounded cleanup, but small enough to improve through
a focused pilot.

## Pilot Scope

Phase 7 should be a three-feature pilot:

1. `cv_system`
2. `inspection_debugging`
3. `trigger_run_management`

These are the right pilot features because they:

- are high-value user-facing surfaces
- already have cleaned capability registries
- span backend behavior, orchestration, and admin UI inspection
- give us a good test of both implementation metadata and proof metadata

The pilot should target the minimum set of files needed to establish direct
evidence for a meaningful subset of capabilities, not every capability at once.

## Proposed Target State

After Phase 7, representative pilot capabilities should look like this:

```yaml
capabilities:
  cv_system.structured-cv-generation:
    code:
      - src/...
    tests:
      - tests/...
    completeness_status: complete
```

or, when only one direct evidence bucket is available:

```yaml
capabilities:
  inspection_debugging.run-detail-inspection-tabs:
    code:
      - src/...
    tests: []
    evidence_gaps:
      - missing_test_evidence
    completeness_status: partial
```

The important property is not that every capability becomes `complete`. It is
that direct evidence becomes real, curated, and reviewer-traceable.

## Proposed Design

### 1. Use a pilot-first evidence-seeding strategy

Do not attempt repo-wide evidence seeding in this phase.

Instead:

- choose a bounded subset of capabilities under the three pilot features
- identify the smallest truthful set of implementation files for each selected
  capability
- identify the tests that materially prove those capabilities
- seed metadata only in those files

This keeps the phase reviewable and reduces the chance of blanket metadata
noise.

### 2. Treat direct evidence as curated ownership, not broad tagging

Direct evidence should be added only when a file materially participates in the
capability.

Examples of acceptable direct evidence:

- a pipeline writer or validator module that directly implements
  `cv_system.structured-cv-generation`
- a run-detail route or UI handler that directly implements
  `inspection_debugging.run-detail-inspection-tabs`
- a run-control endpoint or trigger workflow file that directly implements
  `trigger_run_management.manual-checkpoints-and-continue`

Examples of unacceptable direct evidence:

- tagging a general utility file just because it is imported by a feature file
- tagging a base helper with every capability in its neighborhood
- tagging a broad integration test that does not clearly prove the named
  capability

### 3. Add proof metadata only where verification is real

`@proves <capability_id>` should remain a proof claim, not a routing shortcut.

Rules:

- use `@proves` only in tests that actually exercise or assert the capability
- allow one test to prove multiple capabilities only when the assertions truly
  cover them
- prefer smaller, clearer proof links over broad umbrella proof claims

Where a feature has implementation metadata but no good proof surface yet, that
is acceptable in this phase as long as lineage stays `partial`.

### 4. Keep capability-to-file mappings intentionally sparse

Phase 7 should define a repo rule that each pilot capability should generally
map to:

- one to a few primary implementation files
- zero to a few proof files

not to every transitive participant.

This is important for reviewability. If the lineage entry becomes a wall of
paths, the metadata stops being useful.

### 5. Allow small source-shape cleanup when it improves evidence curation

If a pilot feature has capability boundaries that are still too broad for clean
direct evidence mapping, Phase 7 may do a small `feature.source.yaml` cleanup
first.

Allowed same-phase source cleanup:

- small capability statement tightening
- splitting an obviously overloaded capability into a smaller stable pair
- removing clearly redundant capability overlap

Not allowed in this phase:

- broad capability taxonomy redesign
- renaming many stable capability IDs without strong need

### 6. Harden validation only around pilot expectations

The validator should not suddenly require full repo-wide direct coverage.

It may, however:

- verify that new direct evidence paths exist
- verify that declared proof paths are test files
- reject pilot claims of `complete` when the pilot capability still lacks the
  required direct evidence
- optionally enforce that selected pilot capabilities no longer carry
  `missing_code_evidence` or `missing_test_evidence` once the pilot is landed

The key is to tighten honesty for the pilot without blocking the rest of the
repo from remaining partially hydrated.

## Evidence Sources In Scope

Phase 7 should inspect and update these candidate direct-evidence surfaces:

- `src/**/*.py`
- `scripts/**/*.py`
- `tests/**/*.py`
- pilot feature source files under `docs/features/*/feature.source.yaml`

Optional same-phase evidence surfaces if they already carry meaningful metadata:

- repo-managed workflow files
- config or manifest files tied to pilot capabilities
- admin UI files if this repo stores them and they can truthfully carry feature
  metadata

## Execution Strategy

Phase 7 should likely proceed in these batches:

### Batch 1: Pilot selection and mapping

- choose the subset of pilot capabilities to land first under the three pilot
  features
- map each selected capability to candidate implementation files and candidate
  proof files
- reject noisy or weak mappings before editing

### Batch 2: Direct metadata seeding

- add `capabilities:` metadata to the selected implementation files
- add `@proves` markers to selected tests
- make only small source-shape cleanup if needed for clean mappings

### Batch 3: Generator and validator tightening

- update generation or validation only if needed to support pilot-target checks
- avoid broad repo-wide enforcement in this phase

### Batch 4: Regeneration and pilot review

- rerun `scripts/sync_architecture_docs.py`
- inspect the three pilot lineage files
- confirm selected capabilities gained direct code and test evidence
- confirm gap counts dropped in the expected places

### Batch 5: Governance capture

- update repo governance to describe the pilot curation rule
- record remaining repo-wide drift honestly in `repo_config/adoption-mode.yaml`

## Risks

### Risk 1: Broad metadata spray

If we add `capabilities:` to too many files just to reduce gap counts, the
lineage graph becomes noisy and less trustworthy.

Mitigation:

- require a material participation threshold
- keep mappings sparse and reviewable
- prefer leaving a gap over adding weak evidence

### Risk 2: Weak proof claims

If tests get `@proves` tags without actually verifying the capability, lineage
will overstate proof coverage.

Mitigation:

- add `@proves` only after reviewing the assertions
- allow pilot capabilities to remain partial when proof is not actually present

### Risk 3: Pilot scope creep

The three pilot features contain many capabilities, especially
`inspection_debugging` and `trigger_run_management`.

Mitigation:

- choose a subset of capabilities per feature
- define success as a validated pilot pattern, not full feature completion

### Risk 4: Source-shape churn during evidence seeding

If capability definitions are changed too aggressively during the pilot, the work
may turn into another taxonomy migration instead of direct evidence backfill.

Mitigation:

- allow only small source-shape cleanup
- defer broader taxonomy work to a later phase

## Acceptance Criteria

Phase 7 is complete when all of the following are true:

1. a bounded subset of capabilities under `cv_system`, `inspection_debugging`,
   and `trigger_run_management` have real direct `code` evidence
2. at least some of those pilot capabilities also have real direct `tests`
   evidence through truthful `@proves`
3. the selected pilot capabilities show reduced `missing_code_evidence` and, when
   applicable, reduced `missing_test_evidence`
4. no broad blanket metadata tagging was required to achieve the pilot result
5. generator output and validation remain deterministic and honest after
   regeneration
6. governance docs describe the pilot curation rule and any remaining repo-wide
   intentional gaps

## Validation Strategy

Minimum implementation verification should include:

- `.\.venv\Scripts\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- a targeted review of:
  - `docs/features/cv_system/lineage.generated.yaml`
  - `docs/features/inspection_debugging/lineage.generated.yaml`
  - `docs/features/trigger_run_management/lineage.generated.yaml`
- `git diff --check`

## Open Questions

1. Which exact subset of pilot capabilities under the three target features will
   give the best signal without turning this phase into a broad cleanup?
2. Should Phase 7 enforce pilot-specific validator rules, or should pilot review
   remain a manual acceptance check for this first pass?
3. Are there meaningful admin UI or workflow surfaces in this repo that should
   carry direct capability metadata now, or should the pilot stay Python-first?

## Execution Notes

Phase 7 execution landed on 2026-04-22.

Implemented in this phase:

- direct capability ownership metadata for:
  - `src/fitcv/cv_generator.py`
  - `src/fitcv/validator.py`
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/queue.py`
- truthful `@proves` links for the selected pilot capabilities in:
  - `tests/test_cv_generator.py`
  - `tests/test_validator.py`
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_queue.py`
- pilot-only direct-evidence enforcement via:
  - `repo_config/adoption-mode.yaml`
  - `scripts/validate_adoption_shape.py`
  - `tests/test_validate_adoption_shape.py`
- governance wording updates in `docs/operating_system/feature-lifecycle.md`
- regenerated feature contracts, lineage files, and discovery outputs

Observed pilot result:

- selected `cv_system`, `inspection_debugging`, and `trigger_run_management`
  capabilities now have direct `code` and `tests` evidence
- repo-wide lineage gap counts moved from:
  - `missing_code_evidence=232` to `218`
  - `missing_test_evidence=230` to `218`

Not implemented in this phase:

- repo-wide direct evidence seeding beyond the pilot capabilities
- broader feature capability taxonomy cleanup
