---
name: planning-dispatch
description: Apply at the start of any task that requires planning, implementation, or design work — encodes the triage gate and routing decision tree. Determines which skill to use and ensures FEATURES.md is read and triage is produced before any spec or plan is written.
---

<SUPERPOWERS-SKILL>

## When to Apply

**Apply this skill at the start of any task that requires planning, implementation, or design work.**

This rule determines which skill to use and how to structure the initial output before proceeding.

## Core Principle

> Plan before building.
> Classify before planning.
> Classify by reading `FEATURES.md` first.

## Ownership Clarification

This skill does **not** create specs or plans. It routes to the correct skill:

- **`brainstorming`** owns spec creation: it explores ideas, proposes designs, writes the design doc, and hands off to `writing-plans`.
- **`planning-dispatch`** is invoked AFTER brainstorming approval — it produces the triage block and routes to `writing-plans`.
- **`writing-plans`** receives a confirmed spec and produces the implementation plan.

## Pre-Planning Triage Gate

Before using any planning skill, produce the pre-planning triage output. **This triage output must exist before any spec or plan is written. It is the gate.**

---

### Step 1 — Read FEATURES.md

- [ ] Read the current `FEATURES.md`
- [ ] Check if a related feature already exists
- [ ] If yes: this is MODIFY or REPLACE, not ADD
- [ ] If no: this is ADD

---

### Step 2 — Produce Triage Block

Fill in all fields. Every field is required.

```
Feature type: ADD | MODIFY | REPLACE
Reasoning: <why this classification>

Law: <1-sentence business goal>

Decree:
  must_reuse:
    - <component that must not change>
  must_not_break:
    - <constraint that must hold>

Impacted layers: Data | Pipeline | API | UI | None
Migration needed: yes | no
Rollback complexity: low | medium | high
Risk level: low | medium | high
Risk reason: <what makes this risky>
Rollback trigger: <metric or condition>
```

### Triage Gate Rules

- A spec cannot be written without a completed triage
- A plan cannot be approved without a completed triage
- The triage output goes at the top of every spec and plan
- If `FEATURES.md` has not been updated with this feature entry, update it before proceeding

## Routing Decision Tree

After completing triage, route to the correct skill:

```text
What are you doing?

Exploring idea, comparing approaches
└── brainstorming → writes spec → handoff to writing-plans

Writing spec (brainstorming output exists, triage complete)
└── writing-plans → produces plan → handoff to execution

Executing plan with checkpoints (approved plan exists)
└── executing-plans

Running multiple parallel independent workstreams
└── dispatching-parallel-agents
```

## Scenario Reference

### New Feature Request

1. Read `FEATURES.md`
2. Classify using this skill's triage (ADD / MODIFY / REPLACE)
3. Produce triage block → update `FEATURES.md` with the entry
4. Dispatch: brainstorming → writing-plans → executing-plans
5. If REPLACE: deprecate the old feature in the same cycle

### Bug Fix

1. Read `FEATURES.md` to find the affected feature entry
2. If the fix changes behavior → produce triage → follow MODIFY flow
3. If it corrects a defect without behavior change → apply fix, document in the existing entry

### Exploration Before Commitment

1. Use **brainstorming** to generate options and tradeoffs
2. If direction is clear → produce triage → proceed to spec
3. If unclear → present options before proceeding

## Anti-Patterns

- Writing a plan before reading `FEATURES.md` → leads to ADD when it should be MODIFY
- Skipping the triage block and going straight to tasks
- Using brainstorming when the question is "should we do this?" (use brainstorming for the design, but triage gate is still required first)
- Using writing-plans when design is not finalized
- Dispatching parallel agents when tasks have dependencies → sequence first, parallelize second
- Creating a feature entry after the feature is already built (feature entries must be created before work begins)

## Related Skills

- **`doc-system-lifecycle`**: governs the 4-layer doc system, frontmatter schema, artifact naming, and size constraints. Invoke it before writing any spec or plan.
- **`brainstorming`**: explores ideas and writes the design spec. Invokes `planning-dispatch` after user approves the design.
- **`writing-plans`**: produces the implementation plan from a confirmed spec. Invokes `planning-dispatch` at the top to confirm triage was passed.
- **`subagent-driven-development`**: fast iteration with two-stage review. Recommended execution path after a plan is approved.
- **`executing-plans`**: batch execution with checkpoints. Alternative execution path.

</SUPERPOWERS-SKILL>
