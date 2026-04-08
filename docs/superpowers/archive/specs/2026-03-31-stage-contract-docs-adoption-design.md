---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Adopt the new stage-aware doc system by introducing first-pass stage contracts and stage-linked feature docs for the core pipeline boundaries."
invariants:
  - "Stage contracts remain architectural boundary docs, not replacement lifecycle units."
  - "Feature contracts remain the primary current-state capability contracts."
  - "Stage docs must describe boundaries and handoffs without duplicating full feature truth."
  - "The first rollout should focus on the core pipeline stages only."
  - "Stage docs should align with the stage-transition-artifacts design so runtime inspection work has a stable documentation map."
---

# Stage Contract Docs Adoption Design

## Reference

- [`2026-03-31-stage-transition-artifacts-design.md`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/superpowers/specs/2026-03-31-stage-transition-artifacts-design.md)

## Triage

Feature type: MODIFY  
Summary: Create the first project-specific stage contracts and connect the most relevant pipeline feature docs to those stages under the updated stage-aware doc system.  
Reasoning: The operating-system and skills now support stage-aware documentation, but the project still has no actual stage contracts or stage-linked feature docs. This is the first project-specific adoption of that method, not a new product feature.  
Invariants:
- `docs/stages/*.yaml` must stay architectural and stage-scoped.
- `docs/features/*/*.yaml` must remain the primary lifecycle and capability truth.
- The rollout should cover only the most recognizable pipeline stages first.
- Stage docs must support, not replace, the existing stage-transition-artifacts design and related pipeline specs.
- Generated discovery can be deferred if the stage source layer is not yet stable enough.
Dependencies:
- `cv_system`
- `trigger_run_management`
- `inspection_debugging`
- stage-aware operating-system rules and mirrored skills
- [`2026-03-31-stage-transition-artifacts-design.md`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/superpowers/specs/2026-03-31-stage-transition-artifacts-design.md)
Affected stages:
- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_generation`
Affected features:
- `cv_system`
- `trigger_run_management`
- `inspection_debugging`
Primary lens: stage
Affected docs:
  feature_yaml:
    - `docs/features/cv_system/cv_system.yaml`
    - `docs/features/trigger_run_management/trigger_run_management.yaml`
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history:
    - `docs/features/cv_system/history.md`
    - `docs/features/trigger_run_management/history.md`
    - `docs/features/inspection_debugging/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - none
  readme: none
  generated:
    - none
Generated refresh required: no  
Spec needed: yes  
Plan needed: yes  
Migration needed: yes  
Risk level: medium  
Risk reason: This introduces the first real stage-source layer, so unclear boundaries or over-duplication could make the new doc model noisy instead of useful.

## Why This Spec Exists

The operating system now supports stage-aware documentation in principle, but the repo still has no actual stage contracts.

That leaves us in an awkward middle state:

- rules and skills can ask for affected stages
- the stage-transition-artifacts design assumes recognizable stage groups
- but there is still no stable stage-source layer inside the project docs

So stage-aware planning now has language, but not yet source files.

That matters because the next stage-related work will need stable answers to questions like:

- what exactly does `shortlist` own?
- where does `ranking` begin and end?
- which features primarily participate in `cv_generation`?
- how should future transition artifacts map back to documented stage boundaries?

Without stage contracts, those answers remain implicit and easy to drift.

## Problem Statement

The updated doc system introduced stages as a valid documentation and planning concept, but the project has not yet adopted that concept into its actual source docs.

This creates three gaps:

1. stage-aware planning has no stage-source files to point to
2. feature contracts still cannot express stage participation explicitly
3. the stage-transition-artifacts design has no stable project-level stage map to anchor against

So the immediate need is not a new runtime capability. The immediate need is a **first-pass stage documentation layer** that is:

- real
- bounded
- architectural
- linked to the existing feature contracts

## Design Goal

Adopt the stage-aware doc system into the project by introducing first-pass stage contracts and stage-linked feature contract metadata for the core pipeline boundaries.

The result should let a reader answer:

- what stages exist in the pipeline?
- what boundary does each stage own?
- which features primarily participate in that stage?
- which stages a given feature materially touches?

## Adoption Scope

Phase 1 should cover only the most stable pipeline stage boundaries:

- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_generation`

Phase 1 should also update only the most relevant feature contracts:

- `cv_system`
- `trigger_run_management`
- `inspection_debugging`

Phase 1 should not:

- create stage contracts for every subsystem in the repo
- rewrite unrelated feature docs
- add generated stage discovery yet if the source layer still needs iteration
- turn stage contracts into a second lifecycle/status system

## Proposed Source Model

### Stage contracts

Introduce:

```text
docs/stages/normalize.yaml
docs/stages/enrich.yaml
docs/stages/rule_filter.yaml
docs/stages/shortlist.yaml
docs/stages/ranking.yaml
docs/stages/cv_generation.yaml
```

These become the first project-specific stage boundary docs.

### Feature contract extensions

Update the three relevant feature contracts so they can declare:

```yaml
primary_stage:
stages: []
```

This gives us both directions:

- stage -> primary and related features
- feature -> primary and related stages

## Stage Contract Design

Recommended Phase 1 shape:

```yaml
stage_id:
name:
summary:
boundaries: []
inputs: []
outputs: []
depends_on: []
primary_features: []
related_features: []
refs:
  docs: []
  spec: []
  plan: []
  history: []
