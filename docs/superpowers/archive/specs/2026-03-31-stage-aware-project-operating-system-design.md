---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Adjust the project operating system, cursor rules, and related skills so documentation can model pipeline stages as a navigation layer above features."
invariants:
  - "Features remain the primary current-state contract units."
  - "Stages are a higher-level navigation and ownership layer, not a replacement for features."
  - "Stage-aware documentation must improve discoverability without duplicating feature truth."
  - "Rules and skills must route planning/design work using both affected features and affected stages when relevant."
  - "Generated discovery must remain derived from authoritative source files, never edited manually."
---

# Stage-Aware Project Operating System Design

## Affected Rule and Skill Sources

### Cursor rules

- [project-operating-system.mdc](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.cursor/rules/project-operating-system.mdc)
- [doc-system-lifecycle.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.cursor/rules/operating-system/doc-system-lifecycle.md)
- [stage-lifecycle.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.cursor/rules/operating-system/stage-lifecycle.md)
- [feature-lifecycle.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.cursor/rules/operating-system/feature-lifecycle.md)
- [planning-dispatch.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.cursor/rules/operating-system/planning-dispatch.md)

### Agent skills

- [brainstorming/SKILL.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/brainstorming/SKILL.md)
- [planning-dispatch/SKILL.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/planning-dispatch/SKILL.md)
- [doc-system-lifecycle/SKILL.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/doc-system-lifecycle/SKILL.md)
- [writing-plans/SKILL.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/writing-plans/SKILL.md)
- [executing-plans/SKILL.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/executing-plans/SKILL.md)

## Triage

Feature type: MODIFY  
Summary: Adjust the project operating system so rules, skills, and generated discovery support stage-aware documentation above the existing feature layer.  
Reasoning: This is not a product capability and should not be modeled as a new managed feature. It is a cross-cutting project-method change to the existing rules, skills, and doc-system guidance.  
Invariants:
- `docs/features/*.yaml` remains the primary current-state truth for features.
- Stages must be added as a higher-level grouping layer, not as a replacement for features.
- A single feature may span multiple stages.
- Rules and skills must stay aligned; they cannot drift into two different operating systems.
- The change must improve navigation and planning clarity before any larger stage-artifact rollout.
Domains:
- documentation
- planning
- project_method
- pipeline_architecture
Dependencies:
- current feature-centric doc system
- current operating-system cursor rules
- current `.agents` planning, writing, and execution skills
Affected docs:
  feature_yaml:
    - none
  feature_history:
    - none
  feature_docs:
    - none
  cross_cutting_docs:
    - none
  readme: none
  generated:
    - `docs/generated/*`
Generated refresh required: yes  
Spec needed: yes  
Plan needed: yes  
Impacted layers: Pipeline | None  
Migration needed: yes  
Rollback complexity: medium  
Risk level: medium  
Risk reason: This changes the project’s planning/documentation operating model, so inconsistent rollout across rules, skills, and generated discovery would create confusion.  
Rollback trigger: If stage-aware routing causes repeated misclassification or doc placement confusion in active planning sessions.  
Rollback method: Revert to the current feature-centric operating-system rules and disable stage-aware requirements until rules and generated discovery are aligned.

## Why This Spec Exists

The current operating system is clean and feature-centric, but recent pipeline work exposed a gap:

- the repo has strong feature contracts
- the pipeline itself has recognizable stage boundaries
- many debugging and design conversations are really about stage ownership first, then feature behavior inside those stages

Right now, the method stack treats those conversations only through feature contracts.

That creates friction:

- pipeline work that is naturally stage-oriented has no first-class doc-system concept for stages
- specs and plans have to force stage reasoning into feature-only structure
- stage-crossing features are hard to navigate from a pipeline-architecture point of view
- rules and skills currently cannot ask “which stages are affected?” even when that is the most useful planning question

So the goal is not to abandon features. The goal is to let the doc system model both:

- **features** as the main current-state contracts
- **stages** as a higher-level execution/navigation layer

## Current State

The current project operating system is explicitly feature-centric.

From [project-operating-system.mdc](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.cursor/rules/project-operating-system.mdc):

- it points to:
  - `doc-system-lifecycle`
  - `feature-lifecycle`
  - `planning-dispatch`
- its source-of-truth model is:
  - `code/`
  - `docs/features/*.yaml`
  - `docs/features/<feature_id>/`
  - `docs/*.md`
  - `README.md`
  - `docs/generated/`

The mirrored skills in `.agents` reinforce the same shape:

