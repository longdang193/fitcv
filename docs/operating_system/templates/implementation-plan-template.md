---
template_id: implementation-plan
target_globs:
- docs/superpowers/plans/*.md
required_sections:
- Goal
- Implementation Outcomes
- Task Breakdown
- Verification
- Completion Criteria
required_frontmatter:
  artifact_type: plan
  status: proposed
  layer: change
distribution_tier: starter_kit
---

# Implementation Plan Template

## Goal

<what this plan must deliver>

## Implementation Outcomes

Use this section for final implementation outcomes only.
Do not restate task-by-task execution details or local verification steps here.

### <deliverable 1>

Describe one concrete implementation outcome this plan must deliver, including changed surfaces, expected behavior, and verification intent.

### <deliverable 2>

Describe another concrete implementation result this plan must deliver, such as test coverage, documentation alignment, or downstream handoff readiness.

## Execution Approach

- Mode: `inline sequential | harness sequential_agents | harness parallel_lanes`
- Required skills: `<exact skill names or none>`
- Isolation: `<current workspace | isolated worktree for parallel writers>`
- Commit policy: `<external authorization | no commits during execution>`
- Parallel ownership: `<disjoint files/symbols or none>`
- Sequential fallback: `<ordered fallback when parallel work is unsafe>`

## Task Breakdown

Use `Task` for directly executable implementation slices.
Use `Wave` only when plan truly needs orchestration across multiple related tasks.

Within each task:
- `Purpose` owns bounded outcome
- `Specification Coverage` maps approved requirements or direct scope
- `Required Skills` names only methods needed for this task
- `Files And Symbols` owns exact touched surfaces
- `Dependencies` owns prerequisites and prior task requirements
- `Steps` owns execution sequence
- `Verification` owns task-local proof
- `Exit Criteria` owns task completion gate

For material backend tasks, name direct boundary, important success/failure behavior, final state or side effects, rollback/idempotency, real dependencies, contract evidence, and representative-operation trace mechanism by applicability. Frontend/backend tasks also name final specification, prototype reference when material, canonical contract owner, integration sidecar, browser flow, and sidecar removal condition.

Prefer one smallest valuable vertical capability per task. Do not create isolated frontend and backend phases when neither can prove user-visible capability independently.

Do not duplicate final artifact verification commands here unless a command is truly both task-local and final.

### Task 1: <short task title>

**Purpose:**
- <bounded outcome this task delivers>

**Specification Coverage:**
- <requirement, decision, invariant, or approved direct scope>

**Required Skills:**
- `<skill-name>` or `none`

**Files And Symbols:**
- Inspect: `<path>:<symbol>`
- Modify: `<path>:<symbol>`
- Verify: `<path>`

**Dependencies:**
- <upstream dependency, source-first fact, or prior task result>

**Steps:**
- [ ] Step 1: <first bounded action>
- [ ] Step 2: <second bounded action>
- [ ] Step 3: <verification-aligned follow-up>

**Verification:**
- [ ] `<command, assertion, or inspection target>`
- Expected: <observable result>

**Exit Criteria:**
- <what makes this task done>

### Task 2: <short task title>

**Purpose:**
- <bounded outcome this task delivers>

**Specification Coverage:**
- <requirement, decision, invariant, or approved direct scope>

**Required Skills:**
- `<skill-name>` or `none`

**Files And Symbols:**
- Inspect: `<path>:<symbol>`
- Modify: `<path>:<symbol>`
- Verify: `<path>`

**Dependencies:**
- Task 1 complete
- <any additional dependency>

**Steps:**
- [ ] Step 1: <first bounded action>
- [ ] Step 2: <second bounded action>
- [ ] Step 3: <verification-aligned follow-up>

**Verification:**
- [ ] `<command, assertion, or inspection target>`
- Expected: <observable result>

**Exit Criteria:**
- <what makes this task done>

## Verification

Use this section for final artifact-level verification only.
Do not copy every task-local proof here.

- <final command>

## Completion Criteria

The plan is ready for completion verification when:

1. every required implementation outcome is satisfied
2. every required task and task-local verification item is complete
3. plan deviations, substitutions, blockers, and deferrals are recorded
4. changed code, configuration, tests, validators, documentation, and generated outputs are reconciled with current repository truth
5. final verification commands are identified and runnable

The plan may be marked `completed` only when `skill-verification-before-completion`:

1. runs fresh final verification
2. confirms completion criteria against repository evidence
3. finds no unresolved required task, failed required check, stale status, or unrecorded scope deviation
4. returns `verified` and updates plan status

A checked box records progress; it is not proof by itself.