keywords: []
```

Important Phase 1 rule:

- do not add feature-style lifecycle fields like feature `status`, feature `type`, or rollout state

The point is to document architecture and handoffs, not to create a second feature registry.

## Stage-by-Stage Intent

### `normalize`

Should describe:

- raw job ingestion normalization
- deduplication boundary
- pre-enrichment reject boundary

Should link conceptually to:

- run-input and inspection-related work where relevant

### `enrich`

Should describe:

- enriched job contract creation
- candidate profile load/runtime profile shape
- canonical downstream fields produced here

Should link primarily to:

- `cv_system`
- `trigger_run_management`

### `rule_filter`

Should describe:

- deterministic eligibility gate
- passed/rejected split
- reject-reason ownership

Should link primarily to:

- `trigger_run_management`
- `inspection_debugging`

### `shortlist`

Should describe:

- raw retrieval output
- shortlist transition boundary
- raw vector hits vs scoring shortlist distinction

Should link primarily to:

- `inspection_debugging`

### `ranking`

Should describe:

- AI scoring and ranking input/output boundary
- authoritative ranking fit ownership
- ranked job selection boundary

Should link primarily to:

- `cv_system`
- `inspection_debugging`

### `cv_generation`

Should describe:

- evidence shaping into generation inputs
- validation and repair boundary
- final CV artifact acceptance/rejection boundary

Should link primarily to:

- `cv_system`
- `inspection_debugging`

## Relationship to Stage Transition Artifacts

The stage docs should not duplicate the stage-transition-artifacts spec.

Instead, they should stabilize the documentation map that the artifact design relies on.

Recommended relationship:

- stage contracts explain the architectural boundary
- the stage-transition-artifacts spec explains the bounded runtime artifact captured at that boundary

So for example:

- `docs/stages/shortlist.yaml`
  - explains what `shortlist` owns
- [`2026-03-31-stage-transition-artifacts-design.md`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/superpowers/specs/2026-03-31-stage-transition-artifacts-design.md)
  - explains the run-scoped artifact block that captures `shortlist` output

That keeps one clean separation:

- stage docs = boundary truth
- stage artifacts = inspection snapshot of runtime output at that boundary

## Feature Contract Updates

Each affected feature contract should gain stage metadata with clear intent.

Recommended expectations:

- `primary_stage`
  - the stage where the feature most clearly centers
- `stages`
  - every stage the feature materially affects

Phase 1 examples:

- `cv_system`
  - `primary_stage: cv_generation`
  - `stages: [enrich, ranking, cv_generation]`
- `trigger_run_management`
  - likely spans earlier orchestration-facing pipeline stages such as `normalize`, `enrich`, `rule_filter`, `shortlist`
- `inspection_debugging`
  - spans all inspected stages, with strongest emphasis on `shortlist`, `ranking`, and `cv_generation`

The exact values should be finalized during implementation, but they should stay bounded and obvious.

## History Update Policy

When the three feature contracts gain stage metadata, their history files should record:

- that the feature was mapped into the new stage-aware doc system
- which stages it now declares
- that this was a documentation-structure adoption, not a runtime behavior change by itself

That keeps the feature histories honest and reduces confusion later.

## Options Considered

### Option 1: Add only feature stage metadata, no stage contracts

Pros:

- smallest edit surface

Cons:

- features would point to stages that do not actually exist as source docs
- stage-aware planning would still lack a stage-source layer

Verdict:

- reject

### Option 2: Add first-pass stage contracts and bounded feature stage metadata

Pros:

- creates the missing source layer
- keeps rollout bounded
- aligns directly with the updated operating system
- gives the stage-transition-artifacts work a stable stage map

Cons:

- requires careful boundary wording to avoid duplication

Verdict:

- recommend

### Option 3: Roll out stage contracts and stage metadata repo-wide immediately

Pros:

- complete consistency quickly

Cons:

- too much churn
- too much ambiguity for non-pipeline areas
- likely to create low-signal stage docs outside the most stable boundaries

Verdict:

- reject

## Acceptance Criteria

1. The repo has real stage source docs for:
   - `normalize`
   - `enrich`
   - `rule_filter`
   - `shortlist`
   - `ranking`
   - `cv_generation`

2. Each stage contract is stage-scoped and architectural, not a duplicate feature contract.

3. The three relevant feature contracts expose stage participation through:
   - `primary_stage`
   - `stages`

4. A reader can navigate:
   - from a stage to its primary and related features
   - from a feature to the stages it materially affects

5. The stage docs and the stage-transition-artifacts design are clearly compatible, with stage docs owning boundary definitions and the artifacts spec owning runtime inspection payloads.

6. Feature history updates make clear that the rollout is a documentation-structure adoption, not a hidden runtime feature change by itself.

7. The rollout remains bounded to the initial pipeline stages and does not force repo-wide stage adoption.

## Recommended Next Step

Write an implementation plan that:

1. creates the six initial `docs/stages/*.yaml` contracts
2. updates the three feature contracts with stage metadata
3. updates the three feature history files
4. verifies that stage docs stay architectural and do not duplicate feature truth
