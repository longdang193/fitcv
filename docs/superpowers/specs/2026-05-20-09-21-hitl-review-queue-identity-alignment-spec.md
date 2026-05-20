---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: hitl-review-queue-identity-alignment
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-review-actions
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/_cv_review_queue.html
  - tests/
related_features:
  - admin_control_plane_core
  - cv_system
related_stages:
  - cv_generation
---

## Goal

Define minimal, root-cause patch that removes mismatch between run pause count and review queue visibility for review-required CV records, including records missing `job_url`.

## Key Deliverables

### Unified review item identity contract

Specify stable `review_item_id` generation, persistence, and read-path fallback so all review-required rows are addressable even when `job_url` is missing.

### Counter and queue symmetry

Specify one shared pending-definition used by worker pause logic and review queue aggregation so `pending_count` equals paused review-required count for same run state.

### Action routing by identity

Specify review action selectors and backward compatibility so queue actions resolve by `review_item_id` first and legacy `job_url` path remains supported.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- pin exact asymmetry between pause counter and queue renderer

**Steps:**
- [ ] trace worker finalize logic for `review_required` counting
- [ ] trace queue-build logic and row filtering
- [ ] trace action-entry lookup keys and closure gates
- [ ] classify mismatch cases (`missing job_url`, stale action mapping, mixed payload versions)

**Verification:**
- [ ] root cause reproduced with source references and deterministic mismatch condition

**Exit Criteria:**
- mismatch condition stated as precise contract violation, not symptom wording

### Wave 2: Decision closure

**Purpose:**
- choose smallest complete design that removes mismatch class

**Steps:**
- [ ] compare options with MECE partition:
  - counting-only patch
  - UI-only patch
  - identity-model patch
  - upstream-hard-invariant patch
- [ ] apply razor principle: keep only decisions needed to eliminate class of bug
- [ ] define canonical pending predicate and selector contract

**Verification:**
- [ ] each non-chosen option rejected with concrete residual-risk reason

**Exit Criteria:**
- one coherent design selected with compatibility and migration notes

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof that bug class removed and no closure regression introduced

**Steps:**
- [ ] define unit/integration tests for missing-URL and mixed-row cases
- [ ] define run-level evidence checks for event payload and queue rendering
- [ ] define backward compatibility checks for old payloads lacking `review_item_id`

**Verification:**
- [ ] validation plan proves queue visibility, actionability, and closure correctness

**Exit Criteria:**
- implementation-ready spec with testable acceptance criteria

## Design Decisions

### Decision: Introduce `review_item_id` as canonical row identity

- context: current queue/action model keys by `job_url`; rows with empty `job_url` are dropped, while worker still counts them
- choice: assign deterministic `review_item_id` to each review-required record at debug-payload build/write time; use as primary key across queue, actions, and pending calculations
- alternatives considered:
  - keep `job_url` as required key and suppress non-url rows in counter
  - force upstream `job_url` always present
- impact:
  - removes hidden pending rows
  - keeps `job_url` optional display/data field
  - enables action ledger and closure logic to remain row-complete

### Decision: Define one pending predicate shared by worker and app

- context: worker and app currently derive pending from different key assumptions
- choice: pending row = `status == review_required` AND latest resolution status not in terminal-resolution set, keyed by `review_item_id`
- alternatives considered:
  - retain separate worker/app computations and attempt soft synchronization
- impact:
  - counter/queue symmetry
  - simpler debugging invariant

### Decision: Keep backward compatibility for legacy payload/action records

- context: existing run records may not contain `review_item_id`
- choice: read-path fallback derives deterministic `review_item_id`; action lookup supports legacy `job_url` entries when id absent
- alternatives considered:
  - one-time migration script for all historical rows
- impact:
  - no blocking data migration
  - zero-downtime behavior for existing runs

### Decision: UI must render non-URL review rows with explicit state

- context: hidden rows create operator dead-end and false "no blocks to review"
- choice: render rows without `job_url` as pending items with `missing_job_url` marker; disable URL-dependent controls only
- alternatives considered:
  - hide non-actionable rows from UI
- impact:
  - operator sees true pending inventory
  - avoids silent queue undercount

## Invariants

- Every review-required record has stable identity in runtime processing (`review_item_id` either persisted or derived deterministically).
- Worker pause pending count and review-queue pending count must match for same payload snapshot.
- Queue rendering must not drop review-required rows solely due to missing `job_url`.
- Closure to `succeeded` from awaiting-review remains blocked until all review-required identities terminal.
- Legacy payloads without `review_item_id` remain readable and actionable.

## Acceptance Criteria

1. For run with N review-required rows and zero terminal actions, UI shows `pending_count == N` regardless of missing `job_url`.
2. For mixed rows (some with URL, some without), pause event `remaining` equals queue `pending_count`.
3. Single-row action endpoint can resolve target row by `review_item_id` when `job_url` empty.
4. Batch action endpoint can apply action using selected `review_item_id` list and skip only already-terminal rows.
5. Run cannot auto-close while any review-required identity remains pending.
6. Existing runs with legacy payload (no `review_item_id`) still render queue and accept actions.

## Non-Goals

- No redesign of CV generation policy or reason-code taxonomy.
- No changes to run-mode gating (`run_all` vs `manual_staged`) beyond pending identity alignment.
- No historical backfill job for old persisted runs beyond read-time derivation.
- No UI theme/layout overhaul outside review queue row-state clarity.

## Risks and Mitigations

- Risk: deterministic id collision on weak identity tuple.
  - Mitigation: include multiple stable fields (`run_id`, rank/index, job_url, job_title hash) and collision guard in tests.
- Risk: closure regressions from mixed legacy/new action entries.
  - Mitigation: normalize latest action map by `review_item_id` with explicit fallback precedence rules.
- Risk: hidden coupling with regenerate-once worker path that currently expects `job_url`.
  - Mitigation: mark regenerate control unavailable for missing-URL rows; keep approve/reject path id-based.
- Risk: drift between event payload fields and UI counters.
  - Mitigation: assert parity in integration tests against emitted `cv_review_required` payload and queue summary.

## Validation Plan

- proof target: review-required rows without URL are visible and counted
  - method: integration test on `_build_hitl_review_queue` with synthetic payload containing 7 review-required rows missing URL
  - evidence: test output shows `pending_count=7`, `total_review_required=7`, `queue_items length=7`

- proof target: worker/app pending symmetry holds
  - method: run-level test invoking finalize-status summary + queue build from same debug records
  - evidence: equality assertion between `review_required_remaining` and queue pending

- proof target: actions resolve without job_url
  - method: endpoint test posting action with `review_item_id` only
  - evidence: stored `hitl_review_actions` entry references same id and row resolution status terminalizes

- proof target: legacy payload compatibility
  - method: fixture without `review_item_id`; call queue and action paths
  - evidence: derived id present in in-memory row model; action succeeds

- proof target: no premature closure
  - method: closure gate test with one pending identity and zero accepted CV artifacts
  - evidence: run remains `awaiting_continue` with checkpoint `awaiting_review`

## Completion Criteria

1. all Key Deliverables satisfied by merged implementation and tests
2. downstream implementation plan is generated from this approved spec
3. validation evidence demonstrates invariant preservation for legacy and new payload shapes
