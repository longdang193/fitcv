---
name: brainstorming
description: "Use when exploring or defining new behavior, features, components, or non-trivial changes before implementation."
---

# Brainstorming Ideas Into Designs

Help turn ideas into validated designs through structured dialogue.

<HARD-GATE>
Do NOT write code or implement anything before:
1. design is presented
2. user explicitly approves
</HARD-GATE>

---

## Core Principle

> Design -> validate -> then plan.
> Do not skip layer classification, source ownership, or doc placement.

This skill produces design only.
It does NOT produce implementation.

---

## Doc-System Alignment

Before writing any spec or doc, align with the current source-of-truth model:

```text
code/                                 -> real truth
docs/intent/*.md                     -> project purpose and outcome sources
docs/operating_system/*.md           -> repo method and governance sources
docs/stages/*.source.yaml            -> human-owned stage source when stage-aware docs are in scope
docs/stages/*.yaml                   -> generated stage contracts when stage-aware docs are in scope
docs/features/*/feature.source.yaml  -> human-owned feature source
docs/features/*/<feature_id>.yaml    -> generated feature contract (current state)
docs/features/*/lineage.generated.yaml -> generated feature-local evidence
docs/features/<feature_id>/          -> feature-specific explanation + partial-generated history
docs/*.md                            -> cross-cutting product explanation
docs/superpowers/specs/*.md          -> design artifacts
docs/superpowers/execution_maps/*.md -> orchestration artifacts for approved spec sets
docs/superpowers/plans/*.md          -> execution artifacts
docs/generated/                      -> discovery (auto)
README.md                            -> overview
```

Rules:

- `docs/intent/` governs project what-and-why
- `docs/intent/master-workstream-roadmap.md` is the top-down bridge from
  intent into durable product workstreams while preserving `operating_system`
  as a parallel branch for repo-method work
- `docs/operating_system/` governs repo method and workflow rules
- specs live under `docs/superpowers/specs/`
- execution maps live under `docs/superpowers/execution_maps/`
- plans live under `docs/superpowers/plans/`
- `feature.source.yaml` must exist before spec when a managed feature is changing; cross-cutting operating-system work may use `feature_source: none`
- the spec must link back to the affected `docs/features/<feature_id>/feature.source.yaml` and generated `docs/features/<feature_id>/<feature_id>.yaml` when they exist
- `<feature_id>` is placeholder notation; use the concrete feature-id filename in real docs, for example `docs/features/model-training-pipeline/model-training-pipeline.yaml`
- use stage classification when the work is pipeline-heavy, architecture-heavy, or boundary-heavy
- feature-specific explanation/history belongs under `docs/features/<feature_id>/`
- cross-cutting product explanation belongs under `docs/*.md`
- cross-cutting repo-method explanation belongs under `docs/operating_system/*.md`
- stage-aware work should name both `docs/stages/<stage_id>.source.yaml` and `docs/stages/<stage_id>.yaml`
- when one feature folder is in scope, read minimally:
  - `feature.source.yaml` first
  - generated `<feature_id>.yaml` only when the assembled contract view is needed
  - `lineage.generated.yaml` only for ownership, evidence, or drift work
  - `history.md` only for narrative context
  - do not load the entire feature folder by default

---

## Checklist (Execution Order)