- [planning-dispatch/SKILL.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/planning-dispatch/SKILL.md)
  - requires triage around `docs/features/*.yaml`
- [doc-system-lifecycle/SKILL.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/doc-system-lifecycle/SKILL.md)
  - defines a five-layer doc system with feature YAML as the structured truth
- [brainstorming/SKILL.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/brainstorming/SKILL.md)
  - requires feature alignment before spec writing
- [writing-plans/SKILL.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/writing-plans/SKILL.md)
  - still assumes a purely feature-centric doc model and triage flow
- [executing-plans/SKILL.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/executing-plans/SKILL.md)
  - still describes source-of-truth sync only through the current feature-centric model

This works well for many tasks. The problem is that it has no explicit home for **pipeline stages as recognizable architectural boundaries**.

## Problem Statement

The current operating system lacks a first-class concept for **stages with recognizable boundaries**.

As a result:

1. the system is strong at feature-oriented documentation, but weaker at stage-oriented navigation
2. pipeline planning cannot classify work by affected stages even when that is the clearest framing
3. rules and skills currently assume the structured-truth layer is only feature-based
4. generated discovery can answer “what features exist?” but not “what stages exist and which features live across them?”

This becomes especially painful for work like:

- retrieval vs ranking vs CV-generation cleanup
- debug artifacts at stage transitions
- pipeline ownership design
- stage-local inspection work

## Design Goal

Adjust the project operating system so it can model:

- **features** as the primary current-state contracts
- **stages** as a higher-level execution and navigation layer above features

The design should let rules, skills, specs, plans, and generated discovery answer both:

- what feature is changing?
- what stage or stages are affected?

## Core Design Decision

### Keep features as the primary contract units

Do **not** replace feature YAML with stage YAML.

Feature YAML should remain the main current-state truth for:

- capability ownership
- lifecycle/version/status
- rollout/change tracking

### Add stages as a higher-level grouping layer

Introduce a new stage layer, likely:

- `docs/stages/*.yaml`

Each stage contract should describe:

- the stage identity
- its purpose
- its boundary conditions
- the kinds of transitions it owns
- which features primarily participate in that stage

This creates a two-level model:

1. **stages**
   - architecture / execution boundaries
2. **features**
   - concrete capabilities inside or across those stages

## Recommended Doc-System Model

### Updated high-level source-of-truth model

Recommended new shape:

```text
code/                       → real truth
docs/stages/*.yaml          → stage contracts (architectural boundaries)
docs/features/*.yaml        → feature contracts (current capabilities)
docs/features/<feature_id>/ → feature-specific explanation + history
docs/*.md                   → cross-cutting explanation
README.md                   → overview
docs/generated/             → generated discovery
```

Interpretation:

- `docs/stages/*.yaml`
  - stage-level truth for architectural boundaries
- `docs/features/*.yaml`
  - feature-level truth for capabilities

This is an **extension** of the current system, not a replacement.

## Stage Contract Model

Recommended minimal shape:

```yaml
stage_id:
name:
version:
status:
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

Stage contracts should be:

- stable
- architectural
- few in number

For the current pipeline, likely stages would include:

- normalize
- enrich
- rule_filter
- shortlist
- ranking
- cv_generation

## Feature Contract Extension

Feature contracts should gain explicit stage metadata.

Recommended additions:

```yaml
primary_stage: ranking
stages:
  - shortlist
  - ranking
  - cv_generation
```

Rules:

- `primary_stage`
  - the main stage where the feature primarily lives
- `stages`
  - all stages the feature materially affects

This lets discovery answer:

- stage -> features
- feature -> stages

## Rule Changes Required

### 1. `project-operating-system.mdc`

Should be updated to:

- describe the new stage-aware doc system at a high level
- instruct readers to apply rules in this order:
  - doc placement
  - stage + feature classification
  - planning dispatch

It should explicitly say:

- stages are above features for navigation
- features remain the primary managed contract units

### 2. `operating-system/stage-lifecycle.md`

Should be added to:

- define what a stage is
- define how stages relate to features
- define when stage classification is required
- centralize stage-aware triage/spec/plan vocabulary so the other rules can reference one shared stage model

### 3. `operating-system/doc-system-lifecycle.md`

Should be updated to:

- expand the 5-layer model to include stages
- define where stage contracts live
- define how stage docs relate to feature docs
- clarify that stage docs are architectural and should not duplicate feature truth

### 4. `operating-system/feature-lifecycle.md`

Should be updated to:

- explain that managed work may require both:
  - feature classification
  - stage classification
- keep lifecycle rules anchored on features, not stages
- add stage-awareness to triage fields

### 5. `operating-system/planning-dispatch.md`

Should be updated to:

- require identifying affected stages as well as affected features for pipeline/architecture work
- route stage-heavy pipeline design work without losing the feature contract requirement

## Skill Changes Required

### 1. `brainstorming`

Should require, for pipeline/architecture work:

- identifying affected stages
- identifying affected features
- deciding whether the spec is:
  - primarily stage-oriented
  - feature-oriented
  - or both

### 2. `planning-dispatch`

Should update the triage block to include:

```text
Affected stages:
  - <stage_id>
