---
feature_type: modify
feature_name: none
status: draft
summary: "Update FitCV skills and repo governance so the new Memory and Hook layers are part of normal debugging, execution, and closeout workflows."
invariants:
  - "agent memory must stay curated, compact, and guardrail-oriented"
  - "execution/debug/verification skills should carry the strongest memory expectations"
  - "root instructions should remain concise and only change if alignment wording is needed"
---

# Skill And Rule Memory Hook Alignment Plan

## Spec Anchor

- Spec: [2026-04-10-10-06-skill-and-rule-memory-hook-alignment-spec.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/superpowers/archive/specs/2026-04-10-10-06-skill-and-rule-memory-hook-alignment-spec.md)

## Scope

Update FitCV’s workflow skills and repo-governance layer so the new `docs/operating_system/agent_memory/` and CI-hook model become part of normal execution, debugging, and completion behavior instead of remaining passive context.

## Affected Docs

- feature_yaml: `none`
- feature_history: `none`
- feature_docs: `none`
- cross_cutting_docs:
  - [repo-governance.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/operating_system/repo-governance.md)
- readme: `none`
- generated:
  - [AGENTS.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/AGENTS.md)
  - [docs/AGENTS.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/AGENTS.md)
  - `codex/rules/*.rules`

## Workstreams

### 1. Strengthen `executing-plans`

Target:

- [.agents/skills/executing-plans/SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/executing-plans/SKILL.md)

Changes:

- Add a post-task checkpoint after verification and before marking a task fully complete:
  - did this task reveal a reusable invariant?
  - a reusable pattern?
  - a repeated or important failure?
  - a reusable open question?
- If yes, update the corresponding memory file under `docs/operating_system/agent_memory/`.
- If no, allow normal task completion without forcing a memory edit.

Goal:

- make memory capture a normal part of plan execution closeout

### 2. Strengthen `verification-before-completion`

Target:

- [.agents/skills/verification-before-completion/SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/verification-before-completion/SKILL.md)

Changes:

- Extend the completion gate with a memory-disposition check:
  - if the task involved meaningful failures, retries, or debugging, either
    - update `docs/operating_system/agent_memory/failure-ledger.md`, or
    - explicitly state why no memory update was needed

Goal:

- stop important failure lessons from disappearing once the final verification passes

### 3. Strengthen `systematic-debugging`

Target:

- [.agents/skills/systematic-debugging/SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/systematic-debugging/SKILL.md)

Changes:

- Add an early Phase 1 instruction to consult:
  - [failure-ledger.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/operating_system/agent_memory/failure-ledger.md)
  when the issue may be repeating or resembles a known repo-method failure.
- Keep root-cause investigation as the primary requirement.

Goal:

- use the failure ledger to avoid re-learning known failure modes while preserving debugging rigor

### 4. Add light-touch memory awareness to planning skills

Targets:

- [.agents/skills/brainstorming/SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/brainstorming/SKILL.md)
- [.agents/skills/planning-dispatch/SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.agents/skills/planning-dispatch/SKILL.md)

Changes:

- `brainstorming`
  - add a short note to consult memory when the design touches repo-operating behavior, known repeated issues, or unsettled harness areas
- `planning-dispatch`
  - add a short note that cross-cutting repo-method work may need a memory update during closeout if it yields reusable lessons

Goal:

- keep planning memory-aware without making every plan memory-heavy

### 5. Add the hook-to-memory feedback rule to governance

Target:

- [repo-governance.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/operating_system/repo-governance.md)

Changes:

- Under the hook/enforcement section, add a short rule:
  - repeated or important failures exposed by CI or repo hooks should be turned into one or more of:
    - a memory entry
    - a stronger repo rule
    - a script check
    - a test
    - or an explicit follow-up plan

Goal:

- connect Hooks to Memory and Memory to stronger guardrails

### 6. Review the root instruction layer for wording-only alignment

Target:

- [root-AGENTS.template.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/agent-core/adapters/codex/root-AGENTS.template.md)

Changes:

- Prefer no change unless wording is needed to stay consistent with updated skill behavior.
- If changed, keep the layer concise and refresh generated outputs.

Goal:

- preserve a short, high-signal root activation layer

## Execution Order

1. Update `executing-plans`.
2. Update `verification-before-completion`.
3. Update `systematic-debugging`.
4. Update `brainstorming`.
5. Update `planning-dispatch`.
6. Update `repo-governance.md`.
7. Review `root-AGENTS.template.md` and only edit if wording alignment is needed.
8. If the root template changed, run:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
```

9. Review the final diffs for:
  - memory noise
  - duplicated instructions across root rules and skills
  - over-strong planning requirements

## Validation

### Content Validation

- Confirm `executing-plans` explicitly asks whether a reusable memory update emerged from task execution.
- Confirm `verification-before-completion` requires a memory disposition when meaningful failures or retries occurred.
- Confirm `systematic-debugging` points to the failure ledger without weakening root-cause investigation.
- Confirm `brainstorming` and `planning-dispatch` only add light-touch memory expectations.
- Confirm `repo-governance.md` defines the hook-to-memory-to-guardrail loop.

### Scope Validation

- Confirm no new skill is introduced just for memory maintenance.
- Confirm the root instruction layer stays concise.
- Confirm no file turns Memory into a mandatory diary for every task.

### Generated Validation

- If `root-AGENTS.template.md` changes:
  - run `.\scripts\sync_agent_adapters.ps1`
  - run `.\scripts\verify_agent_adapters.ps1`
  - confirm generated outputs stay in sync

## Risks And Mitigations

### Risk: Over-enforcement creates noise

- Mitigation: put strong requirements in execution/debug/verification skills, but keep planning skills light-touch.

### Risk: Duplicate policy text spreads across too many files

- Mitigation: keep detailed memory workflow rules in skills; keep root instructions and governance summary-level.

### Risk: Memory still remains passive

- Mitigation: explicitly connect CI/hook failures to memory and stronger guardrails in governance and completion workflows.

## Done Criteria

- The five target skill files reflect the new Memory/Hook operating model.
- `repo-governance.md` defines the hook-to-memory feedback loop.
- `root-AGENTS.template.md` is unchanged or lightly aligned, not expanded into a long policy layer.
- Generated agent outputs are refreshed only if the root template changed.
- Final diffs show stronger harness behavior without turning Memory into noisy required ceremony.
