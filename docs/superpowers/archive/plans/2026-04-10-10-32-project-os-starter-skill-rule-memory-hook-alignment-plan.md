---
feature_type: modify
feature_name: none
status: draft
summary: "Sync the second-layer memory and hook skill/governance alignment from FitCV into project-OS-starter."
invariants:
  - "project-OS-starter must stay generic and must not inherit FitCV-specific incidents or product assumptions"
  - "memory expectations should remain strongest in execution, debugging, verification, and governance feedback loops"
  - "root instructions and generated outputs should only change if implementation reveals real wording drift"
---

# Project OS Starter Skill/Rule Memory-Hook Alignment Plan

## Spec Anchor

- Spec: [2026-04-10-10-31-project-os-starter-skill-rule-memory-hook-alignment-spec.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/superpowers/archive/specs/2026-04-10-10-31-project-os-starter-skill-rule-memory-hook-alignment-spec.md)

## Scope

Update [project-OS-starter](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter) so its starter skills and repo-governance layer reflect the second-layer Memory/Hook operating pattern already proven in FitCV.

This pass should add the reusable workflow behavior, not copy FitCV-specific history or expand the starter into a product-shaped repo.

## Affected Docs

- feature_yaml: `none`
- feature_history: `none`
- feature_docs: `none`
- cross_cutting_docs:
  - [executing-plans SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/.agents/skills/executing-plans/SKILL.md)
  - [verification-before-completion SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/.agents/skills/verification-before-completion/SKILL.md)
  - [systematic-debugging SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/.agents/skills/systematic-debugging/SKILL.md)
  - [brainstorming SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/.agents/skills/brainstorming/SKILL.md)
  - [planning-dispatch SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/.agents/skills/planning-dispatch/SKILL.md)
  - [repo-governance.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/docs/operating_system/repo-governance.md)
  - [README.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/README.md)
- readme: [README.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/README.md)
- generated: `none`

## Workstreams

### 1. Strengthen Starter `executing-plans`

Target:

- [executing-plans SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/.agents/skills/executing-plans/SKILL.md)

Changes:

- Add the same post-task memory checkpoint now used in FitCV:
  - did the completed task produce a reusable invariant?
  - a reusable pattern?
  - a repeated or important failure?
  - a reusable open question?
- If yes, point the workflow to the relevant file under `docs/operating_system/agent_memory/`.
- If no, allow the task to close normally without forcing a memory edit.

Goal:

- make memory capture part of execution closeout without turning it into ceremony

### 2. Strengthen Starter `verification-before-completion`

Target:

- [verification-before-completion SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/.agents/skills/verification-before-completion/SKILL.md)

Changes:

- Add a memory-disposition checkpoint:
  - when work involved meaningful failures, retries, or debugging loops, either
    - update the relevant memory file, or
    - explicitly state why no memory update was needed

Goal:

- prevent important lessons from disappearing once verification turns green

### 3. Strengthen Starter `systematic-debugging`

Target:

- [systematic-debugging SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/.agents/skills/systematic-debugging/SKILL.md)

Changes:

- Add an early instruction to consult `docs/operating_system/agent_memory/failure-ledger.md` when the issue looks repeated, familiar, or method-related.
- Keep root-cause investigation as the primary debugging requirement.

Goal:

- let the failure ledger accelerate debugging without replacing disciplined investigation

### 4. Add Light-Touch Memory Awareness To Starter Planning Skills

Targets:

- [brainstorming SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/.agents/skills/brainstorming/SKILL.md)
- [planning-dispatch SKILL.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/.agents/skills/planning-dispatch/SKILL.md)

Changes:

- `brainstorming`
  - add a short note to consult memory when the task touches repo-operating behavior, repeated harness issues, or reusable invariants
- `planning-dispatch`
  - add a short note that cross-cutting operating-system work may yield a reusable memory update during closeout

Goal:

- make planning memory-aware without turning planning into memory bookkeeping

### 5. Add The Hook-To-Memory Feedback Loop To Starter Governance