```text
1. Explore context
   - classify the owning layer first: intent | operating_system | workstream | change
   - read the owning source first:
     - docs/intent/*.md for intent work
     - docs/operating_system/*.md for operating-system work
     - docs/features/*/feature.source.yaml for feature-owned work
   - when starting from intent, check whether the next branch is a product
     workstream or `operating_system`
   - read code and generated contracts only as needed
   - when stage-aware work is central, read docs/stages/<stage_id>.source.yaml and the generated stage contract
   - when one feature folder is in scope, prefer the smallest truthful reading set
   - check if feature already exists
   - check recent commits and other relevant docs
   - when the task touches repo-operating behavior, repeated issues, or unsettled harness areas, consult docs/operating_system/agent_memory/*

2. Ask clarifying questions (one at a time)

3. Propose 2-3 approaches
   - include tradeoffs
   - give recommendation

4. Present design incrementally
   - architecture
   - components
   - data flow
   - constraints / invariants

5. Align layer, feature, and stage ownership
   - classify the work as intent | operating_system | workstream | change
   - identify feature_id when one exists
   - identify affected stages when relevant
   - if starting from intent, decide whether the next branch is workstream or
     operating_system before writing downstream artifacts
   - decide the primary lens: stage | feature | mixed | cross-cutting
   - classify: add | modify | replace
   - name doc targets:
     - feature source -> docs/features/<feature_id>/feature.source.yaml
     - feature contract -> docs/features/<feature_id>/<feature_id>.yaml
     - feature lineage -> docs/features/<feature_id>/lineage.generated.yaml or none
     - feature history -> docs/features/<feature_id>/history.md or none
     - stage source -> docs/stages/<stage_id>.source.yaml or none
     - stage contract -> docs/stages/<stage_id>.yaml or none
     - feature-specific docs -> docs/features/<feature_id>/<doc>.md or none
     - cross-cutting product docs -> docs/<doc>.md or none
     - cross-cutting operating-system docs -> docs/operating_system/<doc>.md or none
     - README -> README.md or none
     - generated discovery -> docs/generated/<file> or none
   - confirm:
     - new feature -> create feature.source.yaml
     - existing feature -> update feature.source.yaml
     - cross-cutting operating-system or method change -> feature_source: none is allowed

6. Invoke planning-dispatch
   - produce triage block
   - confirm whether the next bounded artifact is a complete spec set, a
     spec-authoring map, a detailed spec, an implementation execution map, or
     a direct plan

7. Write spec set or detailed spec
   - save to docs/superpowers/specs/YYYY-MM-DD-HH-MM-<topic>-spec.md
   - follow metadata rules
   - for new change-layer specs, link them to the chosen thread via `parent_thread`
   - link the spec to the affected source docs and generated contracts

8. Write a spec-authoring map when the complete spec set is known but the
   detailed-spec authoring order is not
   - save to docs/superpowers/execution_maps/YYYY-MM-DD-HH-MM-<topic>-execution-map.md
   - use it only for orchestration across detailed-spec authoring work
   - do not turn it into a design spec

9. Write an implementation execution map when approved detailed specs now need
   implementation sequencing
   - save to docs/superpowers/execution_maps/YYYY-MM-DD-HH-MM-<topic>-execution-map.md
   - use it only for implementation orchestration across approved detailed specs
   - do not turn it into a giant implementation plan

10. Spec review loop
   - review -> fix -> repeat (max 3)

11. User approval

12. Handoff
   - invoke writing-plans from one approved detailed spec or from an approved
     implementation execution map, whichever now owns the next bounded plan
     breakdown
```

---

## Process Flow

```text
Explore context
  ↓
Ask questions
  ↓
Propose approaches
  ↓
Present design
  ↓
Align layer, feature, and stage ownership
  ↓
User approval on direction
  ↓
planning-dispatch (triage)
  ↓
Write complete spec set
  ↓
Optional spec-authoring map
  ↓
Write detailed specs
  ↓
Optional implementation execution map
  ↓
Review loop
  ↓
User approval
  ↓
writing-plans
```

---

## Design Rules

- prefer small, well-bounded components
- avoid over-engineering (YAGNI)
- follow existing patterns in repo
- improve locally if needed, not via a surprise global refactor

Each unit must answer:

- what it does
- how to use it
- what it depends on

---

## Spec Writing Rules

- spec belongs in `docs/superpowers/specs/`
- `feature.source.yaml` = human-owned meaning; generated feature YAML = current state
- spec = explanation + design
- spec must name the affected `docs/features/<feature_id>/feature.source.yaml` and generated `docs/features/<feature_id>/<feature_id>.yaml` when one exists
- stage-heavy specs should also name affected stages, the primary lens, and the `stage_source` / `stage_contract` targets
- specs for intent work should point back to `docs/intent/*.md`
- specs for operating-system work should point back to `docs/operating_system/*.md`
- spec should name any feature-specific docs, cross-cutting docs, or operating-system docs it expects to be updated

### Required metadata

```yaml
---
layer: intent | operating_system | workstream | change
artifact_type: spec
status: proposed | active | completed | superseded
parent_thread: <thread-id> | none
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
- for new change-layer specs, `parent_thread` is the preferred lineage field
- `targets` is required when the artifact is cross-cutting or otherwise ambiguous in scope
- `targets` may be omitted only when the artifact is narrow and obviously local
- `related_features` and `related_stages` are optional navigation aids, not a second ownership system

When humans need the assembled thread/spec/plan view, point them to
`docs/generated/planning_lineage.yaml` instead of adding derived links back
into thread files.

---

## Anti-Patterns

- writing a spec before layer classification
- writing a spec before feature classification when a managed feature exists
- writing a spec without classifying affected stages when the work is clearly boundary-heavy
- writing a spec without linking the affected feature source when one exists
- treating `docs/operating_system/` as the default home for project-purpose docs
- assuming `FEATURES.md`
- mixing design and implementation
- generating broad global design docs when the change is local
