# Stage Contract Docs Adoption Implementation Plan

**Feature:** `docs/features/inspection_debugging/inspection_debugging.yaml`  
**Spec:** `docs/superpowers/specs/2026-03-31-stage-contract-docs-adoption-design.md`  
**Type:** modify  
**Status:** planned  

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

## Status Snapshot

- Completed:
  - Task 1: create the initial six stage contracts
  - Task 2: add stage metadata to `cv_system`, `trigger_run_management`, and `inspection_debugging`
  - Task 3: update the three feature history files for the stage-aware docs adoption
  - Task 4: run the final architecture review and source-layer consistency pass
- Partially complete:
  - none
- Pending:
  - none

**Goal:** Create the first project-specific stage contracts for the core pipeline boundaries and link the three most relevant feature contracts into that stage-aware doc layer.

**Architecture:** Phase 1 creates a bounded stage-source layer under `docs/stages/` for six stable pipeline boundaries: `normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, and `cv_generation`. It also adds `primary_stage` and `stages` to the three most relevant feature contracts, then records the adoption in feature history without changing runtime behavior or generated discovery yet.

**Key Invariants:**
- Stage contracts remain architectural boundary docs, not replacement lifecycle units.
- Feature contracts remain the primary current-state capability contracts.
- Stage docs must describe boundaries and handoffs without duplicating full feature truth.
- This rollout stays limited to the six core pipeline stages and three relevant feature contracts.

**Rollout / Revert:**  
- rollback_trigger: the new stage docs become ambiguous, duplicate feature truth heavily, or create conflicting stage boundaries across pipeline work  
- rollback_method: revert the new `docs/stages/*.yaml` files and the stage metadata/history updates on the three feature contracts together  

---

## Doc Update Matrix

- Feature contract:
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/features/trigger_run_management/trigger_run_management.yaml`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
- Stage contracts:
  - `docs/stages/normalize.yaml`
  - `docs/stages/enrich.yaml`
  - `docs/stages/rule_filter.yaml`
  - `docs/stages/shortlist.yaml`
  - `docs/stages/ranking.yaml`
  - `docs/stages/cv_generation.yaml`
- Feature history:
  - `docs/features/cv_system/history.md`
  - `docs/features/trigger_run_management/history.md`
  - `docs/features/inspection_debugging/history.md`
- Feature-specific docs: `none`
- Cross-cutting docs:
  - `docs/superpowers/specs/2026-03-31-stage-contract-docs-adoption-design.md`
- README: `none`
- Generated discovery: `none`

## Stage and Adoption Scope

- Affected stages:
  - `normalize`
  - `enrich`
  - `rule_filter`
  - `shortlist`
  - `ranking`
  - `cv_generation`
- Affected features:
  - `cv_system`
  - `trigger_run_management`
  - `inspection_debugging`
- Primary lens: stage

## File Structure First

- Create:
  - `docs/stages/normalize.yaml`
  - `docs/stages/enrich.yaml`
  - `docs/stages/rule_filter.yaml`
  - `docs/stages/shortlist.yaml`
  - `docs/stages/ranking.yaml`
  - `docs/stages/cv_generation.yaml`
- Modify:
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/features/trigger_run_management/trigger_run_management.yaml`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/cv_system/history.md`
  - `docs/features/trigger_run_management/history.md`
  - `docs/features/inspection_debugging/history.md`

---

## Task 1: Create the Initial Stage Contracts

**Files:**
- Create: `docs/stages/normalize.yaml`
- Create: `docs/stages/enrich.yaml`
- Create: `docs/stages/rule_filter.yaml`
- Create: `docs/stages/shortlist.yaml`
- Create: `docs/stages/ranking.yaml`
- Create: `docs/stages/cv_generation.yaml`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Draft one consistent Phase 1 stage-contract schema across all six files using only:
  - `stage_id`
  - `name`
  - `summary`
  - `boundaries`
  - `inputs`
  - `outputs`
  - `depends_on`
  - `primary_features`
  - `related_features`
  - `refs`
  - `keywords`
- [x] Step 2: Populate `normalize.yaml` and `enrich.yaml` with stable boundary definitions that reflect the current pipeline vocabulary.
- [x] Step 3: Populate `rule_filter.yaml` and `shortlist.yaml` with boundary definitions that make the deterministic gate and retrieval handoff easy to understand.
- [x] Step 4: Populate `ranking.yaml` and `cv_generation.yaml` with boundary definitions that match the current ranking authority model and CV-generation/validation boundary.
- [x] Step 5: Verify the stage files stay architectural and do not drift into feature-style lifecycle fields or runtime implementation dumps.
- [x] Step 6: Run a text audit:
  - `rg -n "stage_id|primary_features|related_features|boundaries|inputs|outputs" docs\\stages`
- [ ] Step 7: Commit.

## Task 2: Add Stage Metadata to the Three Relevant Feature Contracts

**Files:**
- Modify: `docs/features/cv_system/cv_system.yaml`
- Modify: `docs/features/trigger_run_management/trigger_run_management.yaml`
- Modify: `docs/features/inspection_debugging/inspection_debugging.yaml`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add `primary_stage` and `stages` to `cv_system.yaml`, keeping the values bounded and aligned with the spec’s recommended scope.
- [x] Step 2: Add `primary_stage` and `stages` to `trigger_run_management.yaml`, focusing on the earlier orchestration-facing stages it materially affects.
- [x] Step 3: Add `primary_stage` and `stages` to `inspection_debugging.yaml`, emphasizing the inspected stages it most strongly centers on.
- [x] Step 4: Verify the stage metadata in the three feature contracts is:
  - obvious
  - bounded
  - compatible with the six stage contracts
  - not pretending these features own every pipeline stage equally
- [x] Step 5: Run a text audit:
  - `rg -n "primary_stage|stages:" docs\\features\\cv_system\\cv_system.yaml docs\\features\\trigger_run_management\\trigger_run_management.yaml docs\\features\\inspection_debugging\\inspection_debugging.yaml`
- [ ] Step 6: Commit.

## Task 3: Update Feature History for the Stage-Aware Docs Adoption

**Files:**
- Modify: `docs/features/cv_system/history.md`
- Modify: `docs/features/trigger_run_management/history.md`
- Modify: `docs/features/inspection_debugging/history.md`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add a concise history entry to `cv_system/history.md` recording the new stage metadata and clarifying that this was a documentation-structure adoption, not a runtime behavior change by itself.
- [x] Step 2: Add the equivalent stage-adoption entry to `trigger_run_management/history.md`.
- [x] Step 3: Add the equivalent stage-adoption entry to `inspection_debugging/history.md`.
- [x] Step 4: Verify the three history entries clearly state:
  - stage-aware doc adoption happened
  - which stage mapping was introduced
  - no hidden runtime change is implied
- [ ] Step 5: Commit.

## Task 4: Final Architecture Review and Source-Layer Consistency Pass

**Files:**
- Modify: `docs/superpowers/specs/2026-03-31-stage-contract-docs-adoption-design.md` only if terminology drift needs correction
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Re-read the six stage contracts and the three updated feature contracts together.
- [x] Step 2: Confirm a reader can answer:
  - what each stage owns
  - which features primarily participate in that stage
  - which stages each feature materially affects
- [x] Step 3: Re-check compatibility with [`2026-03-31-stage-transition-artifacts-design.md`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/superpowers/specs/2026-03-31-stage-transition-artifacts-design.md), ensuring the stage docs define boundaries while that spec still owns runtime artifact design.
- [x] Step 4: Run a final text audit:
  - `rg -n "primary_stage|related_features|primary_features|stage_id|cv_generation|shortlist|ranking" docs\\stages docs\\features\\cv_system docs\\features\\trigger_run_management docs\\features\\inspection_debugging`
- [x] Step 5: If terminology drifted during implementation, make one bounded sync patch to `docs/superpowers/specs/2026-03-31-stage-contract-docs-adoption-design.md`.
- [x] Step 6: Review diffs for completeness and confirm this rollout stayed within Phase 1 scope with no generated discovery changes.
- [ ] Step 7: Commit.

---

## Execution Order

1. Complete Task 1 first so the repo has real stage-source files before any feature contract points to them.
2. Complete Task 2 next so the three feature contracts can reference the new stage layer consistently.
3. Complete Task 3 after the feature contracts land, so the history entries describe the actual adopted mapping.
4. Complete Task 4 last so the final wording and boundary map can be reviewed as one coherent source layer.

## Verification Checklist

- [ ] The repo has real stage source docs for `normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, and `cv_generation`.
- [ ] Each stage contract is architectural and stage-scoped, not a duplicate feature contract.
- [ ] `cv_system`, `trigger_run_management`, and `inspection_debugging` expose `primary_stage` and `stages`.
- [ ] The feature stage metadata stays bounded and compatible with the six stage contracts.
- [ ] The three history files clearly frame this as a documentation-structure adoption, not a hidden runtime behavior change.
- [ ] The stage docs remain compatible with `2026-03-31-stage-transition-artifacts-design.md`.
- [ ] No generated discovery work was pulled into this rollout.

## Risks and Notes

### Boundary Drift Risk

If the stage contracts are written too loosely, they will stop being useful as architectural anchors.

Mitigation:
- keep the six stages tightly aligned to the existing pipeline vocabulary
- prefer stable handoff language over low-level implementation detail
- review the six files together before completion

### Duplication Risk

The new stage docs could become noisy if they restate too much feature truth.

Mitigation:
- keep feature lifecycle and capability truth in `docs/features/*.yaml`
- use stage docs only for boundaries, inputs, outputs, and stage-to-feature relationships
- keep the feature metadata bounded to `primary_stage` and `stages`

### Scope-Creep Risk

This work could easily expand into generated discovery or repo-wide stage adoption too early.

Mitigation:
- keep generated discovery explicitly out of this plan
- limit feature updates to the three named contracts
- defer broader adoption until this first stage-source layer proves useful
