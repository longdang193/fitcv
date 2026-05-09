---
name: skill-executing-plans
description: Use when you have a written implementation plan to execute in a separate
  session with review checkpoints
allowed-tools: []
hooks:
  pre:
  - python scripts/hooks/run_validator.py --fast
  post:
  - python scripts/hooks/run_validator.py --fast
required_reads:
- docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md
- docs/operating_system/governance/repo-governance.md
tags:
- skill
- execution
- delivery
- skill-executing-plans
required_outputs: []
---

# Executing Plans

## Overview

Load the plan, review it critically, execute task by task, update source-of-truth docs as work lands, then finish the branch.

**Announce at start:** "I'm using the skill-executing-plans skill to implement this plan."

**If subagents are available:** prefer `superpowers:skill-subagent-driven-development` for higher quality. Otherwise use this skill.

---

## Mandatory Read

<MUST-READ>
Before execution starts, read:

- the specific implementation plan file being executed
- `docs/operating_system/templates/implementation-plan-template.md` to confirm canonical plan structure
- `docs/operating_system/templates/implementation-execution-map-template.md` when upstream multi-lane orchestration is in scope
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/planning/planning-dispatch.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `docs/operating_system/lifecycle/feature-lifecycle.md` when feature-owned work is in scope
- `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`
- `docs/operating_system/workflows/workflow-spec-to-plan-to-execution.md`
- `docs/operating_system/workflows/workflow-drift-detection-and-reconciliation.md`
</MUST-READ>

## Lifecycle Compliance

- Keep execution inside the approved triaged layer and bounded thread/plan scope.
- Treat plans as execution guides, not upstream truth; update owning source layers as work lands.
- Refresh generated feature, stage, history, and discovery surfaces from source when in scope.
- Do not hand-edit generated managed surfaces to satisfy completion claims.
- Respect the standardized implementation-plan shape and keep task/wave sequencing consistent with any approved implementation execution map.

## GitNexus Usage

Use GitNexus selectively during execution when cross-file coordination is
non-trivial.

- Prefer GitNexus for shared-module impact checks and cross-lane dependency tracing.
- For small/local execution tasks, GitNexus is optional.
- Before high-trust use, check freshness: <LINK>`.\\scripts\\get_gitnexus_freshness.ps1`</LINK>
- If stale, keep GitNexus advisory and execute source-first.
- If GitNexus conflicts with source/docs/tests, trust source/docs/tests.
- If GitNexus has tooling or query issues, consult the `gitnexus-guide` skill first; if unresolved, continue source-first.

## Source-of-Truth Rule

During execution, keep these layers in sync:

```text
code/                                 → real truth
docs/intent/*.md                     → project purpose and outcome sources
docs/operating_system/*.md           → repo method and governance sources
docs/stages/*.source.yaml            → human-owned stage source
docs/stages/*.yaml                   → generated stage contract
docs/features/*/feature.source.yaml  → human-owned feature source
docs/features/*/<feature_id>.yaml    → generated feature contract
docs/features/*/lineage.generated.yaml → generated feature evidence
docs/features/<feature_id>/          → feature-specific explanation + partial-generated history
docs/*.md                            → cross-cutting product explanation
README.md                            → overview
docs/generated/                      → generated discovery
```

Do not treat the plan as the source of truth.
The plan guides execution; the source layers must be updated as changes are completed.

---

## The Process

### Step 1: Load and Review Plan

1. Read the plan file
2. Read the linked spec and the minimum truthful set for any affected feature folder:
   - `docs/intent/*.md` when the plan layer is `intent`
   - `docs/operating_system/*.md` when the plan layer is `operating_system`
   - `feature.source.yaml` first
   - generated `docs/features/<feature_id>/<feature_id>.yaml` when the assembled contract is needed
   - `lineage.generated.yaml` for evidence, ownership, or drift work
   - `history.md` only when narrative context matters
   - if stage-aware work is in scope, read `docs/stages/<stage_id>.source.yaml`
     before the generated stage contract
3. Confirm the plan still matches the canonical implementation-plan template shape and any approved implementation-execution-map ordering
4. Review critically for gaps, ambiguity, or missing prerequisites
5. If concerns exist, raise them before starting
6. If clear, create TodoWrite and proceed

### Step 2: Execute Tasks

For each task:

1. Mark it `in_progress`
2. Follow plan steps exactly
3. Select the next action using `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`.
4. Do not invent unrelated next steps; choose only from approved roadmap/workstream/thread/spec/map/plan artifacts.
5. Run required verifications
6. Update affected source layers as part of the task:

