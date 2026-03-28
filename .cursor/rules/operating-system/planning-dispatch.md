# Planning Dispatch

## When to Apply

**Apply this rule at the start of any task that requires planning, implementation, or design work.**

This rule determines which skill to use and how to structure the initial output before proceeding.

---

## Core Principle

> Plan before building.
> Classify before planning.
> Classify by reading FEATURES.md first.

---

## Decision Tree: Which Skill to Use

```text
What are you doing?
|
├── Exploring an idea, comparing approaches, or generating design options
|   |
|   └── → Use **brainstorming**
|        Output: 3+ options with tradeoffs, chosen direction with rationale
|
├── Writing a new feature spec or design document
|   |
|   └── → Use **writing-plans**
|        Prerequisites: brainstorming output exists
|        Output: structured spec with Law / Decree / Circular sections
|
├── Writing an implementation plan for a confirmed design
|   |
|   └── → Use **project_plan_generation**
|        Prerequisites: approved spec or design doc exists
|        Output: task-stepped plan with rollback, monitoring, post-execution review
|
├── Executing a plan with checkpoints and rollback safety
|   |
|   └── → Use **executing-plans**
|        Prerequisites: approved implementation plan exists
|        Output: completed tasks, updated FEATURES.md, post-execution review
|
└── Running multiple parallel workstreams
    |
    └── → Use **dispatching-parallel-agents**
         Prerequisites: tasks are independent and can run concurrently
         Output: all branches complete, merged and reviewed
```

---

## Pre-Planning Triage (Required Before All Planning)

Before using any planning skill, produce the pre-planning triage output.
**This triage output must exist before any spec or plan is written. It is the gate.**

---

### Step 1 — Read FEATURES.md

* [ ] Read the current FEATURES.md
* [ ] Check if a related feature already exists
* [ ] If yes: this is MODIFY or REPLACE, not ADD
* [ ] If no: this is ADD

---

### Step 2–5 — Produce Triage Block

Fill in the triage fields defined in `operating-system/feature-lifecycle.md`:

* Feature type
* Reasoning
* Law
* Decree
* Impacted layers
* Migration
* Rollback complexity
* Risk
* Rollback trigger

> See `operating-system/feature-lifecycle.md` → **Triage Fields (Pre-Planning Gate)** for full definitions.

---

## Triage Gate Rules

* A spec cannot be written without a completed triage
* A plan cannot be written without an approved spec
* A plan cannot be approved without a completed triage
* The triage output goes at the top of every spec and plan

---

## Dispatch in Practice

---

### Scenario: New Feature Request

1. Read FEATURES.md
2. Classify using `operating-system/feature-lifecycle.md`
3. Produce triage block
4. Dispatch:
   → brainstorming
   → writing-plans
   → project_plan_generation
   → executing-plans
5. If REPLACE: deprecate the old feature in the same cycle

---

### Scenario: Bug Fix

1. Read FEATURES.md to find affected feature entry
2. If the fix changes behavior → produce triage → follow MODIFY flow
3. If it corrects a defect without behavior change → apply fix, document in existing entry

---

### Scenario: Exploration Before Commitment

1. Use **brainstorming** to generate options and tradeoffs
2. If direction is clear → produce triage → proceed to spec
3. If unclear → present options before proceeding

---

## Anti-Patterns

* Writing a plan before reading FEATURES.md → leads to ADD when it should be MODIFY
* Skipping the triage block and going straight to tasks
* Using writing-plans when the question is → "should we do this?" (use brainstorming instead)
* Using project_plan_generation when design is not finalized
* Dispatching parallel agents when tasks have dependencies → sequence first, parallelize second
