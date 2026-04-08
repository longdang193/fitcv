# Stage-Aware Project Operating System Implementation Plan

**Feature:** `none (cross-cutting operating-system change; no new managed feature contract)`  
**Spec:** `docs/superpowers/specs/2026-03-31-stage-aware-project-operating-system-design.md`  
**Type:** modify  
**Status:** planned  

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

## Status Snapshot

- Completed:
  - Task 1: update the Cursor operating-system rules, including the new `stage-lifecycle` rule
  - Task 2: update the mirrored planning and design skills for stage-aware vocabulary
  - Task 3: update `writing-plans` and `executing-plans` for cross-cutting stage-aware work
  - Task 4: run the final sync and review pass, including the bounded spec sync
- Partially complete:
  - none
- Pending:
  - none

**Goal:** Update the Cursor operating-system rules and mirrored `.agents` skills so stages become a first-class documentation and planning lens above features, without yet rolling the model into project-specific stage files or feature contracts.

**Architecture:** Phase 1 is a documentation-method rollout, not a product feature rollout. This plan is intentionally limited to the operating-system control surface: Cursor rules and mirrored `.agents` skills. It defines the stage-aware model and triage language first, so later project-specific work can adopt stage contracts, feature metadata, and generated discovery against a stable operating-system vocabulary.

**Key Invariants:**
- `docs/features/*/*.yaml` remains the primary current-state contract layer for capabilities.
- This plan does not yet create `docs/stages/*.yaml` or modify project feature contracts.
- Rules and mirrored skills must describe the same operating system.
- Project-specific generated discovery changes are deferred to a later plan.

**Rollout / Revert:**  
- rollback_trigger: stage-aware triage causes repeated doc-placement mistakes or conflicting planning guidance across rules and skills  
- rollback_method: revert the rules and mirrored skills together, returning to the current feature-only operating-system model  

---

## Doc Update Matrix

- Feature contract: `none`
- Feature history: `none`
- Feature-specific docs: `none`
- Cross-cutting docs:
  - `.cursor/rules/project-operating-system.mdc`
  - `.cursor/rules/operating-system/doc-system-lifecycle.md`
  - `.cursor/rules/operating-system/stage-lifecycle.md`
  - `.cursor/rules/operating-system/feature-lifecycle.md`
  - `.cursor/rules/operating-system/planning-dispatch.md`
  - `docs/superpowers/specs/2026-03-31-stage-aware-project-operating-system-design.md`
- README: `none`
- Generated discovery: `none`

## Stage and Adoption Scope

- Affected stages: `none (meta operating-system change introducing stage-aware docs)`
- Affected features for later project adoption:
  - `cv_system`
  - `trigger_run_management`
  - `inspection_debugging`
- Primary lens: mixed

## File Structure First

- Modify:
  - `.cursor/rules/project-operating-system.mdc`
  - `.cursor/rules/operating-system/doc-system-lifecycle.md`
  - `.cursor/rules/operating-system/stage-lifecycle.md`
  - `.cursor/rules/operating-system/feature-lifecycle.md`
  - `.cursor/rules/operating-system/planning-dispatch.md`
  - `.agents/skills/brainstorming/SKILL.md`
  - `.agents/skills/planning-dispatch/SKILL.md`
  - `.agents/skills/doc-system-lifecycle/SKILL.md`
  - `.agents/skills/writing-plans/SKILL.md`
  - `.agents/skills/executing-plans/SKILL.md`

---

## Task 1: Update the Cursor Operating-System Rules

**Files:**
- Modify: `.cursor/rules/project-operating-system.mdc`
- Modify: `.cursor/rules/operating-system/doc-system-lifecycle.md`
- Modify: `.cursor/rules/operating-system/stage-lifecycle.md`
- Modify: `.cursor/rules/operating-system/feature-lifecycle.md`
- Modify: `.cursor/rules/operating-system/planning-dispatch.md`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Create `stage-lifecycle.md` as the focused rule for:
  - what a stage is
  - how stages relate to features
  - when stage classification is required
  - what stage-aware work must name in triage/specs/plans
- [x] Step 2: Update the top-level operating-system rule so it points to `stage-lifecycle.md` and introduces stages as a navigation layer above features.
- [x] Step 3: Add stage-aware placement and stage-contract ownership boundaries to `doc-system-lifecycle.md`, while keeping stage concepts centralized in `stage-lifecycle.md`.
- [x] Step 4: Update `feature-lifecycle.md` so lifecycle ownership stays feature-based while triage can also classify affected stages.
- [x] Step 5: Update `planning-dispatch.md` so triage requires `Affected stages`, `Affected features`, and `Primary lens` for stage-heavy pipeline work.
- [x] Step 6: Verify rule text is internally consistent with:
  - `rg -n "docs/stages|Affected stages|Primary lens|stage-aware" .cursor\\rules`
