---
name: planning-dispatch
description: Use when a task needs planning, design, or implementation routing before specs, plans, or code changes begin.
---
# Planning Dispatch

## When to Apply

Apply this skill at the start of any task involving planning, design, or implementation routing.

It decides:

- which planning layer owns the work
- what to read first
- whether the work is a managed feature change
- which skill should handle the next step

## Core Principle

> Plan before building.  
> Classify before planning.  
> Classify the layer first, then read the owning source.

## Layer Gate

Before feature/stage triage, classify the request into one of these layers:

- `intent`
  - project what-and-why
  - source docs live under `docs/intent/`
- `operating_system`
  - repo method, routing, governance, and workflow rules
  - source docs live under `docs/operating_system/`
- `workstream`
  - a major body of work derived from project intent
  - execution artifacts live under `docs/superpowers/`
- `change`
  - one bounded execution slice such as a patch, refactor, migration, release,
    runbook, or hotfix
  - execution artifacts live under `docs/superpowers/`

Intent and operating-system work should not be forced into fake feature
contracts. Workstream and change work still use feature/stage/source-of-truth
checks when those layers are affected.

Read in this order:

1. the owning layer source:
   - `docs/intent/*.md` for intent work
   - `docs/operating_system/*.md` for operating-system work
   - `docs/features/*/feature.source.yaml` and generated `docs/features/*/<feature_id>.yaml` for feature-owned work
2. `docs/stages/<stage_id>.source.yaml` and generated `docs/stages/<stage_id>.yaml` when stage-aware work is central to the task
3. `code/` when implementation reality or ownership evidence matters
4. `docs/features/<feature_id>/*` when focused feature explanation is needed
5. `docs/generated/*` for lookup only
6. `docs/*.md` for cross-cutting explanation when needed
7. `README.md` for navigation only

When one feature folder is in scope, refine the feature read to the minimum
truthful set:

- `feature.source.yaml` first
- generated `<feature_id>.yaml` only when the assembled current contract is needed
- `lineage.generated.yaml` only for ownership, evidence, or drift work
- `history.md` only for narrative context
- do not read the full feature folder by default

## Ownership Clarification

This skill does **not** write specs or plans. It routes work.

- **`brainstorming`** explores options, presents design, writes the spec, then hands off
- **`planning-dispatch`** produces the triage block and routes to the next skill
- **`writing-plans`** writes the implementation plan from a confirmed design/spec

## Pre-Planning Triage Gate

Before writing a spec or plan, produce triage. This is the gate.

### Step 1 — Classify the owning layer and source

- [ ] Decide whether the work is `intent`, `operating_system`, `workstream`, or `change`
- [ ] Read the owning layer source first
- [ ] If the work touches managed feature meaning, check `docs/features/*/feature.source.yaml`
- [ ] If the work is stage-heavy, identify affected stages and read `docs/stages/<stage_id>.source.yaml`
- [ ] Use generated feature/stage contracts and lineage surfaces for current-state and evidence lookup only
- [ ] Use `docs/generated/*` only for lookup if needed
- [ ] Read `docs/*.md` only if explanation or rationale is needed

### Step 2 — Determine feature classification when relevant

- [ ] If related feature exists: this is usually `MODIFY` or `REPLACE`
- [ ] If not: this is `ADD`

Cross-cutting intent or operating-system work may still use `Affected features: none`.

### Step 3 — Produce Triage Block

Required:

```text
Layer: intent | operating_system | workstream | change
Feature type: ADD | MODIFY | REPLACE
Summary: <1 sentence>
Reasoning: <why this classification>
Invariants:
  - <must hold true>
Dependencies:
  - <if known>
Affected stages:
  - <stage_id> | none
Affected features:
  - <feature_id> | none
Primary lens: stage | feature | mixed | cross-cutting
Affected docs:
  feature_source: `docs/features/<feature_id>/feature.source.yaml` | none
  feature_yaml: `docs/features/<feature_id>/<feature_id>.yaml` | none
  feature_lineage: `docs/features/<feature_id>/lineage.generated.yaml` | none
  feature_history: `docs/features/<feature_id>/history.md` | none
  stage_source: `docs/stages/<stage_id>.source.yaml` | none
  stage_contract: `docs/stages/<stage_id>.yaml` | none
  feature_docs:
    - `docs/features/<feature_id>/<doc>.md`
  cross_cutting_docs:
    - `docs/<doc>.md`
    - `docs/operating_system/<doc>.md`
  readme: `README.md` | none
  generated:
    - `docs/generated/<file>` | none
Generated refresh required: yes | no
Capability IDs:
  - <capability_id> | none
Invariant IDs:
  - <invariant_id> | none
Spec needed: yes | no
Plan needed: yes | no
````

`<feature_id>` is placeholder notation in the triage template. The real
generated contract path uses the concrete feature id as the filename.

Optional for risky work:

```text
Rollback trigger:
Rollback method:
Migration needed: yes | no
Risk level: low | medium | high
```

### Triage Gate Rules

- a spec cannot be written without triage
- a plan cannot be written without triage
- layer classification must happen before spec/plan routing
- if an affected feature exists, its `docs/features/<feature_id>/feature.source.yaml` and generated contract path must be identified before proceeding
- stage-heavy work must name affected stages before proceeding
- stage-heavy work must name both the stage source and generated stage contract paths before proceeding
- triage should name the exact doc targets, not just whether docs are needed
- generated files are never the source of truth; use them only to find the source
- `scripts/sync_architecture_docs.py` is the canonical architecture sync/check workflow; narrower metadata commands are bounded helpers rather than parallel default paths

## Routing Decision Tree

After triage, route to the correct skill:

```text
Exploring an idea or comparing approaches within the chosen layer
└── brainstorming

