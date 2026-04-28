---
name: writing-plans
description: Use when a confirmed design needs a multi-step implementation plan before code changes begin.
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

Use the current source-of-truth model:

```text
code/                                 → real truth
docs/intent/*.md                     → project purpose and outcome sources
docs/operating_system/*.md           → repo method and governance sources
docs/stages/*.source.yaml            → human-owned stage source when stage-aware docs are in scope
docs/stages/*.yaml                   → generated stage contracts when stage-aware docs are in scope
docs/features/*/feature.source.yaml  → human-owned feature source
docs/features/*/<feature_id>.yaml    → generated current feature contract
docs/features/*/lineage.generated.yaml → generated feature-local evidence
docs/features/<feature_id>/          → feature-specific explanation + partial-generated history
docs/*.md                            → cross-cutting product explanation
docs/superpowers/specs/*.md          → design artifacts
docs/superpowers/execution_maps/*.md → orchestration artifacts for approved spec sets
docs/superpowers/plans/*.md          → execution artifacts
README.md                            → overview
docs/generated/                      → generated discovery
```

Rules:

- intent work should point back to `docs/intent/*.md`
- when intent work is being translated into major delivery threads, the plan
  should also point back to `docs/intent/master-workstream-roadmap.md`
- operating-system work should point back to `docs/operating_system/*.md`
- The affected `docs/features/<feature_id>/feature.source.yaml` file is the
  human-owned anchor when a managed feature exists
- The generated `docs/features/<feature_id>/<feature_id>.yaml` file is the
  assembled current-state view
- Cross-cutting operating-system work may use `Feature: none`
- Stage-heavy plans should name affected stages and the primary lens
- Stage-heavy plans should also name `docs/stages/<stage_id>.source.yaml` and
  `docs/stages/<stage_id>.yaml`
- Feature-specific history belongs under `docs/features/<feature_id>/`
- Cross-cutting product architecture belongs under `docs/*.md`
- Cross-cutting repo-method docs belong under `docs/operating_system/*.md`
- The plan must link back to the feature source, generated contract, and spec
  when they exist
- When a multi-spec set needs detailed-spec authoring order first, consult the
  spec-authoring map
- When approved detailed specs need implementation ordering or parallelization,
  consult the implementation execution map rather than collapsing
  orchestration into the plan
- Use `docs/generated/planning_lineage.yaml` for derived thread/spec/plan
  inspection instead of re-entering those links manually in thread files
- Generated discovery is refreshed after source updates; do not edit it manually

---

## Pre-Plan Check

Do not write the plan until these are true:

1. `planning-dispatch` triage exists
2. the affected feature is identified, or the plan explicitly records that this is cross-cutting work with `Feature: none`
3. the relevant `docs/features/<feature_id>/feature.source.yaml` exists when a
   managed feature is changing, or the plan explicitly says it must be created
   before implementation starts
4. the spec exists if the design is non-trivial
5. when the work is now a multi-spec set, the implementation execution map
   exists or the plan explicitly explains why one is unnecessary

When the plan is downstream of intent, the triage and plan should make clear
whether the bounded change belongs under a product workstream or under the
parallel `operating_system` branch.

Important:

- an explicit user request for an implementation plan does not automatically require a new spec
- if triage shows the change is already bounded and design-clear, proceed directly to the plan
- require a spec first only when the design is still meaningfully ambiguous, cross-cutting in an unsettled way, or missing key decisions

Minimum triage:

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

If there is no spec because the user explicitly requested a clear bounded plan, state that the plan is proceeding from triage plus existing source-of-truth docs rather than inventing a placeholder spec.

If the approved work now spans multiple specs, use the implementation execution
map to choose ordering, parallel lanes, and bounded plan split before writing
plans.

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
---
layer: intent | operating_system | workstream | change
artifact_type: plan
status: proposed | active | completed | superseded
parent_workstream: <id> | none
parent_thread: <thread-id> | none
parent_spec: `docs/superpowers/specs/YYYY-MM-DD-HH-MM-<topic>-spec.md` | none
targets:
  - <path>
related_features:
  - <feature_id>
related_stages:
  - <stage_id>
---

# [Feature Name] Implementation Plan

**Feature Source:** `docs/features/<feature_id>/feature.source.yaml` | `none`
**Feature Contract:** `docs/features/<feature_id>/<feature_id>.yaml` | `none`
**Spec:** `docs/superpowers/specs/YYYY-MM-DD-HH-MM-<topic>-spec.md` | `none`
**Implementation Execution Map:** `docs/superpowers/execution_maps/YYYY-MM-DD-HH-MM-<topic>-execution-map.md` | `none`
**Type:** add | modify | replace  
**Plan Layer:** intent | operating_system | workstream | change
**Plan Status:** proposed | active | completed | superseded

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

Rules:

- `layer`, `artifact_type`, and `status` are required frontmatter
- new change-layer plans should use `parent_thread`
- new change-layer plans should use `parent_spec`
- `targets` is required when the plan is cross-cutting or otherwise ambiguous in scope
- `targets` may be omitted only when the plan is narrow and obviously local
- `related_features` and `related_stages` are optional navigation aids
- keep plan metadata aligned with the triage block rather than inventing a second classification
- `parent_workstream` is not the preferred downstream lineage field once a
  change-layer thread/spec pair exists
- when the plan is the requested primary artifact, the first created artifact should be the plan file under `docs/superpowers/plans/`, not an owning source doc

Every plan must also include this section near the top:

```md
## Doc Update Matrix

- Feature source: `docs/features/<feature_id>/feature.source.yaml` | none
- Feature contract: `docs/features/<feature_id>/<feature_id>.yaml`
- Feature lineage: `docs/features/<feature_id>/lineage.generated.yaml` | none
- Stage source: `docs/stages/<stage_id>.source.yaml` | none
- Stage contracts: `docs/stages/<stage_id>.yaml` | none
- Feature history: `docs/features/<feature_id>/history.md` | none
- Feature-specific docs: `docs/features/<feature_id>/<doc>.md` | none
- Cross-cutting docs: `docs/<doc>.md` | none
- Operating-system docs: `docs/operating_system/<doc>.md` | none
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
- which `docs/features/*/feature.source.yaml` files change, or whether this is
  validly `Feature: none`
- which generated feature contracts and lineage files refresh as outputs
- which `docs/stages/*.source.yaml` files change and which generated stage
  contracts refresh when stage-aware docs are in scope
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
- feature source path
- generated contract path when one exists

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