- [x] Step 7: Verify stage concepts are defined once in `stage-lifecycle.md` and referenced, not duplicated ad hoc across the other rules.
- [x] Step 8: Update docs if wording in the spec needs a small synchronization pass.
- [ ] Step 9: Commit.

## Task 2: Update the Mirrored Planning and Design Skills

**Files:**
- Modify: `.agents/skills/brainstorming/SKILL.md`
- Modify: `.agents/skills/planning-dispatch/SKILL.md`
- Modify: `.agents/skills/doc-system-lifecycle/SKILL.md`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Write the failing expectation list for skill parity:
  - brainstorming must identify affected stages as well as features for pipeline/architecture work
  - planning-dispatch triage must include stage-aware fields
  - doc-system-lifecycle must describe `docs/stages/*.yaml` as a new layer above features
- [x] Step 2: Apply the minimal text changes to the three mirrored skills so they match the cursor rules exactly.
- [x] Step 3: Run a parity check:
  - `rg -n "docs/stages|Affected stages|Primary lens|stage-aware" .agents\\skills\\brainstorming .agents\\skills\\planning-dispatch .agents\\skills\\doc-system-lifecycle`
- [x] Step 4: Confirm the mirrored skills no longer describe a purely feature-only operating system.
- [ ] Step 5: Update docs if the spec wording needs to reflect the final triage vocabulary.
- [ ] Step 6: Commit.

## Task 3: Update Plan-Writing and Plan-Execution Skills

**Files:**
- Modify: `.agents/skills/writing-plans/SKILL.md`
- Modify: `.agents/skills/executing-plans/SKILL.md`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Update `writing-plans` so cross-cutting or stage-heavy plans can explicitly use `Feature: none` and still name affected stages, adopted features, and generated discovery outputs.
- [x] Step 2: Update `writing-plans` so the doc update matrix and task structure can include stage contracts when relevant.
- [x] Step 3: Update `executing-plans` so execution review confirms both feature-contract correctness and stage-contract correctness when stage-aware docs are in scope.
- [x] Step 4: Run a consistency check:
  - `rg -n "docs/stages|Affected stages|Primary lens|cross-cutting operating-system change" .agents\\skills\\writing-plans .agents\\skills\\executing-plans`
- [x] Step 5: Confirm the planning and execution skills still preserve feature contracts as the primary lifecycle units.
- [ ] Step 6: Commit.

## Task 4: Final Sync and Review Pass

**Files:**
- Modify: `docs/superpowers/specs/2026-03-31-stage-aware-project-operating-system-design.md` only if terminology drift needs correction
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Re-read the spec, cursor rules, and mirrored skills together.
- [x] Step 2: Confirm the final operating-system model answers:
  - what feature is changing?
  - what stages are affected?
  - which lens is primary?
- [x] Step 3: Run a final repo-wide text audit for the new vocabulary:
  - `rg -n "docs/stages|Affected stages|Primary lens|stage-aware" .cursor .agents docs`
- [x] Step 4: If the wording drifted during implementation, make one bounded sync patch to the spec.
- [x] Step 5: Review diffs for completeness and ensure the plan stayed within the rules-and-skills-only scope.
- [ ] Step 6: Commit.

---

## Execution Order

1. Complete Task 1 first so the operating-system rules define the new model before any mirrored skills or generated discovery are touched.
2. Complete Task 2 next so design and triage skills match the rules before new planning/execution behavior is introduced.
3. Complete Task 3 after the core planning rules land, so plan-writing and plan-execution guidance inherit the new model cleanly.
4. Complete Task 4 last so the final wording describes the implemented operating system, not the earlier draft state.

## Verification Checklist

- [ ] Cursor rules describe stages as a navigation layer above features.
- [ ] Mirrored skills and cursor rules use the same stage-aware vocabulary.
- [ ] Planning and execution skills support cross-cutting work without inventing a fake managed feature.
- [ ] Feature contracts remain the primary lifecycle/versioning units.
- [ ] The operating-system layer is ready for a later project-specific rollout of stage contracts and generated discovery.

## Risks and Notes

### Vocabulary Drift Risk

Rules and mirrored skills can easily drift into slightly different terms.

Mitigation:
- land the rules first
- mirror wording from the rules into skills instead of paraphrasing
- run text audits after each documentation layer changes

### Scope-Creep Risk

This could expand into a full documentation-system rewrite if project-specific files are pulled into the same rollout.

Mitigation:
- keep this plan limited to rules and mirrored skills only
- defer stage contracts, feature metadata, and generated discovery to a later plan

### Adoption Risk

If the operating-system vocabulary is not stabilized first, later project-specific rollout work will encode the wrong structure into source files and generators.

Mitigation:
- land the rule and skill vocabulary first
- keep later project-specific implementation in a separate plan
