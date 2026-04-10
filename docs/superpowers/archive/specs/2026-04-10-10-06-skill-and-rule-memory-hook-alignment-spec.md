---
feature_type: modify
feature_name: none
status: draft
summary: "Align FitCV skills and repo rules so the new agent-memory and CI-hook layers are used consistently during planning, debugging, execution, and closeout."
invariants:
  - "agent memory must remain curated and guardrail-oriented rather than becoming a task diary"
  - "hook and memory expectations should be enforced primarily through execution/debug/verification workflows, not by making every planning step heavy"
  - "existing root repo instructions should stay concise and only carry high-signal activation guidance"
---

# Skill And Rule Memory Hook Alignment Spec

## Triage

Feature type: `MODIFY`  
Summary: Update FitCV skill and rule surfaces so the newly added agent-memory and CI-hook layers are part of normal execution, debugging, and closeout behavior.  
Reasoning: This changes existing repo-method workflows and skill behavior after the agent-memory and CI-hook plans have landed; it does not create a new product feature.  
Invariants:
- `docs/operating_system/agent_memory/` stays compact, reusable, and selective.
- Skills should consult Memory when it materially helps, not on every trivial task.
- Repeated failures should trend toward stronger guardrails: memory, rules, tests, scripts, or hooks.
- Root instructions should remain short and high-signal.
Dependencies:
- `docs/operating_system/agent_memory/`
- `docs/operating_system/repo-governance.md`
- `agent-core/adapters/codex/root-AGENTS.template.md`
- `.agents/skills/executing-plans/SKILL.md`
- `.agents/skills/verification-before-completion/SKILL.md`
- `.agents/skills/systematic-debugging/SKILL.md`
- `.agents/skills/brainstorming/SKILL.md`
- `.agents/skills/planning-dispatch/SKILL.md`
Affected stages:
- `none`
Affected features:
- `none`
Primary lens: `feature`
Affected docs:
  feature_yaml: `none`
  feature_history: `none`
  feature_docs: `none`
  cross_cutting_docs:
    - `docs/operating_system/repo-governance.md`
  readme: `none`
  generated: `AGENTS.md`, `docs/AGENTS.md`, `codex/rules/*.rules`
Generated refresh required: `yes`
Spec needed: `yes`
Plan needed: `yes`

## Context

FitCV now has two new operating-system layers:

- `docs/operating_system/agent_memory/`
- CI-based repo hooks via `.github/workflows/repo-hooks.yml`

The repo already has a lightweight root activation contract in [root-AGENTS.template.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/agent-core/adapters/codex/root-AGENTS.template.md), but the execution-oriented skills still behave as if Memory and Hooks are optional context rather than part of the normal harness loop.

Without follow-up alignment, the likely failure mode is:

- Memory exists but is not consulted at the right times
- CI catches failures, but those lessons do not feed back into memory or stronger guardrails
- execution plans close without deciding whether a reusable lesson should be retained

## Goals

- Make Memory a standard input during debugging and execution closeout when relevant.
- Make the post-execution question "should this update Memory?" explicit.
- Ensure repeated CI/hook failures feed back into memory and then into stronger constraints when appropriate.
- Keep planning skills and root rules light enough that the repo does not become overloaded with mandatory memory lookups.

## Non-Goals

- Do not require memory review for every trivial task.
- Do not turn Memory into a task log or session diary.
- Do not introduce a brand-new skill solely for memory maintenance.
- Do not expand root instructions into a long policy manual.

## Proposed Changes

### 1. `executing-plans` should gain a memory closeout checkpoint

Primary target:

- [.agents/skills/executing-plans/SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/executing-plans/SKILL.md)

Change:

- After each task is verified but before it is considered fully complete, add an explicit checkpoint:
  - did this task reveal a reusable invariant?
  - did it reveal a reusable pattern?
  - did it reveal a repeated or important failure?
  - did it surface an unresolved reusable question?

If yes:

- update the relevant file under `docs/operating_system/agent_memory/`
- mention that update in the task closeout

If no:

- allow the task to complete without forced memory churn

Reason:

- this is the highest-leverage place to prevent memory from being forgotten after plan execution

### 2. `verification-before-completion` should require explicit memory disposition

Primary target:

- [.agents/skills/verification-before-completion/SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/verification-before-completion/SKILL.md)

Change:

- Extend the completion gate so that when meaningful retries, failures, or debugging happened during the task, the agent must either:
  - update `docs/operating_system/agent_memory/failure-ledger.md`, or
  - state explicitly why no memory update was needed

