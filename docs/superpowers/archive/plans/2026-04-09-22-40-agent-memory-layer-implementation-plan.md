---
feature_type: add
feature_name: none
status: planned
summary: "Implement a lightweight agent-memory layer under docs/operating_system and wire it into the root agent instruction surface without introducing a full wiki subsystem."
---

# Agent Memory Layer Implementation Plan

**Feature:** `none`  
**Spec:** `docs/superpowers/archive/specs/2026-04-09-22-25-agent-memory-layer-spec.md`  
**Type:** `add`  
**Status:** `planned`  

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Add a small, operational `agent_memory` layer that preserves invariants, recurring failures, reusable patterns, and open questions, and make the root agent instructions activate that memory at the right moments.

**Architecture:** The implementation adds one new operating-system subdirectory under `docs/operating_system/agent_memory/`, seeds it with four focused memory files plus a README, and updates the root Codex template so generated `AGENTS.md` points agents at the new memory loop. The first rollout stays intentionally small: it reuses the existing doc system, sync/verify workflow, and generated adapter model rather than introducing new runtime code, a wiki platform, or broad skill rewrites.

**Key Invariants:**
- Agent memory stays small and operational rather than becoming a second general-purpose wiki.
- `agent-core/adapters/codex/root-AGENTS.template.md` remains the source of truth for root instruction changes.
- `AGENTS.md` must be regenerated through the existing sync and verify scripts rather than edited directly.
- Important failure-ledger entries should point to a current guardrail or a clearly named follow-up to add one.

**Rollout / Revert:**  
- rollback_trigger: the memory layer adds too much instruction bulk or creates confusion about where current truth lives  
- rollback_method: revert the `agent_memory/` directory, the root template update, and the regenerated `AGENTS.md` in one commit  

---

## Doc Update Matrix

- Feature contract: `none`
- Stage contracts: `none`
- Feature history: `none`
- Feature-specific docs: `none`
- Cross-cutting docs:
  - `docs/operating_system/repo-governance.md`
  - `docs/operating_system/agent_memory/README.md`
  - `docs/operating_system/agent_memory/invariants.md`
  - `docs/operating_system/agent_memory/patterns.md`
  - `docs/operating_system/agent_memory/failure-ledger.md`
  - `docs/operating_system/agent_memory/open-questions.md`
- README: `none`
- Generated discovery: `none`

## File Map

### Create

- `docs/operating_system/agent_memory/README.md`
- `docs/operating_system/agent_memory/invariants.md`
- `docs/operating_system/agent_memory/patterns.md`
- `docs/operating_system/agent_memory/failure-ledger.md`
- `docs/operating_system/agent_memory/open-questions.md`

### Modify

- `agent-core/adapters/codex/root-AGENTS.template.md`
- `docs/operating_system/repo-governance.md`

### Generated / Refresh

- `AGENTS.md`

### Verify

- `scripts/sync_agent_adapters.ps1`
- `scripts/verify_agent_adapters.ps1`

## Scope Decisions

### Included in the first rollout

- the `agent_memory/` directory and initial file scaffolding
- a concise activation contract in the root agent template
- a repo-governance update that names the new memory layer
- initial content rubrics and seed entries for each memory file
- regeneration and verification of `AGENTS.md`

### Explicitly deferred

- changes to debugging or verification skills
- generated AI-facing exports such as `agent-memory.txt`
- `sources/`, `entities/`, `concepts/`, or other full wiki structures
- CI checks for memory freshness
- automatic incident ingestion from chat or terminal history

## Task 1: Create the agent-memory directory and README

**Files:**
- Create: `docs/operating_system/agent_memory/README.md`
- Docs: `docs/operating_system/repo-governance.md`

- [ ] Step 1: Create `docs/operating_system/agent_memory/`.
- [ ] Step 2: Add `README.md` explaining:
  - what agent memory is for
  - which file types exist
  - when each file should be consulted
  - how new memory entries should be added
- [ ] Step 3: State clearly that agent memory complements, but does not replace, feature docs, specs, plans, or existing operating-system docs.
- [ ] Step 4: Add the rule that repeated failures should become rules, tests, scripts, hooks, or explicit follow-up work.
- [ ] Step 5: Keep the README short and operational rather than encyclopedic.
- [ ] Step 6: Commit the directory scaffold and README.

## Task 2: Seed the stable memory files

**Files:**
- Create: `docs/operating_system/agent_memory/invariants.md`
- Create: `docs/operating_system/agent_memory/patterns.md`
- Create: `docs/operating_system/agent_memory/open-questions.md`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Create `invariants.md` with a short list of non-negotiable repo truths that are already stable.
- [ ] Step 2: Seed `invariants.md` with only high-confidence truths such as:
  - generated adapter outputs are regenerated, not hand-edited
  - private/public publication boundaries are strict
  - feature YAML is the current-state anchor when a managed feature is in scope
- [ ] Step 3: Create `patterns.md` with short operational workflow entries rather than long explanations.
- [ ] Step 4: Seed `patterns.md` with a small number of recurring patterns such as:
  - how to handle adapter-source changes
  - how to document cross-cutting operating-system work without inventing a fake feature
  - how to move from spec to plan to execution
