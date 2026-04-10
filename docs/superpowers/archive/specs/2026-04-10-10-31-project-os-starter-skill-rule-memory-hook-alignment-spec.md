---
feature_type: modify
feature_name: none
status: draft
summary: "Sync the second-layer memory and hook skill alignment from FitCV into project-OS-starter."
---

# Project OS Starter Skill/Rule Memory-Hook Alignment Spec

## Triage

Feature type: `MODIFY`  
Summary: Sync the generic second-layer memory and hook alignment from `JOB-PROJECT` into `project-OS-starter` so the starter reflects the current operating loop.  
Reasoning: The starter already contains the first-layer memory and hook infrastructure, but its skills and governance still lag the proven FitCV operating pattern.  
Invariants:
- `project-OS-starter` remains generic and must not absorb FitCV-specific failures, product assumptions, or repo structure beyond starter-owned paths.
- Memory guidance should stay strongest in execution, verification, debugging, and governance feedback loops.
- Root instructions should remain lightweight unless wording drift makes a starter sync necessary.
- Generated adapter outputs remain derived artifacts, not the source of truth.
Dependencies:
- `docs/operating_system/agent_memory/`
- `.agents/skills/`
- `docs/operating_system/repo-governance.md`
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
    - `.agents/skills/executing-plans/SKILL.md`
    - `.agents/skills/verification-before-completion/SKILL.md`
    - `.agents/skills/systematic-debugging/SKILL.md`
    - `.agents/skills/brainstorming/SKILL.md`
    - `.agents/skills/planning-dispatch/SKILL.md`
    - `README.md`
  readme: `README.md`
  generated: `none`
Generated refresh required: `no`
Spec needed: `yes`
Plan needed: `yes`

## Problem

`project-OS-starter` already includes:

- the memory layer under `docs/operating_system/agent_memory/`
- the CI hook workflow
- starter-safe adapter and publication script hardening

But it still lacks the second-layer operating behavior that FitCV now uses to keep Memory and Hooks alive in everyday work:

- `executing-plans` does not ask whether completed work produced reusable memory
- `verification-before-completion` does not require a memory disposition after meaningful failures or retries
- `systematic-debugging` does not consult the failure ledger early
- `brainstorming` and `planning-dispatch` do not include the lightweight memory-aware routing added in FitCV
- starter governance does not yet define the hook -> memory -> stronger guardrail feedback loop

This means the starter contains the mechanism, but not yet the workflow habits that make the mechanism useful.

## Goal

Bring `project-OS-starter` up to the current generic operating pattern by syncing the proven second-layer skill and governance updates from FitCV while keeping the starter product-agnostic.

## Non-Goals

- copying any FitCV-specific failure-ledger entries
- changing starter runtime or product examples
- expanding the root adapter template unless real starter drift requires it
- introducing feature YAML or product-specific docs into the starter

## Scope

Sync these generic updates into `project-OS-starter`:

1. `.agents/skills/executing-plans/SKILL.md`
2. `.agents/skills/verification-before-completion/SKILL.md`
3. `.agents/skills/systematic-debugging/SKILL.md`
4. `.agents/skills/brainstorming/SKILL.md`
5. `.agents/skills/planning-dispatch/SKILL.md`
6. `docs/operating_system/repo-governance.md`
7. `README.md` only if the starter’s onboarding needs one short note about memory-aware execution/verification

Do not sync:

- archived FitCV specs or plans
- product-specific examples
- FitCV runtime/test changes
- any memory content that records FitCV-only incidents

## Design

### 1. Make execution memory-aware

Update the starter copy of `executing-plans` so task execution includes a compact closeout checkpoint:

- after each substantial completed task, ask whether it produced a reusable invariant, pattern, failure, or open question
- if yes, update the appropriate file in `docs/operating_system/agent_memory/`
- if no, continue without forcing noise into the memory layer

This keeps Memory curated and conditional instead of mandatory for every tiny task.

### 2. Make verification require a memory disposition

Update `verification-before-completion` so successful verification is not just green commands. When meaningful failures, retries, or corrective loops happened during the work, the agent must either:

- update the relevant memory file, or
- explicitly note why no memory update was needed

This closes the loop between execution and long-term operational learning.

### 3. Make debugging consult memory earlier

Update `systematic-debugging` so repeated or suspiciously familiar failures consult `docs/operating_system/agent_memory/failure-ledger.md` early in the process.

This should not replace root-cause investigation. It should simply bias the workflow toward checking whether the failure mode is already known before inventing a fresh theory.

### 4. Keep planning memory-aware but light

Update `brainstorming` and `planning-dispatch` with lightweight memory awareness only:

- `brainstorming` should consult memory when repo-operating behavior, repeated harness issues, or reusable invariants are likely to matter
- `planning-dispatch` should note when cross-cutting operating-system work is likely to produce a reusable memory update during closeout

These planning skills should not become heavy memory procedures. Their job is routing and design, not memory bookkeeping.

### 5. Add the governance feedback loop

Update starter `repo-governance.md` to define the reusable control loop:

- Hooks catch failures or drift
- repeated or reusable failures get summarized in Memory
- important repeated failures should then become a stronger guardrail such as a rule, script check, or test

This turns memory from passive notes into an intermediate layer between incidents and enforcement.

## Source Alignment

The sync should be derived from the already-proven generic FitCV changes now present in:

- `JOB-PROJECT/.agents/skills/executing-plans/SKILL.md`
- `JOB-PROJECT/.agents/skills/verification-before-completion/SKILL.md`
- `JOB-PROJECT/.agents/skills/systematic-debugging/SKILL.md`
- `JOB-PROJECT/.agents/skills/brainstorming/SKILL.md`
- `JOB-PROJECT/.agents/skills/planning-dispatch/SKILL.md`
- `JOB-PROJECT/docs/operating_system/repo-governance.md`

The starter sync should copy only the generic operating behavior, not FitCV-specific wording that depends on this repo’s exact product context.

## Validation

The sync is complete when:

- starter skills reflect the new memory-aware execution, verification, debugging, and light planning behavior
- starter governance describes the hook -> memory -> stronger guardrail loop
- no `FitCV`, `JOB-PROJECT`, or product-specific path assumptions are introduced into the starter
- starter scripts still pass:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
.\scripts\publish_public_repo.ps1
```

- no generated refresh is performed unless a root template change becomes necessary during implementation

## Recommendation

Proceed with a narrow sync plan that updates only the six proven generic surfaces above. Keep the starter’s root instruction layer and generated outputs unchanged unless implementation reveals real wording drift that cannot be resolved in the skill/governance layer alone.