- code
- `docs/intent/*.md` when project-purpose sources change
- `docs/operating_system/*.md` when repo method or governance changes
- `docs/stages/*.source.yaml` when stage meaning changes
- `docs/features/*/feature.source.yaml` if current feature state changed
- `docs/features/<feature_id>/history.md` only when human explanation/history notes changed
- other focused docs under `docs/features/<feature_id>/` if feature-specific explanation changed
- `docs/*.md` if cross-cutting product explanation changed
- `README.md` if navigation changed
- before marking the task fully complete, decide whether execution revealed a reusable memory update:
  - invariant → `docs/operating_system/agent_memory/invariants.md`
  - pattern → `docs/operating_system/agent_memory/patterns.md`
  - repeated or important failure → `docs/operating_system/agent_memory/failure-ledger.md`
  - reusable unresolved question → `docs/operating_system/agent_memory/open-questions.md`

If yes, update the relevant memory file as part of task closeout. If no, complete the task without forcing a memory edit.

1. Mark task `completed`

Do not postpone all doc updates until the end if the task changes current feature state.
Do not hand-edit generated feature contracts, generated stage contracts,
`lineage.generated.yaml`, or generated history blocks; update the owning source
and rerun the canonical sync/check workflow instead.

### Step 3: Final Sync and Verification

After all tasks are complete:

1. Run all final checks in the plan
2. Confirm source layers are in sync:

- code matches shipped behavior
- intent docs reflect current purpose when they were in scope
- operating-system docs reflect current repo method when they were in scope
- stage sources reflect the intended architectural boundary model when they are in scope
- feature sources reflect current state
- docs reflect final explanation/history where needed

1. Run `scripts/sync_architecture_docs.py` when architecture metadata surfaces changed
2. Verify generated files were not edited manually
3. Review diffs for completeness

### Step 4: Complete Development

After code, docs, and generated discovery are all updated and verified:

- Announce: "I'm using the skill-finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use `superpowers:skill-finishing-a-development-branch`
- Follow that skill to verify tests, present options, and complete the branch

---

## Required Doc Update Rule

Before execution is considered complete, the agent must update docs as needed.

Minimum required checks:

- if behavior changed → update code
- if project-purpose sources changed → update `docs/intent/*.md`
- if repo method or governance changed → update `docs/operating_system/*.md`
- if stage-aware boundary docs changed → update `docs/stages/*.source.yaml` when in scope
- if current feature state changed → update `docs/features/*/feature.source.yaml`
- if feature-specific explanation/history changed → update `docs/features/<feature_id>/`
- if cross-cutting product explanation changed → update `docs/*.md`
- if navigation changed → update `README.md`
- if execution revealed a reusable memory lesson → update `docs/operating_system/agent_memory/*`
- after architecture source changes → rerun the canonical architecture sync/check workflow

Do not finish execution with stale feature YAML or stale generated discovery.

Before completion, list the exact files updated or intentionally left unchanged for:

- `docs/intent/*.md` when in scope
- `docs/operating_system/*.md` when in scope
- `docs/stages/<stage_id>.source.yaml` when in scope
- `docs/stages/<stage_id>.yaml` when in scope
- `docs/features/<feature_id>/feature.source.yaml`
- `docs/features/<feature_id>/<feature_id>.yaml`
- `docs/features/<feature_id>/lineage.generated.yaml`
- `docs/features/<feature_id>/history.md`
- any other focused docs under `docs/features/<feature_id>/`
- any cross-feature docs under `docs/*.md`
- any memory files under `docs/operating_system/agent_memory/` that changed or were intentionally left unchanged
- `README.md`
- regenerated `docs/generated/*`

Use this completion checklist:

- intent docs updated?
- operating-system docs updated?
- stage sources updated?
- stage contracts updated?
- feature sources updated?
- contract updated?
- feature lineage updated?
- feature history updated?
- other feature-specific docs updated?
- cross-cutting docs updated?
- agent memory updated or explicitly not needed?
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
- rerun `scripts/sync_architecture_docs.py` before finishing when architecture metadata changed
- prefer `scripts/sync_architecture_docs.py` as the canonical architecture sync/check workflow when architecture metadata surfaces changed
- stop when blocked
- never implement on main/master without explicit user consent

---

## Integration

**Required workflow skills:**

- `superpowers:skill-using-git-worktrees` — set up isolated workspace before starting
- `superpowers:skill-writing-plans` — creates the plan
- `superpowers:skill-finishing-a-development-branch` — completes the work after execution
