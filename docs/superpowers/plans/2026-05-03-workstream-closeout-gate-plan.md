---
layer: operating_system
artifact_type: plan
status: completed
parent_workstream: none
targets:
  - docs/superpowers/specs/2026-05-03-workstream-closeout-gate-spec.md
  - docs/operating_system/prompt_templates/workstream-completion-and-intent-check-prompt.md
  - docs/operating_system/prompt_templates/execute-prompt.md
  - scripts/validate_planning_lifecycle.py
  - scripts/validate_checkpoint_packs.py
  - scripts/validate_repo_contracts.py
related_features: []
related_stages: []
---

# Workstream Closeout Gate Implementation Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/specs/2026-05-03-workstream-closeout-gate-spec.md`  
**Type:** add  
**Plan Layer:** operating_system  
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Enforce a closeout gate so plan/workstream completion cannot be recorded while thread status and checkpoint evidence remain unreconciled.

**Architecture:** Keep validator-first enforcement. Reuse existing lifecycle/checkpoint validators, add missing checks where needed, then codify the closeout ritual in prompt guidance. Route enforcement through `validate_repo_contracts.py --fast` and adopt strict mode in CI once migration cleanup is done.

**Key Invariants:**
- completion claims and metadata must match
- completed workstreams can only contain terminal thread statuses
- closed threads require checkpoint evidence
- closeout must fail fast when lineage/status evidence is inconsistent

---

## Task 1: Lock Validator Behavior

- [x] Step 1: Confirm `validate_planning_lifecycle.py` enforces terminal-only thread statuses for completed workstreams (`completed | dropped`).
- [x] Step 2: Extend lifecycle validator to flag completed-workstream threads missing checkpoint evidence (directly or via checkpoint validator integration).
- [x] Step 3: Add/adjust tests to cover:
  - completed workstream with `proposed` thread (must fail)
  - completed workstream with terminal threads but missing checkpoint packs (must fail or strict-fail by policy)

## Task 2: Closeout Ritual In Prompt Surface

- [x] Step 1: Update `workstream-completion-and-intent-check-prompt.md` to make status/evidence reconciliation an explicit closeout output requirement.
- [x] Step 2: Update `execute-prompt.md` with a closeout gate note for plans ending in `status: completed`.
- [x] Step 3: Ensure prompt templates point to required validator commands before closure.

## Task 3: Wire Enforcement In Repo Gate

- [x] Step 1: Keep `validate_planning_lifecycle.py` in `validate_repo_contracts.py --fast`.
- [x] Step 2: Document strict-mode adoption path (`validate_planning_lifecycle.py --strict`) for CI/protected branches.
- [x] Step 3: Add a short operating-system note on when strict mode becomes mandatory.

## Task 4: Migration And Cleanup Pass

- [x] Step 1: Identify current completed workstreams with non-terminal threads.
- [x] Step 2: Reconcile thread statuses to `completed` or `dropped`.
- [x] Step 3: Backfill missing checkpoint packs for closed threads where required.
- [x] Step 4: Regenerate derived planning lineage (`scripts/generate_planning_lineage.py`) if lineage metadata changed.

## Task 5: Verify And Close

- [x] Step 1: Run `python scripts/validate_planning_lifecycle.py --strict`.
- [x] Step 2: Run `python scripts/validate_checkpoint_packs.py`.
- [x] Step 3: Run `python scripts/validate_repo_contracts.py --fast`.
- [x] Step 4: Mark this plan `completed` only after all checks pass.
