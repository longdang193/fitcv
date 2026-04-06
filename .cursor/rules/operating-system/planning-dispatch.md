# Planning Dispatch

## When to Apply

Apply this rule at the start of any task that involves:

- feature planning
- implementation planning
- design work
- execution sequencing
- deciding which planning skill to use

This rule determines:

- which skill to use
- what to read first
- what minimal triage must exist before planning proceeds

---

## Core Principle

> Plan before building.
> Classify before planning.
> Classify by reading the current feature contract first, and by naming affected stages when the work is stage-heavy.

Read:

- `docs/features/*.yaml` for current feature state
- `operating-system/stage-lifecycle.md` when architectural or pipeline stages are central to the work
- `docs/features/<feature_id>/*` for feature-specific explanation and history
- `docs/*.md` for cross-cutting architecture and decisions only when needed
- `docs/generated/*` for fast lookup and discovery

Do not start from old prose docs when the current feature contract already exists.

---

## Decision Tree: Which Skill to Use

```text
What are you doing?
|
├── Exploring an idea, comparing approaches, or generating design options
|   |
|   └── → Use brainstorming
|        Output: options, tradeoffs, recommended direction
|
├── Writing a new spec or design doc
|   |
|   └── → Use brainstorming
|        Prerequisite: triage exists (use brainstorming first if design is unclear)
|        Output: structured spec/design doc
|
├── Writing an implementation plan
|   |
|   └── → Use writing-plans
|        Prerequisite: triage exists, design is clear enough
|        Output: step-by-step implementation plan
|
├── Executing a confirmed plan
|   |
|   └── → Use executing-plans
|        Prerequisite: implementation plan exists
|        Output: completed work, updated feature contract, updated docs, refreshed generated discovery
|
└── Running multiple independent workstreams
    |
    └── → Use dispatching-parallel-agents
         Prerequisite: tasks are independent
         Output: merged and reviewed results
```

---

## Pre-Planning Triage

Before writing a spec or plan, produce a minimal triage block.

This is the gate.

### Step 1 — Find the current feature source

Check in this order:

1. `docs/features/*.yaml`
2. `docs/generated/*` if needed for lookup
3. `docs/*.md` if explanation is needed

Questions to answer:

- does a related feature already exist?
- is this `ADD`, `MODIFY`, or `REPLACE`?
- which current feature contract is affected?
- which stages are affected?
- is the primary lens stage, feature, or mixed?
- do docs/spec/plan already exist?

Do not rely on memory or old prose summaries when a current YAML contract exists.

---

### Step 2 — Produce the triage block

Use the fields from the Feature Lifecycle rule's Triage Fields section:

```
Feature type: ADD | MODIFY | REPLACE
Reasoning: <why this classification>
Summary: <1-sentence goal>

Invariants:
  - <must hold true>

Domains:
  - <affected domain(s)>

Dependencies:
  - <if known>

Affected stages:
  - <stage_id> | none

Affected features:
  - <feature_id> | none

Primary lens: stage | feature | mixed

Affected docs:
  feature_yaml: `docs/features/<feature_id>.yaml` | none
  feature_history: `docs/features/<feature_id>/history.md` | none
  feature_docs:
    - `docs/features/<feature_id>/<doc>.md`
  cross_cutting_docs:
    - `docs/<doc>.md`
  readme: `README.md` | none
  generated:
    - `docs/generated/<file>`

Generated refresh required: yes | no

Impacted layers: Data | Pipeline | API | UI | None
Migration needed: yes | no
Rollback complexity: low | medium | high
Risk level: low | medium | high
Risk reason: <what makes this risky>
Rollback trigger: <metric or condition>
Rollback method: <how to revert>
```

See `operating-system/feature-lifecycle.md` → **Triage Fields (Pre-Planning Gate)** for full field definitions.

Keep triage short. It should help dispatch, not become a mini spec.

---

## Triage Gate Rules

- a spec should not be written without triage
- a plan should not be written without triage
- if the design is still unclear, use `brainstorming` first to generate options
- if implementation is obvious, a spec may be skipped
- triage should reference the current affected feature YAML when one exists
- triage should name affected stages when the work is pipeline-heavy, boundary-heavy, or architecture-heavy
- cross-cutting operating-system or method changes may use `Affected features: none`
- triage should name the exact doc targets, not just whether docs are needed

---

## Dispatch in Practice

### Scenario: New Feature Request

1. Check `docs/features/*.yaml`
2. Confirm no equivalent feature exists
3. Classify as `ADD`
4. Produce triage block
5. Dispatch:

   - brainstorming if options are unclear
   - brainstorming if a design/spec still needs to be written
   - writing-plans if implementation needs sequencing
   - executing-plans when ready

6. Create new feature contract in `docs/features/*.yaml`
7. Regenerate `docs/generated/*` after source changes

---

### Scenario: Existing Feature Behavior Change

1. Find the existing `docs/features/<feature_id>.yaml`
2. Decide whether this is `MODIFY` or `REPLACE`
3. Produce triage block
4. Update existing feature contract or create replacement contract
5. Dispatch to spec/plan/execution as needed
6. Refresh generated discovery after updates

---

### Scenario: Bug Fix

1. Check affected feature YAML
2. If behavior meaningfully changes, treat as `MODIFY`
3. If it is only a defect correction with no contract change:

   - fix code
   - update docs only if needed
   - no new feature planning flow required

---

### Scenario: Exploration Before Commitment

1. Use `brainstorming`
2. Compare options and tradeoffs
3. Once direction is clear, produce triage
4. Then continue to spec or plan if needed

---

## Required Outputs by Dispatch Stage

### After triage

You should know:

- classification (`ADD`, `MODIFY`, or `REPLACE`)
- affected stages
- affected feature
- primary lens
- affected docs
- whether spec is needed
- whether plan is needed

### After spec/design

You should know:

- intended behavior
- constraints/invariants
- affected docs/layers

### After implementation plan

You should know:

- ordered tasks
- risks and rollback if needed
- which files/docs/contracts must be updated

### After execution

You must update:

- code
- `docs/features/*.yaml`
- `docs/features/<feature_id>/` if feature-specific docs changed
- `docs/*.md` if cross-cutting docs changed
- `README.md` if navigation changed
- `docs/generated/*` via generator

---

## Anti-Patterns

- planning before reading the current feature contract
- skipping stage classification when the work is obviously stage-heavy
- creating a new feature when the change is really a `MODIFY`
- skipping triage and jumping straight to tasks
- writing a spec when the real question is still "which direction should we choose?"
- requiring specs/plans for trivial work
- forgetting to refresh `docs/generated/*` after source-layer changes
- using generated discovery as the source of truth instead of code/YAML/docs

---

## Practical Heuristic

Use the shallowest process that is still correct:

- unclear direction → brainstorming
- clear direction, non-trivial design → brainstorming then spec
- clear design, non-trivial execution → writing-plans
- confirmed plan → executing-plans

Always anchor planning on the current feature contract first, and add stage classification when the work crosses architectural boundaries.
