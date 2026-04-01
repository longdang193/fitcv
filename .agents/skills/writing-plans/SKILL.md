---
name: writing-plans
description: Use when you have a confirmed spec with triage block for a multi-step task, before touching code. Enforces the triage gate: do not proceed without a completed triage block from planning-dispatch. Consolidates project_plan_generation duties.
---

# Writing Plans

## Overview

Write implementation plans for an engineer with little project context. Be explicit about files, tests, commands, and validation. Keep plans DRY, YAGNI, TDD-oriented, and broken into small tasks.

Assume the engineer is capable but unfamiliar with the codebase and domain.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Default save path:** `docs/superpowers/plans/YYYY-MM-DD-HH-MM-<topic>-plan.md`  
(User preference overrides this.)

---

## Doc-System Alignment

Use the project doc system:

```text
code/                       → real truth
docs/stages/*.yaml          → stage contracts when stage-aware docs are in scope
docs/features/*.yaml        → structured truth
docs/features/<feature_id>/ → feature-specific explanation + history
docs/*.md                   → cross-cutting explanation
README.md                   → overview
docs/generated/             → generated discovery
```

Rules:

- The affected `docs/features/<feature_id>.yaml` file is the current-state anchor when a managed feature exists
- Cross-cutting operating-system work may use `Feature: none`
- Stage-heavy plans should name affected stages and the primary lens
- Feature-specific history belongs under `docs/features/<feature_id>/`
- Cross-cutting architecture belongs under `docs/*.md`
- The plan must link back to the feature contract when one exists, and to the spec
- Generated discovery is refreshed after source updates; do not edit it manually

---

## Pre-Plan Check

Do not write the plan until these are true:

1. `planning-dispatch` triage exists
2. the affected feature is identified, or the plan explicitly records that this is cross-cutting work with `Feature: none`
3. the relevant `docs/features/<feature_id>.yaml` exists when a managed feature is changing, or the plan explicitly says it must be created before implementation starts
4. the spec exists if the design is non-trivial

Minimum triage:

```text
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
Spec needed: yes | no
Plan needed: yes | no
```

Optional for risky work:

```text
Rollback trigger:
Rollback method:
Migration needed: yes | no
Risk level: low | medium | high
```

If triage is missing, stop and invoke `planning-dispatch`.

---

## Scope Check

If the spec covers multiple independent subsystems, suggest splitting into separate plans. Each plan should produce a coherent, testable increment.

---

## File Structure First

Before tasks, map:

- files to create
- files to modify
- tests to add/update
- docs to update
- generated outputs that must be refreshed

Prefer focused files and clear boundaries. Follow existing repo patterns unless a small local cleanup is necessary for this feature.

---

## Task Granularity

Each step should be small and concrete.

Good:

- write failing test
- run failing test
- implement minimal code
- run passing test
- commit

Avoid bundling multiple actions into one step.

---

## Plan Header

Every plan should start like this:

```md
# [Feature Name] Implementation Plan

**Feature:** `docs/features/<feature_id>.yaml`  
**Spec:** `docs/superpowers/specs/YYYY-MM-DD-HH-MM-<topic>-spec.md`  
**Type:** add | modify | replace  
**Status:** planned | building  

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** [1 sentence]

**Architecture:** [2–3 sentences]

**Key Invariants:**
- [constraint]
- [constraint]

**Rollout / Revert:**  
- rollback_trigger: [if needed]  
- rollback_method: [if needed]

---
```

Every plan must also include this section near the top:

```md
## Doc Update Matrix

- Feature contract: `docs/features/<feature_id>.yaml`
- Stage contracts: `docs/stages/<stage_id>.yaml` | none
- Feature history: `docs/features/<feature_id>/history.md` | none
- Feature-specific docs: `docs/features/<feature_id>/<doc>.md` | none
- Cross-cutting docs: `docs/<doc>.md` | none
- README: `README.md` | none
- Generated discovery: `docs/generated/<file>` | none
```

---

## Task Structure

Use this shape:

```md
### Task N: [Name]

**Files:**
- Create: `path/to/new_file.py`
- Modify: `path/to/existing_file.py`
- Test: `tests/path/test_file.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Write the failing test
- [ ] Step 2: Run it and confirm failure
- [ ] Step 3: Implement the smallest passing change
- [ ] Step 4: Run tests and confirm pass
- [ ] Step 5: Update docs/YAML if required
- [ ] Step 6: Regenerate `docs/generated/` if required
- [ ] Step 7: Commit
```

Include exact commands where useful.

---

## Required Coverage

A complete plan should specify:

- exact file paths
- test files and commands
- doc targets split by contract / feature history / feature-specific docs / cross-cutting docs / README / generated discovery
- which `docs/features/*.yaml` files change, or whether this is validly `Feature: none`
- which `docs/stages/*.yaml` files change when stage-aware docs are in scope
- whether `docs/generated/` must be regenerated
- commit points

Do not write vague steps like “add validation” or “update docs”.

---

## Plan Review Loop

After writing the plan:

- dispatch `plan-document-reviewer`
- fix issues
- re-review up to 3 times
- if still unresolved, surface to human

Provide the reviewer only:

- plan path
- spec path
- feature YAML path

---

## Execution Handoff

After saving the plan, offer:

**"Plan complete and saved to `docs/superpowers/plans/YYYY-MM-DD-HH-MM-<topic>-plan.md`. Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task
2. **Inline Execution** — execute in this session with `executing-plans`

**Which approach?"**

---

## Anti-Patterns

- writing a plan before reading the feature YAML
- forcing a fake feature contract onto cross-cutting operating-system work
- assuming `FEATURES.md`
- saving plans under `docs/plans/`
- writing vague tasks without file paths or test commands
- forgetting doc updates
- forgetting `docs/generated/` refresh when source layers changed