Affected features:
  - <feature_id>
Primary lens: stage | feature | mixed
```

It should still require feature YAML alignment when a feature exists or is being created.

### 3. `doc-system-lifecycle`

Should define:

- `docs/stages/*.yaml` as the new stage-contract layer
- stage/feature cross-reference expectations
- updated generated discovery expectations

### 4. `writing-plans`

Should be updated to:

- include stage-aware doc-system alignment in plan-writing guidance
- require plans for stage-heavy work to name:
  - affected stages
  - affected features
  - whether the plan is stage-oriented, feature-oriented, or mixed
- account for stage contracts in its doc update matrix when relevant

### 5. `executing-plans`

Should be updated to:

- reflect the expanded doc model in its source-of-truth sync guidance
- require execution review to confirm both:
  - feature contracts remain correct
  - stage contracts remain correct
- include stage-aware checks in its completion checklist when relevant

## Generated Discovery Changes

The generated layer should be extended with stage-aware discovery.

Recommended additions:

- `docs/generated/stages_index.yaml`
- `docs/generated/stage_overview.md`
- `docs/generated/stage_feature_map.yaml`

These should answer:

- what stages exist
- what each stage owns
- which features belong to or cross that stage

## Options Considered

### Option 1: Keep the current feature-only operating system

Pros:

- smallest change
- no new doc layer

Cons:

- stage-centric pipeline work keeps fighting the doc model
- planning and discovery remain weaker for boundary-driven pipeline work

Verdict:

- reject

### Option 2: Replace features with stages as the main contract units

Pros:

- strong stage-oriented pipeline framing

Cons:

- wrong abstraction for many capabilities
- features often span multiple stages
- rollout/history/versioning becomes awkward

Verdict:

- reject

### Option 3: Add stages above features as a second structured-truth layer

Pros:

- preserves the strengths of feature contracts
- gives pipeline architecture work a first-class home
- improves navigation without collapsing distinct concepts

Cons:

- requires synchronized rule, skill, and generated-discovery changes

Verdict:

- recommend

## Phase 1 Scope

Phase 1 should:

- introduce the concept and contract of stage-aware documentation
- define stage contracts as a new layer
- update cursor rules so they describe the stage-aware model consistently
- update mirrored skills so planning, plan-writing, and plan-execution all use the same model
- extend generated discovery expectations

Phase 1 should not:

- rewrite every existing feature doc immediately
- move all existing docs under a new directory structure
- require every non-pipeline feature to adopt stage metadata immediately

## Migration Strategy

### First rollout

1. update the cursor rules
2. update the mirrored `.agents` skills
3. define the new `docs/stages/*.yaml` contract
4. add stage metadata to the most relevant pipeline features first
5. add stage-aware generated discovery

### Initial adoption target

Start with the most clearly stage-based features:

- `cv_system`
- `trigger_run_management`
- `inspection_debugging`

That is enough to prove the model before expanding further.

## Acceptance Criteria

1. The operating-system rules explicitly support a stage-aware documentation model.

2. The mirrored `.agents` skills use the same stage-aware model and do not contradict the cursor rules.

3. The planning/execution workflow is covered end to end, including:
   - brainstorming
   - planning-dispatch
   - doc-system-lifecycle
   - writing-plans
   - executing-plans

4. The doc system clearly distinguishes:
   - stage contracts
   - feature contracts
   - feature-specific explanation/history
   - cross-cutting docs

5. Triage for stage-heavy work can identify:
   - affected stages
   - affected features
   - whether the work is primarily stage-oriented, feature-oriented, or mixed

6. The new model preserves features as the primary lifecycle/versioning units.

7. Generated discovery is planned to support:
   - stage index
   - feature index
   - stage-feature mapping

## Recommended Next Step

Write an implementation plan that:

1. updates the `.cursor` operating-system rules
2. updates the `.agents` mirrored skills, including plan-writing and execution skills
3. defines the initial `docs/stages/*.yaml` schema
4. scopes the first generated stage-aware discovery outputs