Target:

- [repo-governance.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/docs/operating_system/repo-governance.md)

Changes:

- Add the generic operating loop:
  - hooks catch failures or drift
  - reusable failures get captured in memory
  - repeated important failures should become stronger guardrails such as rules, checks, tests, or follow-up plans

Goal:

- make Memory an active part of enforcement rather than a passive note layer

### 6. Update Starter README Only If Needed

Target:

- [README.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/README.md)

Changes:

- Add or refine one short note if needed so starter onboarding mentions that execution/verification/debugging now use the memory layer actively.
- Keep this minimal. Do not duplicate detailed skill text in the README.

Goal:

- keep onboarding aligned without making the README heavy

### 7. Review Root Instruction And Generated Surfaces

Targets:

- [root-AGENTS.template.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/agent-core/adapters/codex/root-AGENTS.template.md)
- generated adapter outputs only if the root template changes

Changes:

- Prefer no change.
- If wording drift exists after the skill/governance sync, make the smallest possible root-template alignment and then regenerate outputs.

Goal:

- preserve a short, high-signal root layer

## Execution Order

1. Create a working branch in [project-OS-starter](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter).
2. Update starter `executing-plans`.
3. Update starter `verification-before-completion`.
4. Update starter `systematic-debugging`.
5. Update starter `brainstorming`.
6. Update starter `planning-dispatch`.
7. Update starter `repo-governance.md`.
8. Review `README.md` and only make a small onboarding alignment change if needed.
9. Review `root-AGENTS.template.md` and only edit if wording drift remains after the skill/governance sync.
10. If the root template changed, run:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
```

11. Run:

```powershell
.\scripts\verify_agent_adapters.ps1
.\scripts\publish_public_repo.ps1
```

12. Review final diffs for genericity, then commit and push the starter branch.

## Validation

### Content Validation

- Confirm starter `executing-plans` includes the post-task reusable-memory checkpoint.
- Confirm starter `verification-before-completion` requires a memory disposition after meaningful failures or retries.
- Confirm starter `systematic-debugging` consults the failure ledger early without weakening root-cause rigor.
- Confirm starter `brainstorming` and `planning-dispatch` add only light-touch memory awareness.
- Confirm starter `repo-governance.md` defines the hook-to-memory-to-guardrail loop.

### Genericity Validation

- Search for leftover starter-breaking drift:
  - `FitCV`
  - `JOB-PROJECT`
  - `src/fitcv`
- Confirm the synced wording reads like reusable repo-operating guidance, not a copied FitCV incident history.

### Verification Validation

- If `root-AGENTS.template.md` changed:
  - run `.\scripts\sync_agent_adapters.ps1`
  - run `.\scripts\verify_agent_adapters.ps1`
- In all cases:
  - run `.\scripts\verify_agent_adapters.ps1`
  - run `.\scripts\publish_public_repo.ps1`

### Scope Validation

- Confirm no new starter skill is introduced just for memory maintenance.
- Confirm the starter root layer stays concise.
- Confirm the starter README remains summary-level and does not duplicate the skill internals.

## Risks And Mitigations

### Risk: The starter becomes too prescriptive

- Mitigation: keep strong memory expectations in execution, debugging, and verification; keep planning and README changes light.

### Risk: FitCV-specific wording leaks into the starter

- Mitigation: review every synced paragraph for product references and replace repo-specific incidents with generic operating language.

### Risk: Root-template churn causes unnecessary generated refresh

- Mitigation: only touch the root template if the skill/governance sync leaves a real wording mismatch.

## Done Criteria

- `project-OS-starter` reflects the second-layer memory/hook alignment in the five target skills.
- starter `repo-governance.md` includes the hook -> memory -> stronger guardrail feedback loop.
- starter `README.md` is updated only if a small onboarding alignment is actually helpful.
- starter root instructions and generated outputs remain unchanged unless a real wording drift requires refresh.
- starter verification passes and no FitCV-specific wording remains.
