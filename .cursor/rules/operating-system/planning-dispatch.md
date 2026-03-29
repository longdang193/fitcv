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
> Classify by reading the current feature contract first.

Read:

- `docs/features/*.yaml` for current feature state
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
|   └── → Use writing-plans
|        Prerequisite: triage exists (use brainstorming first if design is unclear)
|        Output: structured spec/design doc
|
├── Writing an implementation plan
|   |
|   └── → Use project_plan_generation
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

---

## Dispatch in Practice

### Scenario: New Feature Request

1. Check `docs/features/*.yaml`
2. Confirm no equivalent feature exists
3. Classify as `ADD`
4. Produce triage block
5. Dispatch:

   - brainstorming if options are unclear
   - writing-plans if design needs a spec
   - project_plan_generation if implementation needs sequencing
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
- affected feature
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
- `docs/*.md` if needed
- `docs/generated/*` via generator

---

## Anti-Patterns

- planning before reading the current feature contract
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
- clear direction, non-trivial design → writing-plans
- clear design, non-trivial execution → project_plan_generation
- confirmed plan → executing-plans

Always anchor planning on the current feature contract first.
