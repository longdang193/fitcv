---
name: executing-plans
description: Use when you have a written implementation plan to execute in a separate session with review checkpoints
---

# Executing Plans

## Overview

Load the plan, review it critically, execute task by task, update source-of-truth docs as work lands, then finish the branch.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

**If subagents are available:** prefer `superpowers:subagent-driven-development` for higher quality. Otherwise use this skill.

---

## Source-of-Truth Rule

During execution, keep these layers in sync:

```text
code/                       → real truth
docs/stages/*.yaml          → stage contracts when stage-aware docs are in scope
docs/features/*/*.yaml        → structured truth
docs/features/<feature_id>/ → feature-specific explanation + history
docs/*.md                   → cross-cutting explanation
README.md                   → overview
docs/generated/             → generated discovery
```

Do not treat the plan as the source of truth.
The plan guides execution; the source layers must be updated as changes are completed.

---

## The Process

### Step 1: Load and Review Plan

1. Read the plan file
2. Read the linked spec and affected `docs/features/<feature_id>/<feature_id>.yaml`
3. Review critically for gaps, ambiguity, or missing prerequisites
4. If concerns exist, raise them before starting
5. If clear, create TodoWrite and proceed

### Step 2: Execute Tasks

For each task:

1. Mark it `in_progress`
2. Follow plan steps exactly
3. Run required verifications
4. Update affected source layers as part of the task:

- code
- `docs/stages/*.yaml` when stage-aware contracts are in scope
- `docs/features/*/*.yaml` if current feature state changed
- `docs/features/<feature_id>/history.md` or other focused docs if feature-specific explanation/history changed
- `docs/*.md` if cross-cutting explanation changed
- `README.md` if navigation changed

1. Mark task `completed`

Do not postpone all doc updates until the end if the task changes current feature state.

### Step 3: Final Sync and Verification

After all tasks are complete:

1. Run all final checks in the plan
2. Confirm source layers are in sync:

- code matches shipped behavior
- stage contracts reflect the current architectural boundary model when they are in scope
- feature YAML reflects current state
- docs reflect final explanation/history where needed

1. Regenerate `docs/generated/*`
2. Verify generated files were not edited manually
3. Review diffs for completeness

### Step 4: Complete Development

After code, docs, and generated discovery are all updated and verified:

- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use `superpowers:finishing-a-development-branch`
- Follow that skill to verify tests, present options, and complete the branch

---

## Required Doc Update Rule

Before execution is considered complete, the agent must update docs as needed.

Minimum required checks:

- if behavior changed → update code
- if stage-aware boundary docs changed → update `docs/stages/*.yaml` when in scope
- if current feature state changed → update `docs/features/*/*.yaml`
- if feature-specific explanation/history changed → update `docs/features/<feature_id>/`
- if cross-cutting explanation changed → update `docs/*.md`
- if navigation changed → update `README.md`
- after source changes → regenerate `docs/generated/*`

Do not finish execution with stale feature YAML or stale generated discovery.

Before completion, list the exact files updated or intentionally left unchanged for:

- `docs/stages/<stage_id>.yaml` when in scope
- `docs/features/<feature_id>/<feature_id>.yaml`
- `docs/features/<feature_id>/history.md`
- any other focused docs under `docs/features/<feature_id>/`
- any cross-feature docs under `docs/*.md`
- `README.md`
- regenerated `docs/generated/*`

Use this completion checklist:

- stage contracts updated?
- contract updated?
- feature history updated?
- other feature-specific docs updated?
- cross-cutting docs updated?
- README updated?
- generated docs refreshed?

---

## When to Stop and Ask for Help

Stop immediately when:

- blocked by missing dependency or access
- plan has critical gaps
- an instruction is unclear
- verification fails repeatedly
- feature/doc updates required by the change are unclear

Ask instead of guessing.

---

## When to Revisit Review

Return to review when:

- the plan is updated
- the spec changed
- the feature contract changed materially
- the implementation approach no longer matches the plan

---

## Remember

- review first
- execute task by task
- do not skip verifications
- keep source-of-truth layers updated during execution
- regenerate `docs/generated/*` before finishing
- stop when blocked
- never implement on main/master without explicit user consent

---

## Integration

**Required workflow skills:**

- `superpowers:using-git-worktrees` — set up isolated workspace before starting
- `superpowers:writing-plans` — creates the plan
- `superpowers:finishing-a-development-branch` — completes the work after execution