Design is clear enough; implementation plan needed
└── writing-plans

Approved plan exists; execute with checkpoints
└── executing-plans

Multiple independent workstreams
└── dispatching-parallel-agents
```

Routing note:

- if the user explicitly asks for an implementation plan and the change is already bounded and clear enough to execute, route directly to `writing-plans` after triage
- do not force a speculative spec hop just because the work is non-trivial; use `brainstorming` only when design is still meaningfully ambiguous

## Scenario Reference

### New Feature Request

1. Check `docs/features/*/feature.source.yaml`
2. Classify as `ADD`
3. Produce triage
4. Create or plan creation of the new `feature.source.yaml`
5. Dispatch: brainstorming → writing-plans → execution
6. Refresh `docs/generated/*` after source changes

### Existing Feature Change

1. Find the existing `docs/features/<feature_id>/feature.source.yaml`
2. Classify as `MODIFY` or `REPLACE`
3. Produce triage
4. Update existing feature source or create replacement feature source
5. Dispatch as needed
6. Refresh `docs/generated/*` after source changes

### Cross-Cutting Operating-System or Method Change

1. Confirm no managed feature contract is the primary lifecycle owner yet
2. Use `Affected features: none` if this is truly cross-cutting
3. Name affected stages plus `stage_source` / `stage_contract` paths if the work is stage-aware by design
4. Keep docs under cross-cutting paths rather than inventing a fake feature
5. Note whether the work is likely to produce a reusable memory update during closeout
6. Dispatch as needed

### Intent Change

1. Start from `docs/intent/`, not `docs/operating_system/`
2. Use `Affected features: none` when no managed feature contract owns the change
3. Keep intent docs stable and source-like instead of writing execution notes
4. If repo method also changes, name the operating-system doc targets separately rather than collapsing purpose and process into one doc


### Bounded Hygiene Or Drift Cleanup

1. Confirm the change is really hygiene, drift cleanup, or local cleanup rather than a hidden feature change
2. Use `Affected features: none` when no managed feature owns the lifecycle
3. Keep the primary lens as `feature` or `cross-cutting`, whichever is more truthful
4. Name the exact cross-cutting docs or rules that own the cleanup
5. Do not force a fake feature contract just to satisfy the planning template
6. Still require explicit triage before spec or plan work
### Bug Fix

1. Check affected feature source
2. If behavior changes meaningfully, follow `MODIFY`
3. If not, fix code and update docs only if needed

### Exploration Before Commitment

1. Use `brainstorming`
2. Once direction is clear, produce triage
3. Then route to spec/plan as needed

### Explicit Plan Request

1. Produce triage first
2. If the requested change is already bounded and clear, route directly to `writing-plans`
3. Use `brainstorming` first only when the design is still meaningfully unsettled
4. Do not treat the owning feature source as the first artifact to create; it is the first source to read

## Anti-Patterns

- skipping the layer gate and jumping straight to feature triage
- planning before reading current feature source
- treating `docs/operating_system/` as the default home for project-purpose docs
- skipping stage classification when the work is obviously stage-heavy
- skipping triage
- writing a plan before the design is clear
- using generated files as the source of truth
- forgetting to refresh `docs/generated/*` after source-layer changes
- creating or updating feature contracts after implementation instead of before or with it

## Related Skills

- **`doc-system-lifecycle`**: governs the source-of-truth layers, metadata rules, and generated discovery
- **`brainstorming`**: explores ideas and writes the spec
- **`writing-plans`**: writes the implementation plan
- **`executing-plans`**: executes an approved plan
- **`subagent-driven-development`**: recommended execution path when task-by-task delegation is helpful