- [ ] Step 5: Create `open-questions.md` for unresolved but reusable repo ambiguities.
- [ ] Step 6: Seed `open-questions.md` only with questions that may affect future agent behavior, not transient implementation details.
- [ ] Step 7: Review all three files and remove anything that duplicates existing source-of-truth docs unnecessarily.
- [ ] Step 8: Commit the stable memory files.

## Task 3: Create the failure ledger with an operational entry format

**Files:**
- Create: `docs/operating_system/agent_memory/failure-ledger.md`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Create `failure-ledger.md`.
- [ ] Step 2: Add a compact entry template that includes:
  - title
  - date
  - trigger/context
  - what went wrong
  - correct behavior
  - prevention added or required
  - links to relevant docs, tests, scripts, or rules
- [ ] Step 3: Seed the ledger with only one or two meaningful entries based on repo-real failure patterns, not hypothetical noise.
- [ ] Step 4: For each seeded entry, name either:
  - the current guardrail already in place, or
  - the explicit follow-up guardrail still needed
- [ ] Step 5: Keep the ledger focused on repeated or important failures rather than logging every mistake.
- [ ] Step 6: Commit the failure-ledger file.

## Task 4: Wire agent memory into the root template

**Files:**
- Modify: `agent-core/adapters/codex/root-AGENTS.template.md`
- Generated / Refresh: `AGENTS.md`
- Verify: `scripts/sync_agent_adapters.ps1`, `scripts/verify_agent_adapters.ps1`

- [ ] Step 1: Update `agent-core/adapters/codex/root-AGENTS.template.md` to mention `docs/operating_system/agent_memory/`.
- [ ] Step 2: Add only a short activation contract covering:
  - consult relevant memory before planning when applicable
  - consult the failure ledger during debugging or retries
  - update the memory layer when significant reusable lessons emerge
- [ ] Step 3: Avoid copying the actual memory content or file-by-file details into the template.
- [ ] Step 4: Run:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
```

- [ ] Step 5: Confirm `AGENTS.md` reflects the new memory contract and remains generated from the root template.
- [ ] Step 6: Commit the template change and regenerated output.

## Task 5: Update repo governance to name the memory layer

**Files:**
- Modify: `docs/operating_system/repo-governance.md`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Update `docs/operating_system/repo-governance.md` so the operating-system structure explicitly acknowledges `docs/operating_system/agent_memory/` as part of the human-readable repo-governance layer.
- [ ] Step 2: Clarify that the memory layer stores operational agent memory, not product behavior contracts.
- [ ] Step 3: Keep the update small and aligned with the existing ownership model.
- [ ] Step 4: Ensure the revised wording does not imply that agent memory replaces feature docs, specs, or rules.
- [ ] Step 5: Commit the governance doc update if not already committed with earlier tasks.

## Task 6: Review for duplication, bloat, and activation clarity

**Files:**
- Verify: `docs/operating_system/agent_memory/README.md`
- Verify: `docs/operating_system/agent_memory/invariants.md`
- Verify: `docs/operating_system/agent_memory/patterns.md`
- Verify: `docs/operating_system/agent_memory/failure-ledger.md`
- Verify: `docs/operating_system/agent_memory/open-questions.md`
- Verify: `agent-core/adapters/codex/root-AGENTS.template.md`
- Verify: `AGENTS.md`

- [ ] Step 1: Review the new memory files and remove any content that merely repeats existing operating-system docs verbatim.
- [ ] Step 2: Confirm the memory files are short enough to be selectively loaded without becoming context bloat.
- [ ] Step 3: Confirm the root template points to memory at the right moments without turning `AGENTS.md` into a long handbook.
- [ ] Step 4: Confirm every failure-ledger entry names a prevention artifact or explicit follow-up.
- [ ] Step 5: Make any final wording fixes needed to keep the memory layer operational and crisp.
- [ ] Step 6: Commit any review-driven refinements.

## Task 7: Run final verification and inspect the diff

**Files:**
- Verify: `scripts/sync_agent_adapters.ps1`
- Verify: `scripts/verify_agent_adapters.ps1`
- Verify: exact entries from the Doc Update Matrix
- Verify: `AGENTS.md`

- [ ] Step 1: Run:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
git status --short
```

- [ ] Step 2: Confirm sync does not leave unexpected drift after the final edits.
- [ ] Step 3: Review the final diff to ensure the rollout only adds:
  - the memory directory
  - the root template update
  - the regenerated root `AGENTS.md`
  - the repo-governance update
- [ ] Step 4: If any unexpected files changed, investigate before closeout rather than folding them into the same work by default.
- [ ] Step 5: Commit any last verification fixes.

## Validation Commands

Run locally before claiming completion:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
git status --short
```

## Completion Criteria

The implementation is complete when:

- `docs/operating_system/agent_memory/` exists with:
  - `README.md`
  - `invariants.md`
  - `patterns.md`
  - `failure-ledger.md`
  - `open-questions.md`
- the memory files contain concise initial content rather than placeholders only
- `agent-core/adapters/codex/root-AGENTS.template.md` points to the memory layer
- generated `AGENTS.md` is refreshed and verified
- `docs/operating_system/repo-governance.md` acknowledges the new memory layer cleanly
- the final result remains lightweight and does not resemble a full wiki subsystem