This should be framed as evidence and disposition, not as mandatory memory editing.

Reason:

- this prevents repeated failure lessons from disappearing once the final verification passes

### 3. `systematic-debugging` should consult the failure ledger early

Primary target:

- [.agents/skills/systematic-debugging/SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/systematic-debugging/SKILL.md)

Change:

- Add a Phase 1 step near the beginning:
  - consult `docs/operating_system/agent_memory/failure-ledger.md` when the issue may be repeating or resembles a known repo-method failure

This should not replace root-cause investigation.
It should help avoid re-learning the same failure modes.

Reason:

- debugging is where the failure ledger delivers the most immediate value

### 4. Planning skills should add only light-touch memory awareness

Primary targets:

- [.agents/skills/brainstorming/SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/brainstorming/SKILL.md)
- [.agents/skills/planning-dispatch/SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/planning-dispatch/SKILL.md)

Changes:

- `brainstorming`
  - add a small note to consult Memory when the design touches repo-operating behavior, known repeated issues, or unsettled harness areas
- `planning-dispatch`
  - add a small triage/closeout note that cross-cutting repo-method work may need a memory update when it yields reusable lessons

Reason:

- planning should be memory-aware, but not memory-heavy
- the repo should avoid making every plan start with a broad memory review when the task is ordinary product work

### 5. Repo governance should define the hook-to-memory feedback loop

Primary target:

- [repo-governance.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/operating_system/repo-governance.md)

Change:

- Add a short rule under the hook or operating-system section:
  - when CI or repo hooks expose a repeated or important failure mode, convert that lesson into one or more of:
    - a memory entry
    - a stronger repo rule
    - a script check
    - a test
    - a follow-up plan if immediate hardening is not appropriate

Reason:

- this turns Hooks into a learning loop rather than a one-time gate

### 6. Root instruction layer should stay mostly as-is

Primary target:

- [root-AGENTS.template.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/agent-core/adapters/codex/root-AGENTS.template.md)

Recommendation:

- no major expansion
- only make wording adjustments if needed for consistency with the updated skills

Current state is already close to sufficient:

- consult relevant memory before planning when appropriate
- consult the failure ledger during debugging/retries
- update memory when a reusable lesson emerges

Reason:

- the detailed operating behavior belongs in the skills, not in a bloated root instruction layer

## Exact File Targets

### Expected to change

- `.agents/skills/executing-plans/SKILL.md`
- `.agents/skills/verification-before-completion/SKILL.md`
- `.agents/skills/systematic-debugging/SKILL.md`
- `.agents/skills/brainstorming/SKILL.md`
- `.agents/skills/planning-dispatch/SKILL.md`
- `docs/operating_system/repo-governance.md`

### May change if consistency wording is needed

- `agent-core/adapters/codex/root-AGENTS.template.md`

### Expected generated refresh if root template changes

- `AGENTS.md`
- `docs/AGENTS.md`
- `codex/rules/*.rules`

## Acceptance Criteria

- `executing-plans` explicitly asks whether task execution produced a reusable memory update before final task closeout.
- `verification-before-completion` requires an explicit memory disposition when meaningful failures or retries occurred.
- `systematic-debugging` instructs agents to consult the failure ledger when the issue may be repeating.
- `brainstorming` and `planning-dispatch` gain light-touch memory awareness without making memory review mandatory for every task.
- `repo-governance.md` defines the hook-to-memory-to-guardrail feedback loop.
- root instructions remain concise and are only updated if needed for alignment.

## Risks

### Risk: Memory becomes mandatory noise

If every skill forces a memory review or memory update on every task, agents will either ignore the layer or spam it with low-value notes.

Mitigation:

- only execution, debugging, and completion skills get stronger requirements
- planning skills stay light-touch

### Risk: Memory becomes a passive note system

If failures are logged but never turned into stronger rules or tests, the repo gains documentation but not real reliability.

Mitigation:

- governance should explicitly connect hooks, failures, memory, and stronger guardrails

### Risk: Root instructions get too long

If detailed workflow behavior is pushed into the root instruction layer, the repo loses signal quality.

Mitigation:

- keep operational detail in skills
- keep root rules as activation guidance only

## Recommended Follow-Up

After this spec is approved:

1. write an implementation plan for the skill/rule alignment
2. update the six target files first
3. refresh generated agent outputs only if the root template changes
4. do a drift review against the new Memory and Hook operating model after implementation
