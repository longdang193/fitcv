---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/worker_job.py
  - config/taxonomy/skill_synonyms.yaml
  - docs/api.md
  - docs/observability.md
  - tests/test_fitcv_cp/test_app.py
related_features:
  - trigger_run_management
  - settings_system
  - inspection_debugging
related_stages:
  - enrich
  - rule_filter
---

# Repeatable Batch Submit, Promote-To-Global, And LLM-Assisted Triage

## Summary

Add three upgrades to synonym review operations:

1. reliable repeatable batch submission (multiple submits on same run)
2. explicit `Promote to Global` workflow for approved run-scoped proposals
3. advisory LLM-assisted triage (`approve/defer/reject`) under strict HITL

## Problem

- batch submission is not consistently reusable for subsequent passes
- approved run-scoped synonyms are not easily promotable to shared/global policy
- proposal review is manual-heavy without assisted prioritization

## Goals

- ensure operators can submit batch decisions repeatedly in one run lifecycle
- provide explicit and auditable global promotion controls
- accelerate review with LLM recommendations while keeping human final authority

## Non-Goals

- no autonomous global mutation by LLM
- no removal of run-scoped proposal artifacts
- no replacement of deterministic base proposal generation

## Contract

## 1) Repeatable Batch Submit

Batch review endpoint must support repeated submissions on the same run:

- each submit reads current row selections only
- already-resolved rows are safely skipped with explicit reason
- no sticky stale form state across submits
- returns per-submit summary: `applied/skipped/failed`

UI requirements:

- render summary banner after submit
- keep controls interactive for subsequent submits
- show row-level current status after each submit

## 2) Promote-To-Global Workflow

Promotion can occur only for proposals with run status `approved_for_run_overlay`.

Required flow:

1. select approved proposals
2. preview global diff (`add`, `update`, `conflict`, `skip`)
3. confirm promotion
4. write global synonym policy + audit event

Policy behavior:

- global mapping update is explicit and reversible
- conflicts require operator confirmation path
- promotion source metadata includes `run_id`, `proposal_id`, actor, note

## 3) LLM-Assisted Triage (Advisory Only)

For each pending proposal, system may provide:

- `recommended_action` (`approve`/`defer`/`reject`)
- recommendation confidence
- short rationale
- risk/conflict flags

Hard rule:

- recommendations are advisory only
- final state change requires explicit human submit (HITL)

UI requirements:

- recommendation displayed per row
- optional “apply recommendations to selected” helper
- operator can override before submit

## 4) Audit And Trace

All review and promotion actions must emit auditable records:

- actor
- timestamp
- previous and new status
- selected action
- recommendation snapshot (if present)
- promotion source and global diff outcome

## Acceptance Criteria

1. Operator can submit batch decisions multiple times in same run.
2. Second/third submits apply only newly selected pending rows.
3. `Promote to Global` is available for approved proposals with preview+confirm.
4. Global promotion writes auditable metadata and conflict outcomes.
5. LLM recommendations are visible but never auto-applied.
6. HITL remains mandatory for all proposal state changes and global promotion.

## Validation Plan

- app tests for repeated batch submits on same run
- app tests for skip behavior on already-resolved rows
- app tests for promote preview + commit + conflict handling
- app tests for recommendation visibility and manual override
- contract gate:
  - `python scripts/validate_repo_contracts.py --fast`

## Rollout

1. fix repeatable batch submit path and result reporting
2. add promote preview/commit endpoints + UI
3. add LLM recommendation fields and UI rendering
4. add recommendation helper action (prefill only)
5. update docs and run validation gate
